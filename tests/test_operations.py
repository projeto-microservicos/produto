"""Deployment rendering must fail before any cluster writes on invalid configuration."""
import copy
import json
from pathlib import Path
import runpy
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = runpy.run_path(str(ROOT / "scripts/render-eks.py"))
render = MODULE["render"]


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / "aws/environment.example.json").read_text())
        self.config["database_host"] = "postgres.example.internal"
        registry = "{account_id}.dkr.ecr.{region}.amazonaws.com".format(**self.config)
        self.images = {service: registry + f"/{service}-service@sha256:" + "a" * 64 for service in MODULE["SERVICES"]}

    def test_complete_internal_release_has_six_digest_deployments_and_no_secrets(self):
        docs = render(self.config, self.images)
        self.assertEqual(len([doc for doc in docs if doc["kind"] == "Deployment"]), 6)
        self.assertTrue(all(doc["metadata"]["namespace"] == "store" for doc in docs))
        self.assertFalse(any(doc["kind"] == "Secret" for doc in docs))
        self.assertNotIn("REPLACE", json.dumps(docs))
        for doc in docs:
            if doc["kind"] == "Service":
                self.assertEqual(doc["spec"].get("type", "ClusterIP"), "ClusterIP")
            if doc["kind"] == "ConfigMap" and doc["metadata"]["name"] in {"account-config", "product-config", "order-config"}:
                self.assertEqual(doc["data"]["DATABASE_SSLMODE"], "require")

    def test_missing_database_and_mutable_images_are_rejected(self):
        incomplete = copy.deepcopy(self.config)
        incomplete["database_host"] = "REPLACE_WITH_RDS_ENDPOINT"
        with self.assertRaises(ValueError):
            render(incomplete, self.images)
        self.images["gateway"] = "store/gateway-service:latest"
        with self.assertRaises(ValueError):
            render(self.config, self.images)

    def test_wrong_registry_and_public_plaintext_origin_are_rejected(self):
        images = dict(self.images, account=self.images["account"].replace(self.config["account_id"], "000000000000"))
        with self.assertRaises(ValueError):
            render(self.config, images)
        self.config["cors_origin"] = "http://public.example.com"
        with self.assertRaises(ValueError):
            render(self.config, self.images)


if __name__ == "__main__":
    unittest.main()
