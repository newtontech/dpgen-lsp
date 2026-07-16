import json
import re
from pathlib import Path

import dpgen_lsp

ROOT = Path(__file__).resolve().parents[1]
RELEASE_VERSION = "0.1.2"


def _project_version() -> str:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    assert match is not None
    return match.group(1)


def test_version_file_matches_pyproject() -> None:
    assert _project_version() == RELEASE_VERSION
    assert dpgen_lsp.__version__ == RELEASE_VERSION
    assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == RELEASE_VERSION


def test_changelog_mentions_current_version() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## {_project_version()} -" in changelog
    assert "official-docs pipeline" in changelog
    assert "OpenQC capability metadata" in changelog


def test_capability_manifest_is_stable() -> None:
    manifest = json.loads((ROOT / "lsp-capabilities.json").read_text(encoding="utf-8"))
    assert manifest["maturity"] == "stable"
    assert manifest["releaseVersion"] == RELEASE_VERSION
    assert manifest["releaseTag"] == f"v{RELEASE_VERSION}"
    assert manifest["repository"] == "newtontech/dpgen-lsp"
    assert manifest["dpgenVersionSupport"]["completeReleaseTagIndex"] is True


def test_project_urls_point_to_release_source_repository() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "https://github.com/newtontech/dpgen-lsp" in pyproject
    assert "https://github.com/SchrodingersCattt/dpgen-lsp" not in pyproject


def test_release_workflow_uses_tag_only_oidc_trusted_publishing() -> None:
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert re.search(r"push:\s*\n\s+tags:\s*\[?\"v\*\"\]?", workflow)
    assert "workflow_dispatch:" not in workflow
    assert "environment: pypi" in workflow
    assert "id-token: write" in workflow
    assert "pypa/gh-action-pypi-publish@release/v1" in workflow
    assert "python -m build" in workflow
    assert "python -m twine check dist/*" in workflow
    assert "scripts/smoke_wheel.sh dist/*.whl" in workflow
    assert "Tag version does not match pyproject.toml" in workflow


def test_release_docs_and_fresh_wheel_smoke_cover_acceptance_surface() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    smoke = (ROOT / "scripts" / "smoke_wheel.sh").read_text(encoding="utf-8")

    assert f"Current release: `{RELEASE_VERSION}`" in readme
    assert "Trusted Publishing" in readme
    assert f"## {RELEASE_VERSION} - 2026-07-16" in changelog
    for required in (
        "dpgen-lsp --help",
        "dpgen-lsp-tool check",
        "dpgen-lsp-tool parse-log",
        "tests/fixtures/valid/param.json",
        "tests/fixtures/invalid/param.json",
        "tests/fixtures/logs/missing_files.log",
    ):
        assert required in smoke
