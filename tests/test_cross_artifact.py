"""Tests for cross-artifact diagnostics and project-level CLI checks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_all_structured_rules_have_provenance():
    from dpgen_lsp.schema.official_rules import load_rule_index, source_provenance

    index = load_rule_index()
    provenance_ids = {item["id"] for item in source_provenance()}
    missing: list[str] = []

    for section_name in ("workflows", "machine", "crossArtifact"):
        section = index.get(section_name, {})
        if section_name == "workflows":
            for workflow in section.values():
                for code, rule in workflow.get("rules", {}).items():
                    if not rule.get("manual_ref") or rule.get("source_id") not in provenance_ids:
                        missing.append(f"workflows:{code}")
        else:
            for code, rule in section.get("rules", {}).items():
                if not rule.get("manual_ref") or rule.get("source_id") not in provenance_ids:
                    missing.append(f"{section_name}:{code}")

    assert missing == []


def test_cross_artifact_model_devi_missing():
    from dpgen_lsp.features.cross_artifact import get_cross_artifact_diagnostics

    param = _load_json(FIXTURES / "projects" / "cross-mismatch" / "param.json")
    machine = _load_json(FIXTURES / "projects" / "cross-mismatch" / "machine.json")

    diagnostics = get_cross_artifact_diagnostics(param, machine)
    codes = {item["code"] for item in diagnostics}

    assert "cross.stage.model_devi.missing" in codes
    assert all(item["manual_ref"].endswith("example-of-machine.html") for item in diagnostics)


def test_cross_artifact_valid_project_has_no_stage_gaps():
    from dpgen_lsp.features.cross_artifact import get_cross_artifact_diagnostics

    param = _load_json(FIXTURES / "projects" / "valid-run" / "param.json")
    machine = _load_json(FIXTURES / "projects" / "valid-run" / "machine.json")

    diagnostics = get_cross_artifact_diagnostics(param, machine)

    assert diagnostics == []


def test_single_file_check_fixture_invalid_param(capsys):
    from dpgen_lsp import tool

    path = FIXTURES / "invalid" / "param.json"
    assert tool.main(["check", str(path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    codes = {item["code"] for item in payload["diagnostics"]}

    assert payload["ok"] is False
    assert "mass_map.lint" in codes
    assert "model_devi_f_trust_lo.lint" in codes


def test_single_file_check_fixture_invalid_machine(capsys):
    from dpgen_lsp import tool

    path = FIXTURES / "invalid" / "machine.json"
    assert tool.main(["check", str(path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    codes = {item["code"] for item in payload["diagnostics"]}

    assert payload["ok"] is False
    assert "machine.section.type" in codes


def test_project_check_cross_mismatch_is_deterministic(capsys):
    from dpgen_lsp import tool

    project = FIXTURES / "projects" / "cross-mismatch"
    assert tool.main(["check", str(project)]) == 0
    first = json.loads(capsys.readouterr().out)

    assert tool.main(["check", str(project)]) == 0
    second = json.loads(capsys.readouterr().out)

    assert first == second
    assert first["project_dir"].endswith("cross-mismatch")
    assert first["ok"] is False
    assert first["summary"]["cross_artifact"] >= 1
    cross_codes = {item["code"] for item in first["cross_artifact_diagnostics"]}
    assert "cross.stage.model_devi.missing" in cross_codes


def test_project_check_valid_run_passes_cross_artifact(capsys):
    from dpgen_lsp import tool

    project = FIXTURES / "projects" / "valid-run"
    assert tool.main(["check", str(project)]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["summary"]["cross_artifact"] == 0
    assert payload["cross_artifact_diagnostics"] == []


@pytest.mark.parametrize(
    ("fixture_dir", "expect_ok"),
    [
        (FIXTURES / "valid", True),
        (FIXTURES / "invalid", False),
    ],
)
def test_single_file_fixture_smoke(fixture_dir: Path, expect_ok: bool, capsys):
    from dpgen_lsp import tool

    for name in ("param.json", "machine.json"):
        path = fixture_dir / name
        assert tool.main(["check", str(path)]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["ok"] is expect_ok
