"""OpenQC and Bohrium routing smoke evidence for dpgen-lsp."""

from __future__ import annotations

import json
from pathlib import Path

from dpgen_lsp.tool import _capabilities_payload, _file_type, main as tool_main

ROOT = Path(__file__).resolve().parents[1]


class TestLanguageDetection:
    def test_param_json(self):
        assert _file_type(Path("param.json")) == "json"

    def test_machine_json(self):
        assert _file_type(Path("machine.json")) == "json"

    def test_log_file(self):
        assert _file_type(Path("dpgen.log")) == "log"


class TestCapabilitiesManifest:
    def test_capabilities_json_exists(self):
        manifest = _capabilities_payload()
        assert manifest["software"] == "dpgen"
        assert manifest["schema"] == "OpenQCLspCapabilities"

    def test_capabilities_include_log_diagnostics(self):
        manifest = _capabilities_payload()
        assert "output-log-diagnostics" in manifest["capabilities"]
        assert "parse-log" in manifest["agentCli"]["operations"]

    def test_pipeline_and_provenance_present(self):
        manifest = _capabilities_payload()
        assert manifest["pipeline"][-1] == "lsp-runtime"
        assert len(manifest["sourceProvenance"]) >= 4

    def test_standard_lsp_handlers(self):
        manifest = _capabilities_payload()
        assert manifest["standardLsp"]["runtime"] == "pygls"
        assert "diagnostic" in manifest["standardLsp"]["textDocument"]


class TestManifestFile:
    def test_lsp_capabilities_fixture_paths(self):
        manifest = json.loads((ROOT / "lsp-capabilities.json").read_text())
        logs = manifest["fixturePaths"]["logs"]
        assert "tests/fixtures/logs" in logs
        assert (ROOT / "tests" / "fixtures" / "logs" / "clean.log").exists()


class TestCLIAvailability:
    def test_capabilities_cli(self, capsys):
        rc = tool_main(["capabilities"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["software"] == "dpgen"
        assert "parse-log" in payload["agentCli"]["operations"]

    def test_manifest_openqc_block(self):
        manifest = json.loads((ROOT / "lsp-capabilities.json").read_text())
        assert manifest["openqc"]["registryId"] == "dpgen-lsp"
        assert manifest["openqc"]["diagnosticEnvelope"] == "DiagnosticEnvelope/v1"
