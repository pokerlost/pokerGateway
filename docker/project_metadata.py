"""Validate the gateway wrapper, upstream and Helm artifact identities."""

from __future__ import annotations

import hashlib
import json
import sys
import tarfile
import tomllib
from pathlib import Path
from typing import Any

import yaml


def versions() -> dict[str, Any]:
    chart = yaml.safe_load(Path("deploy/chart/Chart.yaml").read_text())
    upstream = json.loads(Path("versions.lock.json").read_text())
    verification = tomllib.loads(Path("pyproject.toml").read_text())["project"]
    if chart["appVersion"] != upstream["traefikVersion"]:
        raise ValueError("Helm appVersion and upstream lock differ")
    return {
        "wrapper": chart["version"],
        "traefik": chart["appVersion"],
        "verificationTools": verification["version"],
    }


def release_check() -> None:
    expected = versions()
    source = json.loads(Path("coverage/source.json").read_text())
    if source["dirty"]:
        raise ValueError("Release readiness requires clean reviewed source")
    image = json.loads(Path("coverage/runtime-image.json").read_text())[0]
    labels = image["Config"]["Labels"]
    if (
        labels["org.opencontainers.image.version"] != expected["wrapper"]
        or labels["org.opencontainers.image.revision"] != source["commit"]
    ):
        raise ValueError("Runtime image version/source mismatch")
    if Path("coverage/tested-image-id.txt").read_text().strip() != image["Id"]:
        raise ValueError("Runtime differs from the actual proxy acceptance image")
    archive = Path("coverage/chart") / f"poker-gateway-{expected['wrapper']}.tgz"
    with tarfile.open(archive) as chart:
        stream = chart.extractfile("poker-gateway/Chart.yaml")
        if stream is None or yaml.safe_load(stream)["version"] != expected["wrapper"]:
            raise ValueError("Packaged Helm chart version mismatch")
    records = [
        {
            "path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "version": expected["wrapper"],
        }
        for path in [archive, Path("coverage/runtime-image.json")]
    ]
    Path("coverage/artifacts.json").write_text(json.dumps(records, indent=2) + "\n")
    Path("coverage/versions.json").write_text(json.dumps(expected, indent=2) + "\n")
    print("Gateway wrapper, Traefik, Helm and tested OCI image identities agree.")


if __name__ == "__main__":
    if sys.argv[1] == "version":
        print(json.dumps(versions(), indent=2))
    elif sys.argv[1] == "release-check":
        release_check()
    else:
        raise ValueError("Expected version or release-check")
