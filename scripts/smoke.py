#!/usr/bin/env python3
"""Exercise registration, JWT, products, orders, identity isolation and exchange."""
import argparse
import json
import secrets
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def smoke(base_url, live_exchange=False):
    def request(method, path, body=None, token=None, expected=200, extra_headers=None):
        headers = {"Content-Type": "application/json", **(extra_headers or {})}
        if token:
            headers["Authorization"] = "Bearer " + token
        req = Request(base_url.rstrip("/") + path,
                      data=None if body is None else json.dumps(body).encode(), headers=headers, method=method)
        try:
            with urlopen(req, timeout=15) as response:
                status, data = response.status, response.read()
        except HTTPError as error:
            status, data = error.code, error.read()
        if status != expected:
            raise RuntimeError(f"{method} {path}: expected {expected}, got {status}")
        return json.loads(data) if data else None

    def user():
        credentials = {"email": f"smoke-{secrets.token_hex(8)}@example.com", "password": secrets.token_urlsafe(18)}
        account = request("POST", "/auth/register", {"name": "Smoke test", **credentials}, expected=201)
        token = request("POST", "/auth/login", credentials)["token"]
        return account, token, credentials

    account, token, credentials = user()
    product = None
    try:
        request("GET", "/products", expected=401)
        request("GET", "/products", token="invalid.jwt", expected=401)
        request("POST", "/auth/solve", {"token": token}, expected=404)
        request("GET", "/accounts", token=token, expected=404)
        me = request("GET", "/auth/me", token=token, extra_headers={"id-account": "forged"})
        assert me["id"] == account["id"], "Gateway accepted a forged identity"
        request("POST", "/auth/login", {**credentials, "password": "wrong-password"}, expected=401)
        product = request("POST", "/products", {"name": "Smoke product", "price": 10.12, "unit": "kg"}, token, 201)
        order = request("POST", "/orders", {"items": [{"idProduct": product["id"], "quantity": 2}]}, token, 201)
        detail = request("GET", "/orders/" + order["id"], token=token)
        assert detail["id"] == order["id"]
        assert abs(float(detail["total"]) - 20.24) < 0.001, "Unexpected order total"
        _, second_token, _ = user()
        request("GET", "/orders/" + order["id"], token=second_token, expected=404)
        quote = request("GET", "/exchanges/USD/USD", token=token)
        assert quote["sell"] == 1
        if live_exchange:
            request("GET", "/orders/" + order["id"] + "?currency=BRL", token=token)
        request("POST", "/auth/logout", {}, token, 204)
        print("PASS: registration, login, JWT, protected routes, products, order total, account isolation, exchange and logout")
    finally:
        if product:
            request("DELETE", "/products/" + product["id"], token=token, expected=204)
    print("Synthetic accounts and one order remain in the test database; no credentials were saved")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--live-exchange", action="store_true", help="Also make one real provider request for BRL conversion")
    args = parser.parse_args()
    smoke(args.base_url, args.live_exchange)
