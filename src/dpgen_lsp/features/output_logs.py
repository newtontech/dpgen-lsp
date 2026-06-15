"""Runtime/output log diagnostics for DP-GEN workflow artifacts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Pattern

MANUAL_REF = "https://docs.deepmodeling.com/projects/dpgen/en/latest/"

LOG_FILE_NAMES = {
    "dpgen.log",
    "dpdispatcher.log",
    "record.dpgen",
    "lcurve.out",
    "model_devi.out",
    "md.log",
    "ener.edr",
    "traj.trr",
    "state.cpt",
    "log",
}

ERROR_PATTERNS: tuple[tuple[str, Pattern[str]], ...] = (
    ("log.traceback", re.compile(r"\bTraceback\b", re.IGNORECASE)),
    ("log.runtime_error", re.compile(r"\b(RuntimeError|Exception|Fatal)\b", re.IGNORECASE)),
    ("log.error", re.compile(r"\b(ERROR|CRITICAL)\b", re.IGNORECASE)),
    ("log.failed", re.compile(r"\b(failed|failure)\b", re.IGNORECASE)),
    ("log.nonzero_return_code", re.compile(r"\breturn code\s+([1-9]\d*)\b", re.IGNORECASE)),
    ("log.not_converged", re.compile(r"\bnot\s+converged\b", re.IGNORECASE)),
)

WARNING_PATTERNS: tuple[tuple[str, Pattern[str]], ...] = (
    ("log.warning", re.compile(r"\bWARNING\b", re.IGNORECASE)),
    ("log.nan_or_inf", re.compile(r"\b(nan|inf)\b", re.IGNORECASE)),
)


def is_output_log_path(path: Path) -> bool:
    name = path.name.lower()
    if name in LOG_FILE_NAMES:
        return True
    if name.endswith(".log") and ("dpgen" in name or "dpdispatcher" in name):
        return True
    parts = {part.lower() for part in path.parts}
    return name == "log" and ("00.train" in parts or "01.model_devi" in parts or "02.fp" in parts)


class LogDiagnosticProvider:
    """Detect common DP-GEN, DPDispatcher, and workflow-output failures."""

    def get_diagnostics(self, text: str, uri: str = "") -> list[dict]:
        if not text.strip():
            return [
                _diagnostic(
                    0,
                    0,
                    "Log file is empty; no DP-GEN runtime status can be verified.",
                    severity="warning",
                    code="log.empty",
                    blocking=False,
                )
            ]

        diagnostics: list[dict] = []
        for line_no, line in enumerate(text.splitlines()):
            diagnostics.extend(_match_line(line, line_no, ERROR_PATTERNS, severity="error"))
            diagnostics.extend(_match_line(line, line_no, WARNING_PATTERNS, severity="warning"))
        return _dedupe(diagnostics)


def _match_line(
    line: str,
    line_no: int,
    patterns: tuple[tuple[str, Pattern[str]], ...],
    *,
    severity: str,
) -> list[dict]:
    diagnostics: list[dict] = []
    for code, pattern in patterns:
        match = pattern.search(line)
        if match is None:
            continue
        diagnostics.append(
            _diagnostic(
                line_no,
                match.start(),
                _message_for(code, line),
                severity=severity,
                code=code,
                length=max(match.end() - match.start(), 1),
                blocking=severity == "error",
                actual=line.strip(),
            )
        )
    return diagnostics


def _message_for(code: str, line: str) -> str:
    messages = {
        "log.traceback": "Python traceback found in DP-GEN runtime output.",
        "log.runtime_error": "Runtime exception found in DP-GEN runtime output.",
        "log.error": "Error-level log entry found in DP-GEN runtime output.",
        "log.failed": "Failure marker found in DP-GEN runtime output.",
        "log.nonzero_return_code": "Non-zero task return code found in DP-GEN runtime output.",
        "log.not_converged": "Non-convergence marker found in DP-GEN runtime output.",
        "log.warning": "Warning-level log entry found in DP-GEN runtime output.",
        "log.nan_or_inf": "NaN or Inf value found in DP-GEN runtime output.",
    }
    return messages.get(code, f"Runtime log diagnostic: {line.strip()}")


def _diagnostic(
    line: int,
    character: int,
    message: str,
    *,
    severity: str,
    code: str,
    length: int = 1,
    blocking: bool,
    actual: str | None = None,
) -> dict:
    payload = {
        "code": code,
        "severity": severity,
        "category": "preflight/runtime-risk",
        "confidence": 1.0,
        "source": "dpgen-lsp",
        "range": {
            "start": {"line": line, "character": character},
            "end": {"line": line, "character": character + length},
        },
        "message": message,
        "fix_hints": ["Inspect the referenced DP-GEN, DPDispatcher, or task output log."],
        "blocking": blocking,
        "manual_ref": MANUAL_REF,
    }
    if actual is not None:
        payload["actual"] = actual
    return payload


def _dedupe(diagnostics: list[dict]) -> list[dict]:
    seen: set[tuple[str, int, int]] = set()
    result: list[dict] = []
    for item in diagnostics:
        start = item["range"]["start"]
        key = (item["code"], start["line"], start["character"])
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result
