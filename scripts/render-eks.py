#!/usr/bin/env python3
"""Render all application manifests and ConfigMaps; no cluster or Secrets are modified."""
import argparse
import json
from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ("account", "product", "auth", "exchange", "order", "gateway")


def render(config, images):
    for key in ("region", "account_id", "cluster", "namespace", "database_host", "database_name", "cors_origin"):
        if not isinstance(config.get(key), str) or not config[key] or "REPLACE" in config[key]:
            raise ValueError(f"Set {key} in the environment file")
    if not re.fullmatch(r"https://[^/\s]+|http://(?:127\.0\.0\.1|localhost):[0-9]+", config["cors_origin"]):
        raise ValueError("Use an HTTPS origin or an explicit loopback origin for port-forward")
    namespace = config["namespace"]
    documents = []
    for service in SERVICES:
        image = images.get(service, "")
        prefix = f"{config['account_id']}.dkr.ecr.{config['region']}.amazonaws.com/{service}-service@sha256:"
        if not image.startswith(prefix) or not re.fullmatch(r"[0-9a-f]{64}", image[len(prefix):]):
            raise ValueError(f"Set an ECR digest image for {service}")
        cfg_docs = list(yaml.safe_load_all((ROOT / "services" / service / "k8s/config.example.yaml").read_text(encoding="utf-8")))
        configmap = next(doc for doc in cfg_docs if doc and doc.get("kind") == "ConfigMap")
        data = configmap["data"]
        if service in {"account", "product", "order"}:
            data.update(DATABASE_HOST=config["database_host"], DATABASE_DB=config["database_name"], DATABASE_SSLMODE="require")
        if service == "order":
            for key in ("REDIS_HOST", "RABBITMQ_HOST"):
                data.pop(key, None)
        if service == "gateway":
            data["CORS_ALLOWED_ORIGINS"] = config["cors_origin"]
        for key, value in list(data.items()):
            if "REPLACE" in str(value):
                # Disabled optional infrastructure must not carry a placeholder into deployment.
                if service == "exchange" and key in {"REDIS_URL", "RABBITMQ_URL"}:
                    data.pop(key)
                else:
                    raise ValueError(f"Unresolved setting {service}.{key}")
        documents.append(configmap)
        for doc in yaml.safe_load_all((ROOT / "services" / service / "k8s/k8s.yaml").read_text(encoding="utf-8")):
            if not doc:
                continue
            if doc["kind"] == "Deployment":
                container = doc["spec"]["template"]["spec"]["containers"][0]
                container["image"] = image
                if service != "exchange":
                    container.setdefault("env", []).append({"name": "JAVA_TOOL_OPTIONS", "value": "-XX:MaxRAMPercentage=65.0"})
                doc["spec"]["template"]["spec"]["nodeSelector"] = {"kubernetes.io/arch": "amd64"}
                # No surge on the current small node group. This can briefly interrupt service.
                doc["spec"]["strategy"] = {"type": "RollingUpdate", "rollingUpdate": {"maxSurge": 0, "maxUnavailable": 1}}
            documents.append(doc)
    for doc in documents:
        doc["metadata"]["namespace"] = namespace
    return documents


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--images", required=True)
    parser.add_argument("--output", default="artifacts/eks.local.yaml")
    args = parser.parse_args()
    try:
        result = render(json.loads(Path(args.environment).read_text(encoding="utf-8-sig")),
                        json.loads(Path(args.images).read_text(encoding="utf-8-sig")))
    except (ValueError, KeyError) as error:
        parser.error(str(error))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump_all(result, sort_keys=False), encoding="utf-8")
    print(f"Rendered {len(result)} application resources to {output}; no Secrets included")
