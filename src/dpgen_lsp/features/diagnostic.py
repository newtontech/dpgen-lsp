"""Diagnostics provider for JSON parse and schema validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..schema.loader import (
    SchemaTree,
    load_schema_tree,
    detect_workflow,
    detect_file_type,
    DPGEN_IMPORT_MAP,
    MACHINE_IMPORT_MAP,
)


def _range(line: int, character: int, length: int = 1) -> dict:
    return {
        "start": {"line": line, "character": character},
        "end": {"line": line, "character": character + max(length, 1)},
    }


def _diagnostic(
    line: int,
    character: int,
    message: str,
    severity: str = "error",
    code: str = "diagnostic",
    length: int = 1,
    category: str = "schema",
    fix_hints: list[str] | None = None,
    blocking: bool = True,
) -> dict:
    return {
        "code": code,
        "severity": severity,
        "category": category,
        "confidence": 1.0,
        "source": "dpgen-lsp",
        "range": _range(line, character, length),
        "message": message,
        "fix_hints": fix_hints or [],
        "blocking": blocking,
    }


class DiagnosticProvider:

    def __init__(self):
        self._schema_cache: dict[str, SchemaTree] = {}

    def get_diagnostics(
        self, text: str, uri: str = "", base_dir: Path | None = None
    ) -> list[dict]:
        diagnostics: list[dict] = []

        if not text.strip():
            return diagnostics

        try:
            json.loads(text)
        except json.JSONDecodeError as e:
            diagnostics.append(_diagnostic(
                e.lineno - 1 if e.lineno else 0,
                e.colno - 1 if e.colno else 0,
                f"JSON parse error: {e.msg}",
                severity="error",
                code="json.parse_error",
                category="syntax",
            ))
            return diagnostics

        try:
            data = json.loads(text)
        except Exception:
            return diagnostics

        file_type = detect_file_type(text)

        if file_type == "machine":
            diagnostics.extend(_validate_machine_config(data, text))
        else:
            workflow = detect_workflow(text)
            schema = self._get_schema(workflow)
            if schema.root is not None:
                try:
                    from dargs import Argument
                    info = DPGEN_IMPORT_MAP[schema.workflow]
                    arginfo_module = __import__(
                        info["module"], fromlist=[info["func"]]
                    )
                    arginfo_func = getattr(arginfo_module, info["func"])
                    arg = arginfo_func()
                    arg.check_value(data, strict=False)
                except ImportError:
                    pass
                except Exception as e:
                    diagnostics.append(_diagnostic(
                        0, 0,
                        f"Schema validation: {e}",
                        severity="error",
                        code="schema.validation",
                        category="schema",
                    ))

        return diagnostics

    def _get_schema(self, workflow: str) -> SchemaTree:
        if workflow not in self._schema_cache:
            try:
                self._schema_cache[workflow] = load_schema_tree(workflow)
            except Exception:
                self._schema_cache[workflow] = SchemaTree(workflow)
        return self._schema_cache[workflow]


# ── PR1: machine.json schema validation ──────────────────────────────────


def _validate_machine_config(data: dict, text: str) -> list[dict]:
    """Validate machine.json sections against dpdispatcher Machine.arginfo().

    machine.json structure:
    {
      "train": [ { "machine": {...}, ... } ],
      "model_devi": [ { "machine": {...}, ... } ],
      "fp": [ { "machine": {...}, ... } ]
    }
    """
    diagnostics: list[dict] = []

    try:
        from dpdispatcher.machine import Machine
        machine_arginfo = Machine.arginfo()
    except ImportError:
        return diagnostics
    except Exception:
        return diagnostics

    for section_name in ("train", "model_devi", "fp"):
        section_data = data.get(section_name)
        if not isinstance(section_data, list):
            continue

        for idx, task in enumerate(section_data):
            if not isinstance(task, dict):
                continue
            machine_data = task.get("machine")
            if machine_data is None or not isinstance(machine_data, dict):
                continue

            try:
                machine_arginfo.check_value(machine_data, strict=False)
            except Exception as e:
                err_msg = str(e)
                line = _find_section_line(text, section_name)
                fix_hints = []
                if "program_id" in err_msg:
                    fix_hints.append(
                        "Change program_id from string to integer"
                    )
                if "remote_profile" in err_msg:
                    fix_hints.append(
                        "Ensure remote_profile contains email, password, and program_id"
                    )
                diagnostics.append(_diagnostic(
                    line, 0,
                    f"Machine config validation error in '{section_name}': {err_msg}",
                    severity="error",
                    code=f"machine.{section_name}.schema",
                    category="schema",
                    fix_hints=fix_hints,
                ))

    return diagnostics


def _find_section_line(text: str, section_name: str) -> int:
    """Find the line number of a top-level section key."""
    lines = text.splitlines()
    for lno, raw in enumerate(lines):
        stripped = raw.strip()
        if stripped.startswith(f'"{section_name}"'):
            return lno
    return 0
