"""Cross-artifact diagnostics between param.json and machine.json.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""

from __future__ import annotations

from typing import Any

from ..schema.official_rules import manual_ref_for


def _section_ready(machine_data: dict[str, Any], section: str) -> bool:
    value = machine_data.get(section)
    if isinstance(value, list):
        return len(value) > 0
    if isinstance(value, dict):
        return bool(value)
    return False


def _diagnostic(
    *,
    code: str,
    message: str,
    severity: str = "error",
    category: str = "cross-file reference",
    blocking: bool = True,
    manual_ref: str | None = None,
    expected: Any = None,
    actual: Any = None,
    fix_hints: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "category": category,
        "confidence": 1.0,
        "source": "dpgen-lsp",
        "range": {
            "start": {"line": 0, "character": 0},
            "end": {"line": 0, "character": 1},
        },
        "message": message,
        "fix_hints": fix_hints or [],
        "blocking": blocking,
        "manual_ref": manual_ref,
        "expected": expected,
        "actual": actual,
        "artifact": "project",
    }


def _param_needs_training(param_data: dict[str, Any]) -> bool:
    return any(
        key in param_data
        for key in ("numb_models", "default_training_param", "init_data_sys", "init_data_prefix")
    )


def _param_needs_model_devi(param_data: dict[str, Any]) -> bool:
    jobs = param_data.get("model_devi_jobs")
    return isinstance(jobs, list) and len(jobs) > 0


def _param_needs_fp(param_data: dict[str, Any]) -> bool:
    return bool(param_data.get("fp_style"))


def get_cross_artifact_diagnostics(
    param_data: dict[str, Any],
    machine_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Validate that machine.json stages match param.json workflow needs.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""
    diagnostics: list[dict[str, Any]] = []

    stage_checks = (
        (
            "train",
            _param_needs_training,
            "cross.stage.train.missing",
            "param.json configures training but machine.json has no train task environments.",
            "Add a non-empty train section to machine.json for DP-GEN training jobs.",
        ),
        (
            "model_devi",
            _param_needs_model_devi,
            "cross.stage.model_devi.missing",
            "param.json defines model_devi_jobs but machine.json has no model_devi task environments.",
            "Add a non-empty model_devi section to machine.json for exploration jobs.",
        ),
        (
            "fp",
            _param_needs_fp,
            "cross.stage.fp.missing",
            "param.json sets fp_style but machine.json has no fp task environments.",
            "Add a non-empty fp section to machine.json for first-principles labeling.",
        ),
    )

    for section, needs_stage, code, message, fix_hint in stage_checks:
        if not needs_stage(param_data):
            continue
        if _section_ready(machine_data, section):
            continue
        diagnostics.append(
            _diagnostic(
                code=code,
                message=message,
                manual_ref=manual_ref_for("cross", code=code),
                expected=f"non-empty machine.json '{section}' section",
                actual=machine_data.get(section, "missing"),
                fix_hints=[fix_hint],
            )
        )

    return diagnostics
