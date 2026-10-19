"""Contract checks for all owned routing/security rules, not Traefik source coverage."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_file_provider_has_no_socket_admin_retry_or_unbounded_body() -> None:
    static = yaml.safe_load((ROOT / "config/traefik.yaml").read_text())
    routes = yaml.safe_load((ROOT / "config/dynamic/routes.yaml").read_text())
    assert set(static["providers"]) == {"file"}
    assert static["api"] == {"dashboard": False, "insecure": False}
    assert static["accessLog"]["fields"]["headers"]["defaultMode"] == "drop"
    assert all(
        not value.get("forwardedHeaders", {}).get("insecure", False)
        for value in static["entryPoints"].values()
    )
    middlewares = routes["http"]["middlewares"]
    assert all("retry" not in value for value in middlewares.values())
    assert middlewares["bounded-body"]["buffering"]["maxRequestBodyBytes"] == 1048576
    for name in (
        "authService",
        "accountsService",
        "virtualMoney",
        "pokerService",
        "cryptoService",
    ):
        matching = [
            router
            for router in routes["http"]["routers"].values()
            if f"/api/{name}" in router["rule"]
        ]
        assert len(matching) == 2
        assert all("bounded-body" in router["middlewares"] for router in matching)
        assert all(
            "remove-client-request-id" in router["middlewares"] for router in matching
        )
    assert routes["tls"]["options"]["default"]["minVersion"] == "VersionTLS13"


def test_context_and_chart_pin_only_intended_artifacts() -> None:
    ignored = (ROOT / ".dockerignore").read_text().splitlines()
    assert ignored == [
        "*",
        "!Dockerfile",
        "!config/",
        "!config/**",
        ".vscode/",
        ".serena/",
    ]
    lock = json.loads((ROOT / "versions.lock.json").read_text())
    chart = ROOT / f"deploy/chart/charts/traefik-{lock['chartVersion']}.tgz"
    assert hashlib.sha256(chart.read_bytes()).hexdigest() == lock["chartSha256"]
    assert lock["gatewayApiVersion"] == "v1.6.3"
    values = yaml.safe_load((ROOT / "deploy/chart/values.yaml").read_text())
    assert values["traefik"]["image"]["digest"] in lock["image"]
    assert values["traefik"]["providers"]["kubernetesGateway"]["enabled"]
    assert not values["traefik"]["providers"]["kubernetesIngress"]["enabled"]
    assert not values["traefik"]["providers"]["kubernetesCRD"]["allowCrossNamespace"]
    assert values["traefik"]["securityContext"]["readOnlyRootFilesystem"]
    assert values["traefik"]["service"]["spec"]["type"] == "ClusterIP"
    compose = yaml.safe_load((ROOT / "compose.yaml").read_text())
    gateway = compose["services"]["gateway"]
    assert gateway["read_only"] and gateway["cap_drop"] == ["ALL"]
    assert all(port.startswith("127.0.0.1:") for port in gateway["ports"])


def test_gateway_tls_policy_matches_the_file_provider() -> None:
    policy = yaml.safe_load(
        (ROOT / "deploy/chart/templates/tls-options.yaml").read_text()
    )
    assert policy["kind"] == "TLSOption" and policy["metadata"]["name"] == "default"
    assert policy["spec"] == {"minVersion": "VersionTLS13", "sniStrict": True}
