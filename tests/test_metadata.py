"""Version/readiness boundaries use synthetic local artifacts, not Docker mocks."""

from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from docker.project_metadata import app

COMMIT = "a" * 40
RUNNER = CliRunner()


def chart_archive(root: Path, app_version: str) -> None:
    payload = f"version: 0.2.0-dev.0\nappVersion: {app_version}\n".encode()
    with tarfile.open(
        root / "coverage/chart/poker-gateway-0.2.0-dev.0.tgz", "w:gz"
    ) as archive:
        info = tarfile.TarInfo("poker-gateway/Chart.yaml")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))


@pytest.fixture
def metadata_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "deploy/chart").mkdir(parents=True)
    (tmp_path / "coverage/chart").mkdir(parents=True)
    (tmp_path / "deploy/chart/Chart.yaml").write_text(
        "version: 0.2.0-dev.0\nappVersion: 3.7.15\n"
    )
    (tmp_path / "versions.lock.json").write_text(
        json.dumps({"traefikVersion": "3.7.15"})
    )
    (tmp_path / "pyproject.toml").write_text('[project]\nversion="0.1.0.dev0"\n')
    (tmp_path / "coverage/source.json").write_text(
        json.dumps({"commit": COMMIT, "dirty": False, "contentSha256": "b" * 64})
    )
    (tmp_path / "coverage/runtime-image.json").write_text(
        json.dumps(
            [
                {
                    "Id": "sha256:fixture",
                    "Config": {
                        "Labels": {
                            "org.opencontainers.image.version": "0.2.0-dev.0",
                            "org.opencontainers.image.revision": COMMIT,
                        }
                    },
                }
            ]
        )
    )
    (tmp_path / "coverage/tested-image-id.txt").write_text("sha256:fixture\n")
    (tmp_path / "coverage/source-commit.txt").write_text(COMMIT + "\n")
    chart_archive(tmp_path, "3.7.15")
    return tmp_path


def test_native_versions_remain_independent(metadata_tree: Path) -> None:
    result = RUNNER.invoke(app, ["version"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {
        "wrapper": "0.2.0-dev.0",
        "traefik": "3.7.15",
        "verificationTools": "0.1.0.dev0",
    }


def test_release_metadata_records_validated_artifacts(metadata_tree: Path) -> None:
    result = RUNNER.invoke(app, ["release-check"])
    assert result.exit_code == 0, result.output
    assert len(json.loads((metadata_tree / "coverage/artifacts.json").read_text())) == 2


def test_archived_app_version_must_match_upstream(metadata_tree: Path) -> None:
    chart_archive(metadata_tree, "3.0.0")
    result = RUNNER.invoke(app, ["release-check"])
    assert result.exit_code != 0
    assert "version/appVersion" in str(result.exception)


def test_proxy_source_receipt_must_match(metadata_tree: Path) -> None:
    (metadata_tree / "coverage/source-commit.txt").write_text("c" * 40)
    result = RUNNER.invoke(app, ["release-check"])
    assert result.exit_code != 0
    assert "Proxy acceptance source" in str(result.exception)


def test_source_identity_rejects_string_booleans(metadata_tree: Path) -> None:
    (metadata_tree / "coverage/source.json").write_text(
        json.dumps({"commit": COMMIT, "dirty": "false", "contentSha256": "b" * 64})
    )
    result = RUNNER.invoke(app, ["release-check"])
    assert result.exit_code != 0
    assert not (metadata_tree / "coverage/artifacts.json").exists()
