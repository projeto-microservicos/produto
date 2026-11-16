#!/usr/bin/env python3
"""Prepare an isolated Minikube demo. Every Kubernetes command names its local context."""
import argparse
import os
from pathlib import Path
import secrets
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
PROFILE = "store-local"
NAMESPACE = "store-demo"
SERVICES = ("account", "product", "auth", "exchange", "order", "gateway")


def run(*args, **kwargs):
    return subprocess.run(args, cwd=ROOT, check=True, **kwargs)


def local_manifests():
    # Read previously generated local credentials without ever printing them.
    envfile = ROOT / ".local/kubernetes.secret.env"
    envfile.parent.mkdir(exist_ok=True)
    if envfile.exists():
        settings = dict(line.split("=", 1) for line in envfile.read_text().splitlines() if "=" in line)
    else:
        settings = {"DB_PASSWORD": secrets.token_urlsafe(48), "JWT_SECRET": secrets.token_urlsafe(48)}
        fd = os.open(envfile, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            out.write("".join(f"{key}={value}\n" for key, value in settings.items()))
    docs = []
    for service in SERVICES:
        configs = list(yaml.safe_load_all((ROOT / "services" / service / "k8s/config.example.yaml").read_text(encoding="utf-8")))
        cfg = next(doc for doc in configs if doc and doc["kind"] == "ConfigMap")
        data = cfg["data"]
        if service in {"account", "product", "order"}:
            data.update(DATABASE_HOST="postgres", DATABASE_DB="store", DATABASE_SSLMODE="disable")
            docs.append({"apiVersion": "v1", "kind": "Secret", "metadata": {"name": f"{service}-secrets"},
                         "stringData": {"DATABASE_USERNAME": "store", "DATABASE_PASSWORD": settings["DB_PASSWORD"]}})
        if service == "auth":
            data["JWT_COOKIE_SECURE"] = "false"
            docs.append({"apiVersion": "v1", "kind": "Secret", "metadata": {"name": "auth-secrets"},
                         "stringData": {"JWT_SECRET": settings["JWT_SECRET"]}})
        if service == "gateway":
            data["CORS_ALLOWED_ORIGINS"] = "http://localhost:*"
        for key, value in list(data.items()):
            if "REPLACE" in str(value):
                del data[key]
        docs.append(cfg)
        for doc in yaml.safe_load_all((ROOT / "services" / service / "k8s/k8s.yaml").read_text(encoding="utf-8")):
            if not doc:
                continue
            if doc["kind"] == "Deployment":
                container = doc["spec"]["template"]["spec"]["containers"][0]
                container["imagePullPolicy"] = "Never"
                if service != "exchange":
                    container.setdefault("env", []).append({"name": "JAVA_TOOL_OPTIONS", "value": "-XX:MaxRAMPercentage=65.0"})
                doc["spec"]["strategy"] = {"type": "RollingUpdate", "rollingUpdate": {"maxSurge": 0, "maxUnavailable": 1}}
            docs.append(doc)
    docs += list(yaml.safe_load_all((ROOT / "k8s/local-postgres.yaml").read_text(encoding="utf-8")))
    docs.append({"apiVersion": "v1", "kind": "Secret", "metadata": {"name": "postgres-secrets"},
                 "stringData": {"POSTGRES_USER": "store", "POSTGRES_DB": "store", "POSTGRES_PASSWORD": settings["DB_PASSWORD"]}})
    for doc in docs:
        doc["metadata"]["namespace"] = NAMESPACE
    return docs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["render", "start", "load", "status", "stop"])
    args = parser.parse_args()
    kubectl = ["kubectl", "--context", PROFILE, "--request-timeout=30s", "-n", NAMESPACE]
    if args.command in {"render", "start"}:
        docs = local_manifests()
        target = ROOT / ".local/kubernetes.local.yaml"
        target.write_text(yaml.safe_dump_all(docs, sort_keys=False), encoding="utf-8")
        print(f"Rendered {len(docs)} local resources including Secrets to ignored .local directory")
        if args.command == "render":
            return
        run("minikube", "start", "--profile", PROFILE, "--driver=docker", "--memory=4096", "--cpus=4", "--keep-context=true")
        run("minikube", "--profile", PROFILE, "addons", "enable", "metrics-server")
        for service in SERVICES:
            run("minikube", "--profile", PROFILE, "image", "load", f"store/{service}-service:dev")
        run("minikube", "--profile", PROFILE, "image", "load", "postgres:17")
        # Apply an isolated namespace; never use the current (possibly AWS) context.
        namespace = {"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": NAMESPACE}}
        run(*kubectl, "apply", "-f", "-", input=yaml.safe_dump(namespace), text=True)
        run(*kubectl, "apply", "-f", str(target))
        for service in ("postgres", *SERVICES):
            run(*kubectl, "rollout", "status", f"deployment/{service}", "--timeout=360s")
        run(*kubectl, "apply", "-f", "k8s/hpa.yaml")
    elif args.command == "load":
        # Start one bounded Job, never an endless load-generator loop.
        script = (ROOT / "load/store.js").read_text(encoding="utf-8")
        docs = [{"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "store-load-script"}, "data": {"store.js": script}},
                *yaml.safe_load_all((ROOT / "k8s/load-job.yaml").read_text(encoding="utf-8"))]
        run(*kubectl, "apply", "-f", "-", input=yaml.safe_dump_all(docs), text=True)
        print("Watch: kubectl --context store-local -n store-demo get hpa,pods -w")
        print("Logs: kubectl --context store-local -n store-demo logs -f job/store-load")
    elif args.command == "status":
        run(*kubectl, "get", "deployments,hpa,pods")
        run(*kubectl, "top", "pods")
    elif args.command == "stop":
        run("minikube", "stop", "--profile", PROFILE)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
