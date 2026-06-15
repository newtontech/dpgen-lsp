"""Runtime log diagnostics for DP-GEN and dpdispatcher output.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LogDiagnostic:
    code: str
    severity: str
    message: str
    line: int
    column: int = 1
    blocking: bool = True
    category: str = "preflight/runtime-risk"
    confidence: float = 0.85
    manual_ref: str = ""
    source_id: str = "dpgen-run-param"
    fix_hints: list[str] | None = None
    config_path: str | None = None

    def to_dict(self, *, file_path: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "line": self.line,
            "column": self.column,
            "blocking": self.blocking,
            "category": self.category,
            "confidence": self.confidence,
            "source": "dpgen-log-parser",
            "manual_ref": self.manual_ref
            or "https://docs.deepmodeling.com/projects/dpgen/en/latest/run/param.html",
            "source_id": self.source_id,
            "range": {
                "start": {"line": max(self.line - 1, 0), "character": 0},
                "end": {"line": max(self.line - 1, 0), "character": 1},
            },
            "path": file_path,
        }
        if self.fix_hints:
            payload["fix_hints"] = self.fix_hints
        if self.config_path:
            payload["config_path"] = self.config_path
        return payload


_PATH_RE = re.compile(
    r"(?P<path>(?:[\w./-]+/)?(?:param\.json|machine\.json|init_data_sys|sys_configs|model_devi|iter\.\d+)[\w./-]*)"
)
_FILE_NOT_FOUND_RE = re.compile(
    r"(FileNotFoundError|No such file or directory|cannot find file|does not exist)",
    re.IGNORECASE,
)
_TRAINING_FAILED_RE = re.compile(r"(train(?:ing)? failed|lcurve\.out.*error|dp train failed)", re.IGNORECASE)
_MODEL_DEVI_FAILED_RE = re.compile(r"(model_devi failed|model deviation failed|devi job failed)", re.IGNORECASE)
_LABELING_FAILED_RE = re.compile(r"(label(?:ing)? failed|fp task failed|first-principles failed)", re.IGNORECASE)
_SCHEDULER_RE = re.compile(
    r"(submission failed|queue not found|resource mismatch|machine\.json|dpdispatcher)",
    re.IGNORECASE,
)
_KEY_ERROR_RE = re.compile(r"KeyError:\s*['\"](?P<key>[^'\"]+)['\"]")
_JSON_ERROR_RE = re.compile(r"(JSONDecodeError|Expecting property name enclosed in quotes)", re.IGNORECASE)
_TASK_MALFORMED_RE = re.compile(r"(malformed task|invalid task dict|bad task format)", re.IGNORECASE)


def _extract_config_path(line: str) -> str | None:
    match = _PATH_RE.search(line)
    if match:
        return match.group("path")
    if "param.json" in line:
        return "param.json"
    if "machine.json" in line:
        return "machine.json"
    return None


def parse_log_content(content: str, file_path: str = "<log>") -> list[dict[str, Any]]:
    """Parse DP-GEN or dpdispatcher log content into DiagnosticEnvelope items.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""
    diagnostics: list[LogDiagnostic] = []
    seen: set[tuple[str, int, str]] = set()

    def add(item: LogDiagnostic) -> None:
        key = (item.code, item.line, item.message)
        if key in seen:
            return
        seen.add(key)
        diagnostics.append(item)

    lines = content.splitlines()
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        config_path = _extract_config_path(stripped)

        if _FILE_NOT_FOUND_RE.search(stripped):
            add(
                LogDiagnostic(
                    code="dpgen.log.file_not_found",
                    severity="error",
                    message=f"runtime missing file: {stripped}",
                    line=index,
                    config_path=config_path,
                    source_id="dpgen-run-example-param",
                    fix_hints=[
                        "Verify init_data_sys, sys_configs, and model paths in param.json exist",
                        "Check relative paths from the DP-GEN project root",
                    ],
                )
            )

        if _TRAINING_FAILED_RE.search(stripped):
            add(
                LogDiagnostic(
                    code="dpgen.log.training_failed",
                    severity="error",
                    message=f"training stage failed: {stripped}",
                    line=index,
                    config_path=config_path or "param.json",
                    source_id="dpgen-run-param",
                    fix_hints=[
                        "Inspect iter.*/00.train logs and lcurve.out",
                        "Confirm numb_models and training data paths in param.json",
                    ],
                )
            )

        if _MODEL_DEVI_FAILED_RE.search(stripped):
            add(
                LogDiagnostic(
                    code="dpgen.log.model_devi_failed",
                    severity="error",
                    message=f"model deviation failed: {stripped}",
                    line=index,
                    config_path=config_path or "param.json",
                    source_id="dpgen-run-param",
                    fix_hints=[
                        "Check model_devi_jobs and trust_lo/trust_hi thresholds",
                    ],
                )
            )

        if _LABELING_FAILED_RE.search(stripped):
            add(
                LogDiagnostic(
                    code="dpgen.log.labeling_failed",
                    severity="error",
                    message=f"labeling/fp stage failed: {stripped}",
                    line=index,
                    config_path=config_path or "param.json",
                    source_id="dpgen-run-param",
                )
            )

        if _SCHEDULER_RE.search(stripped):
            add(
                LogDiagnostic(
                    code="dpgen.log.scheduler_mismatch",
                    severity="warning",
                    message=f"scheduler or machine resource issue: {stripped}",
                    line=index,
                    blocking=False,
                    config_path=config_path or "machine.json",
                    source_id="dpgen-run-example-machine",
                    fix_hints=[
                        "Compare machine.json train/model_devi/fp sections with cluster resources",
                    ],
                )
            )

        key_match = _KEY_ERROR_RE.search(stripped)
        if key_match:
            key = key_match.group("key")
            add(
                LogDiagnostic(
                    code="dpgen.log.missing_key",
                    severity="error",
                    message=f"runtime KeyError for '{key}'",
                    line=index,
                    config_path="param.json",
                    source_id="dpgen-run-param",
                    fix_hints=[f"Add or correct key '{key}' in param.json"],
                )
            )

        if _JSON_ERROR_RE.search(stripped):
            add(
                LogDiagnostic(
                    code="dpgen.log.malformed_json",
                    severity="error",
                    message=f"malformed JSON in generated task: {stripped}",
                    line=index,
                    source_id="dpgen-run-example-param",
                )
            )

        if _TASK_MALFORMED_RE.search(stripped):
            add(
                LogDiagnostic(
                    code="dpgen.log.malformed_task",
                    severity="error",
                    message=f"malformed generated task: {stripped}",
                    line=index,
                    source_id="dpgen-run-param",
                )
            )

    return [item.to_dict(file_path=file_path) for item in diagnostics]


def parse_log_path(path: Path) -> list[dict[str, Any]]:
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        content = ""
    return parse_log_content(content, str(path.resolve()))
