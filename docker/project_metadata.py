"""Validate the gateway wrapper, upstream and Helm artifact identities."""

from __future__ import annotations

import hashlib
import json
import tarfile
import tomllib
from pathlib import Path

import typer
import yaml
from pydantic import BaseModel, ConfigDict, Field

from docker.release import Source

app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)


class ChartVersion(BaseModel):
    """Helm owns SemVer validation; this boundary requires typed metadata."""

    model_config = ConfigDict(strict=True)
    version: str = Field(min_length=1)
    app_version: str = Field(alias="appVersion", min_length=1)


class GatewayVersions(BaseModel):
    model_config = ConfigDict(strict=True)
    wrapper: str
    traefik: str
    verification_tools: str = Field(serialization_alias="verificationTools")


def versions() -> GatewayVersions:
    chart = ChartVersion.model_validate(
        yaml.safe_load(Path("deploy/chart/Chart.yaml").read_text())
    )
    upstream = json.loads(Path("versions.lock.json").read_text())
    verification = tomllib.loads(Path("pyproject.toml").read_text())["project"]
    if chart.app_version != upstream["traefikVersion"]:
        raise ValueError("Helm appVersion and upstream lock differ")
    return GatewayVersions(
        wrapper=chart.version,
        traefik=chart.app_version,
        verification_tools=verification["version"],
    )


@app.command("release-check")
def release_check() -> None:
    expected = versions()
    source = Source.model_validate_json(Path("coverage/source.json").read_text())
    if source.dirty or source.commit is None:
        raise ValueError("Release readiness requires clean reviewed source")
    image = json.loads(Path("coverage/runtime-image.json").read_text())[0]
    labels = image["Config"]["Labels"]
    if (
        labels["org.opencontainers.image.version"] != expected.wrapper
        or labels["org.opencontainers.image.revision"] != source.commit
    ):
        raise ValueError("Runtime image version/source mismatch")
    if Path("coverage/tested-image-id.txt").read_text().strip() != image["Id"]:
        raise ValueError("Runtime differs from the actual proxy acceptance image")
    if Path("coverage/source-commit.txt").read_text().strip() != source.commit:
        raise ValueError("Proxy acceptance source mismatch")
    archive = Path("coverage/chart") / f"poker-gateway-{expected.wrapper}.tgz"
    with tarfile.open(archive) as chart:
        stream = chart.extractfile("poker-gateway/Chart.yaml")
        if stream is None:
            raise ValueError("Packaged Helm chart metadata missing")
        archived = ChartVersion.model_validate(yaml.safe_load(stream))
        if (
            archived.version != expected.wrapper
            or archived.app_version != expected.traefik
        ):
            raise ValueError("Packaged Helm chart version/appVersion mismatch")
    records = [
        {
            "path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "version": expected.wrapper,
        }
        for path in [archive, Path("coverage/runtime-image.json")]
    ]
    Path("coverage/artifacts.json").write_text(json.dumps(records, indent=2) + "\n")
    Path("coverage/versions.json").write_text(
        expected.model_dump_json(by_alias=True, indent=2) + "\n"
    )
    print("Gateway wrapper, Traefik, Helm and tested OCI image identities agree.")


class OfflineInputs(BaseModel):
    """Previously accepted immutable images and chart bytes for this source."""

    model_config = ConfigDict(strict=True, extra="forbid")
    source: Source
    runtime_image_id: str = Field(pattern=r"^sha256:[a-f0-9]{64}$")
    fixture_image_id: str = Field(pattern=r"^sha256:[a-f0-9]{64}$")
    chart_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


def offline_inputs() -> OfflineInputs:
    expected = versions()
    archive = Path("coverage/chart") / f"poker-gateway-{expected.wrapper}.tgz"
    image = json.loads(Path("coverage/runtime-image.json").read_text())[0]
    return OfflineInputs.model_validate(
        {
            "source": json.loads(Path("coverage/source.json").read_text()),
            "runtime_image_id": image["Id"],
            "fixture_image_id": Path("coverage/fixture-image-id.txt")
            .read_text()
            .strip(),
            "chart_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        }
    )


@app.command("capture-offline")
def capture_offline() -> None:
    """Capture native inputs only after successful proxy and artifact validation."""
    release_check()
    Path("coverage/gateway-cache.json").write_text(
        offline_inputs().model_dump_json(by_alias=True, indent=2) + "\n"
    )


@app.command("check-offline")
def check_offline() -> None:
    """Reject replaced images, source changes and modified chart bytes."""
    saved = OfflineInputs.model_validate_json(
        Path("coverage/gateway-cache.json").read_text()
    )
    if saved != offline_inputs():
        raise ValueError("Prepared gateway source, images or chart bytes changed")
    release_check()


@app.command("version")
def show_version() -> None:
    """Show the independently owned wrapper, upstream and tool versions."""
    typer.echo(versions().model_dump_json(by_alias=True, indent=2))


if __name__ == "__main__":
    app()
