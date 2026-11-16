#!/usr/bin/env python3
"""Save a read-only AWS inventory and official unit prices without credentials or Secrets."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import tempfile


def aws(*args):
    result = subprocess.run(["aws", *args, "--output", "json"], text=True, capture_output=True)
    if result.returncode:
        return {"error": result.stderr.strip()}
    return json.loads(result.stdout)


def price(service, fields):
    filters = [{"Type": "TERM_MATCH", "Field": field, "Value": value} for field, value in fields.items()]
    # CLI file input avoids platform-specific shell quoting of locations with spaces.
    with tempfile.TemporaryDirectory(prefix="store-prices-") as temporary:
        path = Path(temporary) / "filters.json"
        path.write_text(json.dumps(filters), encoding="utf-8")
        result = aws("pricing", "get-products", "--region", "us-east-1", "--service-code", service,
                     "--filters", f"file://{path.as_posix()}", "--max-results", "100")
    if "error" in result:
        return result
    prices = []
    for encoded in result.get("PriceList", []):
        product = json.loads(encoded)
        for term in product.get("terms", {}).get("OnDemand", {}).values():
            for dimension in term.get("priceDimensions", {}).values():
                prices.append({key: dimension[key] for key in ("description", "unit", "pricePerUnit")})
    return prices


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", default="us-east-2")
    parser.add_argument("--cluster", default="eks-store")
    parser.add_argument("--output", default="artifacts/aws-inventory.local.json")
    args = parser.parse_args()
    region = args.region
    result = {"captured_at": datetime.now(timezone.utc).isoformat(), "region": region}
    queries = {
        "cluster": ("eks", "describe-cluster", "--name", args.cluster, "--query", "cluster.{name:name,status:status,version:version}"),
        "nodegroup": ("eks", "describe-nodegroup", "--cluster-name", args.cluster, "--nodegroup-name", "default", "--query", "nodegroup.{scaling:scalingConfig,types:instanceTypes,disk:diskSize}"),
        "rds": ("rds", "describe-db-instances", "--query", "DBInstances[].{name:DBInstanceIdentifier,status:DBInstanceStatus,class:DBInstanceClass,storage:AllocatedStorage,multi_az:MultiAZ}"),
        "nat": ("ec2", "describe-nat-gateways", "--filter", "Name=state,Values=available", "--query", "NatGateways[].{id:NatGatewayId,vpc:VpcId}"),
        "load_balancers": ("elbv2", "describe-load-balancers", "--query", "LoadBalancers[].{name:LoadBalancerName,type:Type}"),
    }
    for key, query in queries.items():
        result[key] = aws(*query, "--region", region)
    if region == "us-east-2":
        result["unit_prices"] = {
            "t2.small": price("AmazonEC2", {"regionCode": region, "instanceType": "t2.small", "operatingSystem": "Linux", "tenancy": "Shared", "preInstalledSw": "NA", "capacitystatus": "Used"}),
            "nat": price("AmazonEC2", {"regionCode": region, "productFamily": "NAT Gateway"}),
            "rds.t4g.micro": price("AmazonRDS", {"regionCode": region, "instanceType": "db.t4g.micro", "databaseEngine": "PostgreSQL", "deploymentOption": "Single-AZ"}),
        }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Inventory and prices saved to {output}")
