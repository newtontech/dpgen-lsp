"""Tests for the official-docs -> rules -> runtime pipeline."""

from __future__ import annotations

import json
from pathlib import Path


def test_static_schema_fallback_has_official_fields():
    from dpgen_lsp.schema.loader import load_schema_tree
    from dpgen_lsp.schema.official_rules import source_provenance

    schema = load_schema_tree("run")

    assert schema.root is not None
    assert schema.find_node("type_map") is not None
    assert schema.find_node("sys_configs") is not None
    assert any("example-of-param" in source["url"] for source in source_provenance())


def test_capabilities_include_pipeline_and_provenance(capsys):
    from dpgen_lsp import tool

    assert tool.main(["capabilities"]) == 0
    payload = json.loads(capsys.readouterr().out)
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "lsp-capabilities.json").read_text(encoding="utf-8"))

    for key in (
        "id",
        "languageId",
        "executable",
        "defaultBranch",
        "filePatterns",
        "maturity",
        "blockingPolicy",
        "diagnosticSchema",
        "fixturePaths",
        "outputLogPatterns",
        "openqc",
        "wikiPaths",
        "versionedSourceProvenance",
    ):
        assert payload[key] == manifest[key]

    assert payload["pipeline"] == [
        "official-docs-fetch",
        "structured-schema-rules",
        "source-provenance",
        "tests",
        "lsp-runtime",
    ]
    assert any(
        source["id"] == "dpgen-run-example-machine" for source in payload["sourceProvenance"]
    )
    assert any(source["kind"] == "structured_rules" for source in payload["sourceProvenance"])
    assert set(manifest["capabilities"]) <= set(payload["capabilities"])
    assert "definition" in payload["standardLsp"]["textDocument"]
    assert "v0.13.3" in payload["dpgenVersionSupport"]["knownReleaseTags"]
    assert "run/mdata.html" in payload["dpgenVersionSupport"]["docPages"]
    assert payload["dpgenVersionSupport"]["releaseTagsUpdatedAt"]
    assert payload["dpgenVersionSupport"]["dpgenVersionFields"] == [
        "dpgen_version",
        "dpgenVersion",
    ]
    assert "api_version" in payload["dpgenVersionSupport"]["relatedRuntimeVersionFields"]
    assert payload["dpgenVersionSupport"]["coverage"]["latestReleaseTag"] == "v0.13.3"
    assert payload["dpgenVersionSupport"]["coverage"]["releaseTagCount"] >= 30


def test_manifest_publishes_versioned_raw_provenance():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "lsp-capabilities.json").read_text(encoding="utf-8"))
    versioned = manifest["versionedSourceProvenance"]
    snapshot = json.loads((root / versioned["snapshot"]).read_text(encoding="utf-8"))
    provenance = json.loads((root / versioned["provenance"]).read_text(encoding="utf-8"))
    version_index = json.loads((root / versioned["versionIndex"]).read_text(encoding="utf-8"))

    assert versioned["sourceCount"] == len(snapshot["sources"]) == len(provenance["sources"])
    assert versioned["versions"] == ["latest", "stable", "devel", "v0.13.3", "v0.12.1"]
    assert set(versioned["docPages"]) == set(version_index["policy"]["docPages"])
    assert versioned["sourceCount"] >= 30


def test_manifest_fixture_paths_exist_and_drive_smoke_checks():
    from dpgen_lsp.tool import check_path

    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "lsp-capabilities.json").read_text(encoding="utf-8"))

    for group, paths in manifest["fixturePaths"].items():
        assert any((root / path).exists() for path in paths), group

    valid_payload = check_path(root / "tests" / "fixtures" / "valid" / "param.json")
    invalid_payload = check_path(
        root / "tests" / "fixtures" / "invalid" / "param_bad_version_and_mass_map.json"
    )

    invalid_by_code = {item["code"]: item for item in invalid_payload["diagnostics"]}
    assert valid_payload["ok"] is True
    assert invalid_payload["ok"] is False
    assert invalid_by_code["mass_map.lint"]["blocking"] is True
    assert invalid_by_code["version.unverified"]["blocking"] is False


def test_docs_backed_diagnostics_include_manual_ref(tmp_path: Path):
    from dpgen_lsp.features.diagnostic import DiagnosticProvider

    text = json.dumps(
        {
            "type_map": ["H", "C"],
            "mass_map": [1],
            "init_data_sys": ["missing/deepmd"],
            "sys_configs": [["missing/scale*/POSCAR"]],
            "numb_models": 1,
            "model_devi_f_trust_lo": 0.2,
            "model_devi_f_trust_hi": 0.1,
            "fp_style": "vasp",
            "fp_pp_files": ["POTCAR_H"],
        },
        indent=2,
    )

    diagnostics = DiagnosticProvider().get_diagnostics(text, base_dir=tmp_path)
    by_code = {item["code"]: item for item in diagnostics}

    assert "mass_map.lint" in by_code
    assert "path.sys_configs" in by_code
    assert by_code["mass_map.lint"]["manual_ref"].startswith("https://docs.deepmodeling.com/")
    assert by_code["path.sys_configs"]["manual_ref"].startswith("https://docs.deepmodeling.com/")
    assert by_code["numb_models.lint"]["blocking"] is False


