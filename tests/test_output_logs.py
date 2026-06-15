from __future__ import annotations

from pathlib import Path


def test_clean_dpgen_log_fixture_passes_agent_check():
    from dpgen_lsp.tool import check_path

    root = Path(__file__).resolve().parents[1]
    payload = check_path(root / "tests" / "fixtures" / "logs" / "dpgen.log")

    assert payload["ok"] is True
    assert payload["diagnostics"] == []
    assert payload["file_type"] == "log" if "file_type" in payload else True


def test_failed_dpdispatcher_log_blocks_agent_check(tmp_path: Path):
    from dpgen_lsp.tool import check_path

    log_path = tmp_path / "dpdispatcher.log"
    log_path.write_text(
        "2026-06-15 ERROR task failed with return code 2\n"
        "RuntimeError: remote fp task did not converge\n",
        encoding="utf-8",
    )

    payload = check_path(log_path)
    by_code = {item["code"]: item for item in payload["diagnostics"]}

    assert payload["ok"] is False
    assert by_code["log.error"]["blocking"] is True
    assert by_code["log.nonzero_return_code"]["blocking"] is True
    assert by_code["log.runtime_error"]["blocking"] is True


def test_empty_log_warns_without_blocking(tmp_path: Path):
    from dpgen_lsp.tool import check_path

    log_path = tmp_path / "dpgen.log"
    log_path.write_text("", encoding="utf-8")

    payload = check_path(log_path)
    by_code = {item["code"]: item for item in payload["diagnostics"]}

    assert payload["ok"] is True
    assert by_code["log.empty"]["severity"] == "warning"
    assert by_code["log.empty"]["blocking"] is False
