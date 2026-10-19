"""Execute Traefik HTTP/TLS/WebSocket acceptance in owned Docker resources."""

from __future__ import annotations

import json
import os
import ssl
import subprocess
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
import yaml
from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]


def docker(*arguments: str) -> str:
    return subprocess.check_output(
        ["docker", *arguments], text=True, stderr=subprocess.STDOUT, timeout=60
    ).strip()


@dataclass(frozen=True)
class Proxy:
    url: str
    tls_url: str
    identifier: str
    ca: Path
    upstreams: tuple[str, ...]


@pytest.fixture(scope="module")
def proxy(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Proxy]:
    directory = tmp_path_factory.mktemp("gateway")
    network = "codex-gateway-" + uuid4().hex[:12]
    containers: list[str] = []
    cert, key = directory / "cert.pem", directory / "key.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-days",
            "1",
            "-subj",
            "/CN=localhost",
            "-addext",
            "subjectAltName=DNS:localhost,IP:127.0.0.1",
        ],
        capture_output=True,
        check=True,
        timeout=15,
    )
    # These synthetic fixture keys remain under pytest's private parent directory;
    # only their exact files are mounted into the non-root test container.
    os.chmod(key, 0o444)
    os.chmod(cert, 0o444)
    extra = directory / "acceptance.yaml"
    extra.write_text(
        yaml.safe_dump(
            {
                "http": {
                    "routers": {
                        "acceptance": {
                            "rule": "PathPrefix(`/technical/`)",
                            "priority": 1000,
                            "entryPoints": ["web"],
                            "service": "echo",
                            "middlewares": [
                                "security",
                                "bounded-body",
                                "remove-client-request-id",
                                "technical-prefix",
                            ],
                        },
                        "acceptance-tls": {
                            "rule": "PathPrefix(`/technical/`)",
                            "priority": 1000,
                            "entryPoints": ["websecure"],
                            "tls": {},
                            "service": "echo",
                            "middlewares": [
                                "security",
                                "bounded-body",
                                "technical-prefix",
                            ],
                        },
                        "acceptance-missing": {
                            "rule": "Path(`/missing-upstream`)",
                            "priority": 1000,
                            "entryPoints": ["web"],
                            "service": "missing",
                        },
                    },
                    "middlewares": {
                        "technical-prefix": {
                            "stripPrefix": {"prefixes": ["/technical"]}
                        }
                    },
                    "services": {
                        "echo": {
                            "loadBalancer": {
                                "servers": [
                                    {"url": "http://fixture-one:8080"},
                                    {"url": "http://fixture-two:8080"},
                                ]
                            }
                        },
                        "missing": {
                            "loadBalancer": {"servers": [{"url": "http://127.0.0.1:1"}]}
                        },
                    },
                },
                "tls": {
                    "certificates": [
                        {
                            "certFile": "/run/fixture-tls/cert.pem",
                            "keyFile": "/run/fixture-tls/key.pem",
                        }
                    ]
                },
            }
        )
    )
    os.chmod(extra, 0o444)
    docker(
        "network", "create", "--label", "io.codex.owner=platform-task-gateway", network
    )
    try:
        for name in ("one", "two"):
            containers.append(
                docker(
                    "run",
                    "--detach",
                    "--read-only",
                    "--network",
                    network,
                    "--network-alias",
                    "fixture-" + name,
                    "--cap-drop",
                    "ALL",
                    "--security-opt",
                    "no-new-privileges:true",
                    "--env",
                    "FIXTURE_NAME=" + name,
                    "pokergateway:fixture",
                )
            )
        identifier = docker(
            "run",
            "--detach",
            "--read-only",
            "--network",
            network,
            "--user",
            "65532:65532",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges:true",
            "--publish",
            "127.0.0.1::8080",
            "--publish",
            "127.0.0.1::8443",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=32m",
            "--mount",
            f"type=bind,source={extra},target=/etc/traefik/dynamic/acceptance.yaml,readonly",
            "--mount",
            f"type=bind,source={cert},target=/run/fixture-tls/cert.pem,readonly",
            "--mount",
            f"type=bind,source={key},target=/run/fixture-tls/key.pem,readonly",
            "pokergateway:candidate",
        )
        containers.append(identifier)
        http_port = docker("port", identifier, "8080/tcp").rsplit(":", 1)[1]
        tls_port = docker("port", identifier, "8443/tcp").rsplit(":", 1)[1]
        result = Proxy(
            f"http://127.0.0.1:{http_port}",
            f"https://localhost:{tls_port}",
            identifier,
            cert,
            tuple(containers[:-1]),
        )
        with httpx.Client(trust_env=False, timeout=2) as client:
            for _ in range(100):
                try:
                    if client.get(result.url + "/technical/ready").status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                time.sleep(0.1)
            else:
                raise RuntimeError(
                    "Traefik readiness failed: " + docker("logs", identifier)[-2000:]
                )
        yield result
    finally:
        for identifier in reversed(containers):
            docker("rm", "--force", identifier)
        docker("network", "rm", network)


