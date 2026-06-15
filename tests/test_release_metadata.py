import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _project_version() -> str:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    assert match is not None
    return match.group(1)


def test_version_file_matches_pyproject() -> None:
    assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == _project_version()


def test_changelog_mentions_current_version() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## {_project_version()} -" in changelog
    assert "official-docs pipeline" in changelog
    assert "OpenQC capability metadata" in changelog


def test_capability_manifest_is_stable() -> None:
    manifest = json.loads((ROOT / "lsp-capabilities.json").read_text(encoding="utf-8"))
    assert manifest["maturity"] == "stable"
    assert manifest["dpgenVersionSupport"]["completeReleaseTagIndex"] is True
