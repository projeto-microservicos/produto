#!/usr/bin/env python3
"""Prepare per-service RDS roles through a temporary Kubernetes Job. No writes without --apply."""
import argparse
import base64
import json
from pathlib import Path
import secrets
import subprocess
import sys
import time
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {"account": "accounts", "product": "products", "order": "orders"}


def capture(*args):
    return subprocess.check_output(args, cwd=ROOT, text=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--admin-secret-arn", required=True, help="MasterSecretArn output from the RDS stack")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    config = json.loads(Path(args.environment).read_text(encoding="utf-8-sig"))
    if "REPLACE" in config["database_host"]:
        parser.error("Set the RDS endpoint first")
    identity = json.loads(capture("aws", "sts", "get-caller-identity", "--output", "json"))
    if identity["Account"] != config["account_id"]:
        parser.error("AWS identity mismatch")
    if not args.admin_secret_arn.startswith(f"arn:aws:secretsmanager:{config['region']}:{config['account_id']}:secret:"):
        parser.error("Master secret must belong to the configured region and account")
    context = f"arn:aws:eks:{config['region']}:{config['account_id']}:cluster/{config['cluster']}"
    kubectl = ["kubectl", "--context", context, "--request-timeout=30s", "-n", config["namespace"]]
    admin = json.loads(capture("aws", "secretsmanager", "get-secret-value", "--secret-id", args.admin_secret_arn,
                               "--region", config["region"], "--query", "SecretString", "--output", "text"))
    credential_file = ROOT / ".local/database-credentials.secret.env"
    credential_file.parent.mkdir(exist_ok=True)
    saved = {}
    if credential_file.exists():
        saved = dict(line.split("=", 1) for line in credential_file.read_text().splitlines() if "=" in line)
    app_secrets, statements = [], []
    for service, schema in SCHEMAS.items():
        name = f"{service}-secrets"
        existing = capture(*kubectl, "get", "secret", name, "--ignore-not-found", "-o", "json").strip()
        username = f"store_{service}"
        password = saved.get(service, secrets.token_urlsafe(48))
        if existing:
            values = json.loads(existing)["data"]
            username = base64.b64decode(values["DATABASE_USERNAME"]).decode()
            password = base64.b64decode(values["DATABASE_PASSWORD"]).decode()
            if username != f"store_{service}":
                parser.error(f"Existing {name} does not use the expected per-service role; review manually")
        saved[service] = password
        quoted = password.replace("'", "''")
        statements += [f"DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{username}') THEN CREATE ROLE {username} LOGIN; END IF; END $$;",
                       f"ALTER ROLE {username} PASSWORD '{quoted}';",
                       f"CREATE SCHEMA IF NOT EXISTS {schema} AUTHORIZATION {username};",
                       f"ALTER SCHEMA {schema} OWNER TO {username};"]
        app_secrets.append({"apiVersion": "v1", "kind": "Secret", "metadata": {"name": name, "namespace": config["namespace"]},
                            "stringData": {"DATABASE_USERNAME": username, "DATABASE_PASSWORD": password}})
    credential_file.write_text("".join(f"{key}={value}\n" for key, value in saved.items()), encoding="utf-8")
    secret_name = "store-database-bootstrap"
    job_name = f"store-db-bootstrap-{int(time.time())}"
    secret = {"apiVersion": "v1", "kind": "Secret", "metadata": {"name": secret_name, "namespace": config["namespace"]},
              "stringData": {"PGHOST": config["database_host"], "PGDATABASE": config["database_name"],
                             "PGUSER": admin["username"], "PGPASSWORD": admin["password"], "PGSSLMODE": "require",
                             "bootstrap.sql": "\n".join(statements)}}
    job = {"apiVersion": "batch/v1", "kind": "Job", "metadata": {"name": job_name, "namespace": config["namespace"]},
           "spec": {"backoffLimit": 0, "activeDeadlineSeconds": 120, "ttlSecondsAfterFinished": 600,
                    "template": {"spec": {"restartPolicy": "Never", "automountServiceAccountToken": False,
                        "containers": [{"name": "psql", "image": "postgres:17",
                            "command": ["psql", "-v", "ON_ERROR_STOP=1", "-f", "/bootstrap/bootstrap.sql"],
                            "env": [{"name": key, "valueFrom": {"secretKeyRef": {"name": secret_name, "key": key}}}
                                    for key in ("PGHOST", "PGDATABASE", "PGUSER", "PGPASSWORD", "PGSSLMODE")],
                            "resources": {"requests": {"cpu": "50m", "memory": "32Mi"}, "limits": {"cpu": "250m", "memory": "128Mi"}},
                            "volumeMounts": [{"name": "sql", "mountPath": "/bootstrap", "readOnly": True}]}],
                        "volumes": [{"name": "sql", "secret": {"secretName": secret_name, "items": [{"key": "bootstrap.sql", "path": "bootstrap.sql"}]}}]}}}}
    target = ROOT / ".local/database-bootstrap.local.yaml"
    target.write_text(yaml.safe_dump_all([secret, job, *app_secrets], sort_keys=False), encoding="utf-8")
    print("Prepared database bootstrap and per-service Secrets under ignored .local/; values not printed")
    if not args.apply:
        print("No cluster changes. Rerun with --apply after reviewing the target and cost.")
        return
    try:
        subprocess.run([*kubectl, "apply", "-f", "-"], input=yaml.safe_dump_all([secret, job]), text=True, check=True)
        subprocess.run([*kubectl, "wait", "--for=condition=complete", f"job/{job_name}", "--timeout=150s"], check=True)
        subprocess.run([*kubectl, "apply", "-f", "-"], input=yaml.safe_dump_all(app_secrets), text=True, check=True)
        print("Database roles, schemas and application Secrets configured; master credentials are not used by the apps")
    finally:
        subprocess.run([*kubectl, "delete", "job", job_name, "--ignore-not-found"], check=False)
        subprocess.run([*kubectl, "delete", "secret", secret_name, "--ignore-not-found"], check=False)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
