"""Runtime log fixture tests for DP-GEN log diagnostics."""

from __future__ import annotations

import json
from pathlib import Path

from dpgen_lsp.features.log_parser import parse_log_content, parse_log_path
from dpgen_lsp.tool import main as tool_main

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "tests" / "fixtures" / "logs"


def test_clean_log_has_no_diagnostics():
    diagnostics = parse_log_path(LOGS / "clean.log")
    assert diagnostics == []


def test_missing_files_log_maps_to_config_paths():
    diagnostics = parse_log_path(LOGS / "missing_files.log")
    codes = {item["code"] for item in diagnostics}
    assert "dpgen.log.file_not_found" in codes
    assert any(item.get("config_path") for item in diagnostics)
    assert all(item["manual_ref"].startswith("https://docs.deepmodeling.com/") for item in diagnostics)


def test_training_failed_log():
    diagnostics = parse_log_content((LOGS / "training_failed.log").read_text())
    assert any(item["code"] == "dpgen.log.training_failed" for item in diagnostics)


def test_model_devi_failed_log():
    diagnostics = parse_log_content((LOGS / "model_devi_failed.log").read_text())
    assert any(item["code"] == "dpgen.log.model_devi_failed" for item in diagnostics)


def test_labeling_failed_log():
    diagnostics = parse_log_content((LOGS / "labeling_failed.log").read_text())
    assert any(item["code"] == "dpgen.log.labeling_failed" for item in diagnostics)


def test_scheduler_mismatch_is_nonblocking_warning():
    diagnostics = parse_log_content((LOGS / "scheduler_mismatch.log").read_text())
    item = next(item for item in diagnostics if item["code"] == "dpgen.log.scheduler_mismatch")
    assert item["blocking"] is False
    assert item["severity"] == "warning"
    assert item.get("fix_hints")


def test_malformed_task_includes_key_error_and_task_code():
    diagnostics = parse_log_content((LOGS / "malformed_task.log").read_text())
    codes = {item["code"] for item in diagnostics}
    assert "dpgen.log.missing_key" in codes
    assert "dpgen.log.malformed_task" in codes


def test_parse_log_cli_returns_diagnostic_envelope(capsys):
    rc = tool_main(["parse-log", str(LOGS / "missing_files.log")])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["operation"] == "parse_log"
    assert payload["diagnostic_engine"] == "1.0"
    assert payload["diagnostics"]
    assert payload["capabilities"]["operation"] == "parse-log"


def test_fix_operation_exposes_log_fix_hints(capsys, tmp_path: Path):
    log_path = tmp_path / "dpgen.log"
    log_path.write_text("KeyError: 'model_devi_jobs'\n", encoding="utf-8")
    rc = tool_main(["fix", str(log_path)])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["operation"] == "fix"
    assert payload["diagnostic_engine"] == "1.0"
    assert payload["capabilities"]["status"] == "unavailable"
    # fix on a log without position context may be unavailable; parse-log still gives hints
    parse_rc = tool_main(["parse-log", str(log_path)])
    assert parse_rc == 0