def test_real_version_security_readiness_and_balancing(proxy: Proxy) -> None:
    assert "3.7.15" in docker("exec", proxy.identifier, "traefik", "version")
    health = json.loads(docker("inspect", proxy.identifier))[0]["Config"][
        "Healthcheck"
    ]["Test"]
    assert health[0] == "CMD"
    docker("exec", proxy.identifier, *health[1:])
    with httpx.Client(trust_env=False, timeout=5) as client:
        replies = [client.get(proxy.url + "/technical/echo") for _ in range(20)]
        assert all(reply.status_code == 200 for reply in replies)
        assert {reply.json()["fixture"] for reply in replies} == {"one", "two"}
        assert replies[0].headers["x-content-type-options"] == "nosniff"
        assert "'wasm-unsafe-eval'" in replies[0].headers["content-security-policy"]
        assert "'unsafe-eval'" not in replies[0].headers["content-security-policy"]
        assert client.get(proxy.url + "/api/unknown").status_code == 404
        assert client.get(proxy.url + "/api/raw/dashboard").status_code == 404
        assert client.get(proxy.url + "/realtime").status_code == 404
        assert client.get(proxy.url + "/missing-upstream").status_code == 502
    inspected = json.loads(docker("inspect", proxy.identifier))[0]
    assert inspected["Config"]["User"] == "65532:65532"
    assert inspected["HostConfig"]["ReadonlyRootfs"]
    assert not any(
        "docker.sock" in mount["Destination"] for mount in inspected["Mounts"]
    )


def test_headers_body_limit_and_no_mutation_retry(proxy: Proxy) -> None:
    with httpx.Client(trust_env=False, timeout=5) as client:
        response = client.post(
            proxy.url + "/technical/echo",
            content=b"payload",
            headers={
                "Host": "gateway.example.invalid",
                "Authorization": "Bearer synthetic-validation-token",
                "X-Request-Id": "client-supplied-id",
                "X-Forwarded-Host": "untrusted.invalid",
                "X-Forwarded-Proto": "https",
                "X-Forwarded-For": "203.0.113.255",
            },
        )
        assert response.status_code == 200
        value = response.json()
        assert value["host"] == "gateway.example.invalid"
        assert value["authorization"] == "Bearer synthetic-validation-token"
        assert value["body_size"] == 7 and value["path"] == "/echo"
        assert value["client_id"] is None
        assert value["forwarded_host"] != "untrusted.invalid"
        assert value["forwarded_proto"] == "http"
        assert "203.0.113.255" not in value["forwarded_for"]
        assert (
            client.post(
                proxy.url + "/technical/echo", content=b"x" * 1048577
            ).status_code
            == 413
        )
        before = sum(
            client.get(proxy.url + "/technical/count").json()["failed_posts"]
            for _ in range(2)
        )
        assert client.post(proxy.url + "/technical/fail").status_code == 503
        after = sum(
            client.get(proxy.url + "/technical/count").json()["failed_posts"]
            for _ in range(2)
        )
        assert after - before == 1
    assert "synthetic-validation-token" not in docker("logs", proxy.identifier)
    assert "client-supplied-id" not in docker("logs", proxy.identifier)


def test_real_https_and_websockets_keep_one_upstream_per_connection(
    proxy: Proxy,
) -> None:
    context = ssl.create_default_context(cafile=str(proxy.ca))
    with httpx.Client(trust_env=False, verify=context) as client:
        assert client.get(proxy.tls_url + "/technical/echo").status_code == 200
    for base, secure in (
        (proxy.url.replace("http:", "ws:"), False),
        (proxy.tls_url.replace("https:", "wss:"), True),
    ):
        with connect(
            base + "/technical/ws",
            ssl=context if secure else None,
            proxy=None,
            open_timeout=5,
            close_timeout=3,
        ) as socket:
            owners = set()
            for index in range(5):
                socket.send(f"message-{index}")
                value = json.loads(socket.recv())
                assert value["echo"] == f"message-{index}"
                owners.add(value["fixture"])
            assert len(owners) == 1
            socket.send(b"binary")
            assert socket.recv() == b"binary"
        assert socket.close_code == 1000


def test_one_failed_upstream_is_visible_without_replaying_requests(
    proxy: Proxy,
) -> None:
    docker("stop", "--time", "5", proxy.upstreams[0])
    try:
        with httpx.Client(trust_env=False, timeout=5) as client:
            statuses = {
                client.get(proxy.url + "/technical/echo").status_code for _ in range(12)
            }
        assert statuses == {200, 502}
    finally:
        docker("start", proxy.upstreams[0])
        with httpx.Client(trust_env=False, timeout=2) as client:
            for _ in range(50):
                replies = [
                    client.get(proxy.url + "/technical/ready").status_code
                    for _ in range(2)
                ]
                if replies == [200, 200]:
                    break
                time.sleep(0.1)
            else:
                raise AssertionError("Restarted fixture did not recover")


def test_sigterm_drains_an_inflight_request_and_exits_within_the_bound(
    proxy: Proxy,
) -> None:
    with (
        httpx.Client(trust_env=False, timeout=20) as client,
        ThreadPoolExecutor(max_workers=1) as pool,
    ):
        before = sum(
            client.get(proxy.url + "/technical/count").json()["slow_requests"]
            for _ in range(2)
        )
        pending = pool.submit(client.get, proxy.url + "/technical/slow")
        for _ in range(100):
            started = sum(
                client.get(proxy.url + "/technical/count").json()["slow_requests"]
                for _ in range(2)
            )
            if started == before + 1:
                break
            time.sleep(0.01)
        else:
            raise AssertionError("Controlled upstream request never started")
        begin = time.monotonic()
        docker("kill", "--signal", "TERM", proxy.identifier)
        response = pending.result(timeout=5)
        assert response.status_code == 200 and response.json()["path"] == "/slow"
        assert docker("wait", proxy.identifier) == "0"
        assert time.monotonic() - begin < 20
        state = json.loads(docker("inspect", proxy.identifier))[0]["State"]
        assert not state["Running"] and not state["OOMKilled"]
