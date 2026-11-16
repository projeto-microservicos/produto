#!/usr/bin/env python3
"""Check an explicit EKS target and server-validate the manifest. Use --apply to deploy."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ("account", "product", "auth", "exchange", "order", "gateway")


def capture(*args):
    return subprocess.check_output(args, cwd=ROOT, text=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--manifest", default="artifacts/eks.local.yaml")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    config = json.loads(Path(args.environment).read_text(encoding="utf-8-sig"))
    context = f"arn:aws:eks:{config['region']}:{config['account_id']}:cluster/{config['cluster']}"
    namespace = config["namespace"]
    identity = json.loads(capture("aws", "sts", "get-caller-identity", "--output", "json"))
    if identity["Account"] != config["account_id"]:
        parser.error("AWS account mismatch")
    kubectl = ["kubectl", "--context", context, "--request-timeout=30s", "-n", namespace]
    documents = list(yaml.safe_load_all(Path(args.manifest).read_text(encoding="utf-8")))
    for doc in documents:
        if not doc or doc["kind"] not in {"Deployment", "Service", "ConfigMap"}:
            parser.error("Manifest may only contain application Deployments, Services and ConfigMaps")
        if doc["metadata"].get("namespace") != namespace:
            parser.error("Manifest namespace mismatch")
        if doc["kind"] == "Service" and doc.get("spec", {}).get("type", "ClusterIP") != "ClusterIP":
            parser.error("Public exposure must be configured separately with TLS")
    for name, keys in {"account-secrets": {"DATABASE_USERNAME", "DATABASE_PASSWORD"},
                       "product-secrets": {"DATABASE_USERNAME", "DATABASE_PASSWORD"},
                       "order-secrets": {"DATABASE_USERNAME", "DATABASE_PASSWORD"},
                       "auth-secrets": {"JWT_SECRET"}}.items():
        # Fetch key names only, never secret values.
        names = capture(*kubectl, "get", "secret", name, "-o", 'go-template={{range $k,$v := .data}}{{$k}}{{" "}}{{end}}')
        if not keys.issubset(set(names.split())):
            parser.error(f"Missing keys in {name}: {sorted(keys)}")
    subprocess.run([*kubectl, "apply", "--dry-run=server", "-f", args.manifest], check=True)
    print("Identity, target, Secret keys and server dry-run passed")
    if args.apply:
        # Save the previous application deployment specs to support rollback without secret values.
        previous = capture(*kubectl, "get", "deployment", "-o", "yaml")
        (ROOT / "artifacts").mkdir(exist_ok=True)
        (ROOT / "artifacts/previous-deployments.local.yaml").write_text(previous, encoding="utf-8")
        subprocess.run([*kubectl, "apply", "-f", args.manifest], check=True)
        for service in SERVICES:
            subprocess.run([*kubectl, "rollout", "status", f"deployment/{service}", "--timeout=300s"], check=True)
        print("Six services deployed. Validate through a port-forward before enabling public ingress.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
