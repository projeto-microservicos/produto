#!/usr/bin/env python3
"""Run the complete local project without installing Java or k6 on the host."""
import argparse
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ("account", "product", "auth", "gateway", "order")


def run(*args, **kwargs):
    subprocess.run(args, cwd=ROOT, check=True, **kwargs)


def init():
    target = ROOT / ".env"
    if target.exists():
        print(".env already exists; preserved")
    else:
        template = (ROOT / ".env.example").read_text(encoding="utf-8")
        settings = re.sub("GENERATE_ME", lambda _: secrets.token_urlsafe(48), template)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            out.write(settings)
        print("Created local .env; secrets are not printed")
    (ROOT / "artifacts").mkdir(exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["init", "doctor", "up", "down", "status", "logs", "smoke", "test", "load"])
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--profile", choices=["smoke", "ramp"], default="smoke")
    parser.add_argument("--monitoring", action="store_true")
    args = parser.parse_args()
    compose = ["docker", "compose"]
    if args.command == "init":
        init()
    elif args.command == "doctor":
        for service in (*SERVICES, "exchange"):
            if not (ROOT / "services" / service / "Dockerfile").is_file():
                parser.error("Initialize submodules with git submodule update --init --recursive")
        run("docker", "info", "--format", "{{.OSType}} {{.ServerVersion}}")
        run(*compose, "config", "--quiet")
    elif args.command == "up":
        init()
        if args.monitoring:
            compose += ["--profile", "monitoring"]
        run(*compose, "up", "--build", "-d", "--wait", "--wait-timeout", "360")
    elif args.command == "down":
        run(*compose, "--profile", "monitoring", "--profile", "load", "down")
    elif args.command in {"status", "logs"}:
        run(*compose, "ps" if args.command == "status" else "logs", *( ["--tail", "80"] if args.command == "logs" else []))
    elif args.command == "smoke":
        run(sys.executable, "scripts/smoke.py", "--base-url", args.base_url)
    elif args.command == "test":
        run(sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v")
        # Bind paths are separate arguments: spaces in Windows paths are supported.
        for service in SERVICES:
            run("docker", "run", "--rm", "--mount", f"type=bind,source={ROOT / 'services' / service},target=/workspace",
                "--mount", "type=volume,source=store-maven-cache,target=/root/.m2", "-w", "/workspace",
                "maven:3.9-eclipse-temurin-25", "mvn", "-B", "-ntp", "verify")
        run("docker", "run", "--rm", "--mount", f"type=bind,source={ROOT},target=/workspace,readonly",
            "-w", "/workspace", "-e", "PYTHONPATH=/workspace/services/exchange", "python:3.12-slim",
            "python", "scripts/test-python.py")
    elif args.command == "load":
        init()
        env = dict(os.environ, LOAD_PROFILE=args.profile)
        run(*compose, "--profile", "load", "run", "--rm", "k6", env=env)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
