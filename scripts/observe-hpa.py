#!/usr/bin/env python3
"""Capture HPA and ready replicas through load and cooldown using an explicit context."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--context", default="store-local")
parser.add_argument("--namespace", default="store-demo")
parser.add_argument("--seconds", type=int, default=660)
parser.add_argument("--output", default="artifacts/hpa-timeline.local.jsonl")
args = parser.parse_args()
output = Path(args.output)
output.parent.mkdir(parents=True, exist_ok=True)
kubectl = ["kubectl", "--context", args.context, "--request-timeout=15s", "-n", args.namespace]
deadline = time.monotonic() + args.seconds
with output.open("w", encoding="utf-8") as stream:
    while time.monotonic() < deadline:
        def read(*command):
            return json.loads(subprocess.check_output([*kubectl, *command, "-o", "json"], text=True))
        hpa = read("get", "hpa", "gateway")["status"]
        deployment = read("get", "deployment", "gateway")["status"]
        job = read("get", "job", "store-load")["status"]
        record = {"timestamp": datetime.now(timezone.utc).isoformat(),
                  "current": hpa.get("currentReplicas"), "desired": hpa.get("desiredReplicas"),
                  "ready": deployment.get("readyReplicas", 0), "metrics": hpa.get("currentMetrics", []),
                  "job_succeeded": job.get("succeeded", 0), "job_failed": job.get("failed", 0)}
        stream.write(json.dumps(record) + "\n")
        stream.flush()
        if record["job_failed"]:
            raise SystemExit("Load Job failed; timeline saved")
        if record["job_succeeded"] and record["current"] == record["desired"] == record["ready"] == 1:
            print("Load completed and gateway returned to one ready replica; timeline saved")
            break
        time.sleep(5)