def test_machine_sections_are_validated_without_dpdispatcher():
    from dpgen_lsp.features.diagnostic import DiagnosticProvider

    text = json.dumps({"api_version": "1.0", "train": {}})

    diagnostics = DiagnosticProvider().get_diagnostics(text)
    by_code = {item["code"]: item for item in diagnostics}

    assert "machine.section.type" in by_code
    assert "machine.section.missing" in by_code
    assert by_code["machine.section.type"]["manual_ref"].endswith("example-of-machine.html")


def test_known_release_version_is_not_warned():
    from dpgen_lsp.features.diagnostic import DiagnosticProvider

    text = json.dumps(
        {
            "dpgen_version": "v0.13.3",
            "type_map": ["H"],
            "model_devi_jobs": [],
        }
    )
    diagnostics = DiagnosticProvider().get_diagnostics(text)

    assert "version.unverified" not in {item["code"] for item in diagnostics}


def test_unknown_declared_version_gets_nonblocking_warning():
    from dpgen_lsp.features.diagnostic import DiagnosticProvider

    diagnostics = DiagnosticProvider().get_diagnostics(json.dumps({"dpgen_version": "v9.9.9"}))
    by_code = {item["code"]: item for item in diagnostics}

    assert by_code["version.unverified"]["blocking"] is False
    assert by_code["version.unverified"]["category"] == "version"
    assert by_code["version.unverified"]["actual"] == "v9.9.9"


def test_related_runtime_version_fields_do_not_trigger_dpgen_release_warning():
    from dpgen_lsp.features.diagnostic import DiagnosticProvider
    from dpgen_lsp.schema.versioning import declared_dpgen_version

    data = {"api_version": "1.0", "deepmd_version": "2.0.1", "train_backend": "pytorch"}

    assert declared_dpgen_version(data) is None
    diagnostics = DiagnosticProvider().get_diagnostics(json.dumps(data))

    assert "version.unverified" not in {item["code"] for item in diagnostics}


def test_version_diagnostics_are_valid_diagnostic_engine_categories(tmp_path: Path):
    from dpgen_lsp.rich_diagnostics import DIAGNOSTIC_CATEGORIES
    from dpgen_lsp.tool import check_path

    schema = json.loads(
        (
            Path(__file__).resolve().parents[1] / "diagnostics" / "diagnostic-engine-v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    category_enum = schema["properties"]["diagnostics"]["items"]["properties"]["category"]["enum"]
    input_path = tmp_path / "param.json"
    input_path.write_text(json.dumps({"dpgen_version": "v9.9.9"}), encoding="utf-8")

    payload = check_path(input_path)
    diagnostic = {item["code"]: item for item in payload["diagnostics"]}["version.unverified"]

    assert "version" in DIAGNOSTIC_CATEGORIES
    assert "version" in category_enum
    assert diagnostic["category"] == "version"
    assert payload["ok"] is True


def test_raw_official_docs_snapshot_matches_rule_sources():
    from dpgen_lsp.schema.official_rules import source_provenance

    root = Path(__file__).resolve().parents[1]
    raw = json.loads((root / "raw" / "assets" / "dpgen-official-docs.json").read_text())
    raw_ids = {source["id"] for source in raw["sources"]}
    official_ids = {
        source["id"] for source in source_provenance() if source["kind"] == "official_docs"
    }

    assert official_ids <= raw_ids
    assert raw["pipeline"][-1] == "lsp-runtime"


def test_version_index_covers_release_tags_and_docs_versions():
    root = Path(__file__).resolve().parents[1]
    version_index = json.loads((root / "raw" / "assets" / "dpgen-version-index.json").read_text())

    assert version_index["summary"]["releaseTagCount"] >= 30
    assert "v0.13.3" in version_index["releaseTags"]
    assert any(item["slug"] == "v0.12.1" for item in version_index["readthedocsVersions"])


def test_structured_rules_and_manifest_match_fetched_release_tags():
    root = Path(__file__).resolve().parents[1]
    version_index = json.loads((root / "raw" / "assets" / "dpgen-version-index.json").read_text())
    rules = json.loads((root / "src" / "dpgen_lsp" / "schema" / "dpgen_rules.json").read_text())
    capabilities = json.loads((root / "lsp-capabilities.json").read_text())

    release_tags = set(version_index["releaseTags"])
    rule_tags = set(rules["versionSupport"]["knownReleaseTags"])
    manifest_tags = set(capabilities["dpgenVersionSupport"]["knownReleaseTags"])

    assert release_tags <= rule_tags
    assert release_tags <= manifest_tags
    assert rules["versionSupport"]["releaseTagsUpdatedAt"] == version_index["fetched_at"]
