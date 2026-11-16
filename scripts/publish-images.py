#!/usr/bin/env python3
"""Publish the six locally tested images to existing ECR repositories and record digests."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ("account", "product", "auth", "exchange", "order", "gateway")


def capture(*args):
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def publish(config, tag, create_repositories=False):
    region, account = config["region"], config["account_id"]
    identity = json.loads(capture("aws", "sts", "get-caller-identity", "--output", "json"))
    if identity["Account"] != account:
        raise ValueError("AWS identity does not match the configured account")
    registry = f"{account}.dkr.ecr.{region}.amazonaws.com"
    repositories = set(json.loads(capture("aws", "ecr", "describe-repositories", "--region", region,
                                         "--query", "repositories[].repositoryName", "--output", "json")))
    missing = {f"{service}-service" for service in SERVICES} - repositories
    if missing and not create_repositories:
        raise ValueError(f"Missing ECR repositories: {sorted(missing)}; use --create-repositories to create them")
    # Finish all read-only local checks before publishing anything.
    for service in SERVICES:
        capture("docker", "image", "inspect", f"store/{service}-service:dev")
    for name in sorted(missing):
        capture("aws", "ecr", "create-repository", "--region", region, "--repository-name", name,
                "--image-tag-mutability", "IMMUTABLE", "--image-scanning-configuration", "scanOnPush=true")
    images = {}
    # Do not persist an ECR authentication token in the user's Docker configuration.
    with tempfile.TemporaryDirectory(prefix="store-ecr-") as temporary:
        password = capture("aws", "ecr", "get-login-password", "--region", region)
        subprocess.run(["docker", "--config", temporary, "login", "--username", "AWS", "--password-stdin", registry],
                       input=password, text=True, check=True, stdout=subprocess.DEVNULL)
        del password
        for service in SERVICES:
            image = f"{registry}/{service}-service:{tag}"
            subprocess.run(["docker", "tag", f"store/{service}-service:dev", image], check=True)
            subprocess.run(["docker", "--config", temporary, "push", image], check=True)
            digest = capture("aws", "ecr", "describe-images", "--region", region,
                             "--repository-name", f"{service}-service", "--image-ids", f"imageTag={tag}",
                             "--query", "imageDetails[0].imageDigest", "--output", "text")
            images[service] = f"{registry}/{service}-service@{digest}"
    return images


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--tag", default=datetime.now(timezone.utc).strftime("review-%Y%m%d%H%M%S"))
    parser.add_argument("--create-repositories", action="store_true")
    parser.add_argument("--output", default="artifacts/images.local.json")
    args = parser.parse_args()
    result = publish(json.loads(Path(args.environment).read_text(encoding="utf-8-sig")), args.tag, args.create_repositories)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Published six images; digests saved to {output}")
