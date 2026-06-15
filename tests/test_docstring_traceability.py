"""Tests for the OpenQC v1 docstring/wiki/raw traceability contract."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "reports" / "docstring-wiki-raw-traceability.json"
CHECKER = ROOT / "scripts" / "check_docstring_traceability.py"

RULE_CODE_RE = re.compile(r"^DPGEN-[A-Z]+-[A-Z]+-\d{3}$")


def _run_checker(*extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--root",
            str(ROOT),
            *extra,
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def _load_report() -> dict:
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def test_docstring_wiki_raw_traceability_is_complete() -> None:
    result = _run_checker("--strict")
    assert result.returncode == 0, result.stdout + result.stderr


def test_checker_regenerates_openqc_v1_report() -> None:
    result = _run_checker("--write-report")
    assert result.returncode == 0, result.stdout + result.stderr
    assert REPORT_PATH.is_file()
    report = _load_report()
    assert report["schemaVersion"] == "openqc.lsp.traceability.v1"


@pytest.fixture(scope="module")
def report() -> dict:
    """Regenerate the report once and reuse it across the v1 contract tests."""
    result = _run_checker("--write-report")
    assert result.returncode == 0, result.stdout + result.stderr
    return _load_report()


def test_report_has_required_top_level_fields(report: dict) -> None:
    required = [
        "schemaVersion",
        "serverId",
        "repository",
        "languageId",
        "generatedAt",
        "summary",
        "docstrings",
        "wikiSources",
        "ruleIds",
        "sourceUrls",
        "rawManifest",
    ]
    missing = [field for field in required if field not in report]
    assert missing == [], f"missing top-level fields: {missing}"


def test_report_summary_counters_are_zero_failure(report: dict) -> None:
    summary = report["summary"]
    assert summary["docstringsTotal"] == summary["docstringsLinked"]
    assert summary["brokenWikiLinks"] == 0
    assert summary["wikiSourcesWithoutRaw"] == 0
    assert summary["rawManifestFailures"] == 0


def test_report_server_repository_and_language(report: dict) -> None:
    capabilities = json.loads((ROOT / "lsp-capabilities.json").read_text())
    assert report["serverId"] == capabilities["id"]
    assert report["languageId"] == capabilities["languageId"]
    assert report["repository"] == capabilities["repository"]
    assert report["repository"].count("/") == 1, report["repository"]


def test_docstring_records_match_summary_and_use_repo_relative_paths(report: dict) -> None:
    summary = report["summary"]
    records = report["docstrings"]
    assert len(records) == summary["docstringsTotal"]
    assert sum(1 for item in records if item["linked"]) == summary["docstringsLinked"]
    for item in records:
        assert item["path"] == item["file"]
        assert item["wikiPath"].startswith("wiki/"), item
        assert item["symbol"], item
        assert not item["path"].startswith("/"), item
        assert not item["file"].startswith("/"), item
        for ref in item["wikiRefs"]:
            assert not ref.startswith("/"), ref
        for ref in item["brokenWikiRefs"]:
            assert not ref.startswith("/"), ref


def test_wiki_sources_match_summary_and_use_repo_relative_paths(report: dict) -> None:
    summary = report["summary"]
    records = report["wikiSources"]
    assert len(records) >= summary["wikiPagesTotal"]
    assert len({item["wikiPath"] for item in records}) == summary["wikiPagesWithRaw"]
    for item in records:
        assert item["wikiPath"].startswith("wiki/"), item
        assert item["rawPath"].startswith("raw/"), item
        assert item["sourceUrl"], item
        assert item["file"].startswith("wiki/"), item
        for ref in item["rawRefs"]:
            assert ref.startswith("raw/"), item
        assert item["missingRawRefs"] == []
        assert item["refsMissingFromManifest"] == []


def test_rule_ids_follow_openqc_v1_format(report: dict) -> None:
    records = report["ruleIds"]
    assert records, "ruleIds should not be empty"
    for item in records:
        assert RULE_CODE_RE.match(item["code"]), item
        assert item["fileRole"] in {"PARAM", "MACHINE", "CROSS"}, item
        assert item["category"].isupper(), item
        # legacyCode must remain non-empty so the OpenQC contract preserves
        # the original rule index identifier.
        assert item["legacyCode"], item
        assert item["source"].startswith("src/"), item
        assert item["sourcePath"] == item["source"], item
        for ref in item["wikiRefs"]:
            assert ref.startswith("wiki/"), item
        for ref in item["rawRefs"]:
            assert ref.startswith("raw/"), item
        # manualRef is a URL pulled from the rule index.
        assert item["manualRef"].startswith(("http://", "https://")), item


def test_rule_ids_are_unique_and_stable(report: dict) -> None:
    codes = [item["code"] for item in report["ruleIds"]]
    assert len(set(codes)) == len(codes), "rule id codes must be unique"


def test_rule_ids_cover_expected_legacy_codes(report: dict) -> None:
    legacy = {item["legacyCode"] for item in report["ruleIds"]}
    expected = {
        "mass_map.lint",
        "fp_pp_files.lint",
        "fp_task_max.lint",
        "model_devi_f_trust_lo.lint",
        "numb_models.lint",
        "PRINT_LEVEL.lint",
        "STRESS_TENSOR.lint",
        "path.init_data_sys",
        "path.sys_configs",
        "machine.section.missing",
        "machine.section.type",
        "machine.train.scass_type",
        "machine.model_devi.scass_type",
        "machine.fp.scass_type",
        "cross.stage.train.missing",
        "cross.stage.model_devi.missing",
        "cross.stage.fp.missing",
    }
    assert expected <= legacy, sorted(expected - legacy)


def test_source_urls_are_absolute_http_urls(report: dict) -> None:
    urls = report["sourceUrls"]
    assert urls, "sourceUrls should not be empty"
    for item in urls:
        assert item["url"].startswith(("http://", "https://")), item
        assert item["rawPath"].startswith("raw/"), item


def test_raw_manifest_has_entries_and_no_errors(report: dict) -> None:
    manifest = report["rawManifest"]
    assert manifest["exists"] is True
    assert manifest["ok"] is True
    assert manifest["path"] == "raw/assets/manifest.json"
    assert manifest["errors"] == []
    assert manifest["entries"], "raw manifest entries should not be empty"
    for entry in manifest["entries"]:
        assert entry["raw_path"].startswith("raw/"), entry
        assert entry["checksum_sha256"], entry


def test_committed_report_matches_freshly_generated_report() -> None:
    """The committed report must be byte-identical to a fresh checker run,
    ignoring the rolling ``generatedAt`` timestamp."""
    committed = _load_report()

    write_result = _run_checker("--write-report")
    assert write_result.returncode == 0, write_result.stdout + write_result.stderr
    regenerated = _load_report()

    def _scrub(report: dict) -> dict:
        copy = dict(report)
        copy.pop("generatedAt", None)
        return copy

    assert _scrub(regenerated) == _scrub(committed)
