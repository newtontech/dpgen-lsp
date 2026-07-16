#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: $0 path/to/dpgen_lsp-*.whl" >&2
  exit 2
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WHEEL="$1"
if [[ "$WHEEL" != /* ]]; then
  WHEEL="$(pwd)/$WHEEL"
fi
if [ ! -f "$WHEEL" ]; then
  echo "wheel not found: $WHEEL" >&2
  exit 2
fi

PYTHON_BIN="${PYTHON:-python3}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

"$PYTHON_BIN" -m venv "$TMP_DIR/venv"
VENV_PYTHON="$TMP_DIR/venv/bin/python"
BIN="$TMP_DIR/venv/bin"
"$VENV_PYTHON" -m pip install --disable-pip-version-check "$WHEEL"

(
  cd "$TMP_DIR"
  # Server CLI: dpgen-lsp --help
  "$BIN/dpgen-lsp" --help >"$TMP_DIR/server-help.txt"
)

VALID="$REPO_ROOT/tests/fixtures/valid/param.json"
INVALID="$REPO_ROOT/tests/fixtures/invalid/param.json"
LOG_FILE="$REPO_ROOT/tests/fixtures/logs/missing_files.log"

# Agent CLI: dpgen-lsp-tool check
"$BIN/dpgen-lsp-tool" check "$VALID" --fail-on-blocking >"$TMP_DIR/valid.json"

if "$BIN/dpgen-lsp-tool" check "$INVALID" --fail-on-blocking >"$TMP_DIR/invalid.json"; then
  echo "invalid fixture unexpectedly passed" >&2
  exit 1
fi

# Agent CLI: dpgen-lsp-tool parse-log
"$BIN/dpgen-lsp-tool" parse-log "$LOG_FILE" >"$TMP_DIR/log.json"
"$BIN/dpgen-lsp-tool" capabilities >"$TMP_DIR/capabilities.json"

"$VENV_PYTHON" - "$TMP_DIR" <<'PY'
import importlib.metadata
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
assert importlib.metadata.version("dpgen-lsp") == "0.1.2"

help_text = (root / "server-help.txt").read_text()
valid = json.loads((root / "valid.json").read_text())
invalid = json.loads((root / "invalid.json").read_text())
log = json.loads((root / "log.json").read_text())
capabilities = json.loads((root / "capabilities.json").read_text())

assert "usage: dpgen-lsp" in help_text
assert valid["ok"] is True
assert invalid["ok"] is False
assert any(item["code"] == "mass_map.lint" for item in invalid["diagnostics"])
assert log["ok"] is False
assert any(item["code"] == "dpgen.log.file_not_found" for item in log["diagnostics"])
assert capabilities["releaseVersion"] == "0.1.2"
assert capabilities["releaseTag"] == "v0.1.2"
PY

echo "Fresh-wheel smoke passed: server help, agent CLI, valid/invalid/log fixtures"
