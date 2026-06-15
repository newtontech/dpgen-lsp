"""Semantic lint provider for cross-field consistency checks.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dpgen_lsp.schema.loader import detect_workflow


# Known Bohrium machine types (PR4)
KNOWN_BOHRIUM_MACHINES = {
    "cpu": [
        "c2_m4_cpu",
        "c4_m8_cpu",
        "c8_m16_cpu",
        "c16_m32_cpu",
        "c32_m64_cpu",
        "c32_m128_cpu",
        "c64_m256_cpu",
    ],
    "gpu": [
        "1 * NVIDIA V100_32g",
        "1 * NVIDIA A100_80g",
        "1 * NVIDIA 4090",
        "2 * NVIDIA V100_32g",
        "2 * NVIDIA A100_80g",
        "4 * NVIDIA A100_80g",
    ],
}


def _diagnostic(
    line: int,
    character: int,
    message: str,
    severity: str = "error",
    code: str = "lint",
    length: int = 1,
    category: str = "semantic",
    fix_hints: list[str] | None = None,
    blocking: bool = True,
) -> dict:
    """Create a diagnostic dict.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""
    return {
        "code": code,
        "severity": severity,
        "category": category,
        "confidence": 1.0,
        "source": "dpgen-lsp",
        "range": {
            "start": {"line": line, "character": character},
            "end": {"line": line, "character": character + max(length, 1)},
        },
        "message": message,
        "fix_hints": fix_hints or [],
        "blocking": blocking,
    }


def _find_key_line(text: str, key: str) -> int:
    """Find the line number of a key in JSON text.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""
    lines = text.splitlines()
    for lno, raw in enumerate(lines):
        if f'"{key}"' in raw:
            return lno
    return 0


def _find_next_key_line(text: str, key: str, used_lines: set[int]) -> int:
    """Find the next unused occurrence of a key in JSON text.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""
    lines = text.splitlines()
    for lno, raw in enumerate(lines):
        if f'"{key}"' in raw and lno not in used_lines:
            return lno
    return 0


def _lint_simple(
    key: str,
    message: str,
    category: str,
    text: str,
    severity: str = "error",
    blocking: bool = True,
) -> dict:
    """Create a simple lint diagnostic for a key.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""
    line = 0
    character = 0
    length = len(key)
    lines = text.splitlines()
    for lno, raw in enumerate(lines):
        if f'"{key}"' in raw:
            line = lno
            character = raw.find(f'"{key}"')
            break
    return _diagnostic(
        line, character, message, severity, f"{key}.lint", length, category, blocking=blocking
    )


# ── General semantic lint checks ─────────────────────────────────────────


def _lint_general_checks(data: dict, text: str) -> list[dict]:
    """General cross-field consistency checks.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""
    diagnostics: list[dict] = []

    type_map_len = len(data.get("type_map", []))
    mass_map_val = data.get("mass_map", [])
    if isinstance(mass_map_val, list) and mass_map_val != "auto" and len(mass_map_val) != type_map_len:
        diagnostics.append(_lint_simple(
            "mass_map",
            "mass_map length should match type_map length",
            "semantic",
            text,
        ))

    fp_task_max = data.get("fp_task_max", 0)
    fp_task_min = data.get("fp_task_min", 0)
    if fp_task_max > 0 and fp_task_min > 0 and fp_task_max < fp_task_min:
        diagnostics.append(_lint_simple(
            "fp_task_max",
            "fp_task_max should be >= fp_task_min",
            "semantic",
            text,
        ))

    f_lo = data.get("model_devi_f_trust_lo", 0)
    f_hi = data.get("model_devi_f_trust_hi", 1)
    if isinstance(f_lo, (int, float)) and isinstance(f_hi, (int, float)) and f_lo >= f_hi:
        diagnostics.append(_lint_simple(
            "model_devi_f_trust_lo",
            "model_devi_f_trust_lo should be less than model_devi_f_trust_hi",
            "semantic",
            text,
        ))

    for low_key, high_key in (
        ("model_devi_e_trust_lo", "model_devi_e_trust_hi"),
        ("model_devi_v_trust_lo", "model_devi_v_trust_hi"),
    ):
        low = data.get(low_key)
        high = data.get(high_key)
        if isinstance(low, (int, float)) and isinstance(high, (int, float)) and low >= high:
            diagnostics.append(_lint_simple(
                low_key,
                f"{low_key} should be less than {high_key}",
                "semantic",
                text,
            ))

    numb_models = data.get("numb_models", 0)
    if numb_models > 0 and numb_models < 2:
        diagnostics.append(_lint_simple(
            "numb_models",
            "numb_models=1 may not be sufficient for model deviation. 4 is recommended.",
            "suggestion",
            text,
            severity="warning",
            blocking=False,
        ))

    training_iter0_model_path = data.get("training_iter0_model_path")
    if isinstance(numb_models, int) and numb_models > 0 and isinstance(training_iter0_model_path, list):
        if len(training_iter0_model_path) != numb_models:
            diagnostics.append(_lint_simple(
                "training_iter0_model_path",
                "training_iter0_model_path length should match numb_models",
                "semantic",
                text,
            ))

    if "fp_style" in data:
        fp_style = data["fp_style"]
        if fp_style in ("vasp", "pwscf", "abacus", "siesta"):
            fp_pp_files = data.get("fp_pp_files", [])
            if isinstance(fp_pp_files, list) and len(fp_pp_files) != type_map_len:
                diagnostics.append(_lint_simple(
                    "fp_pp_files",
                    f"fp_pp_files length ({len(fp_pp_files)}) should match type_map length ({type_map_len})",
                    "semantic",
                    text,
                ))

    return diagnostics


# ── Workflow-specific semantic lint ─────────────────────────────────────


def _lint_run_workflow(data: dict, text: str) -> list[dict]:
    """Checks specific to dpgen run parameter files.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""
    diagnostics: list[dict] = []

    model_devi_jobs = data.get("model_devi_jobs")
    if isinstance(model_devi_jobs, list) and not model_devi_jobs:
        diagnostics.append(_lint_simple(
            "model_devi_jobs",
            "model_devi_jobs should contain at least one exploration job",
            "semantic",
            text,
        ))

    sys_configs = data.get("sys_configs")
    if isinstance(sys_configs, list) and isinstance(model_devi_jobs, list):
        max_idx = len(sys_configs) - 1
        for job_index, job in enumerate(model_devi_jobs):
            if not isinstance(job, dict):
                continue
            sys_idx = job.get("sys_idx")
            invalid: list[Any] = []
            if isinstance(sys_idx, int):
                if sys_idx < 0 or sys_idx > max_idx:
                    invalid.append(sys_idx)
            elif isinstance(sys_idx, list):
                invalid.extend(
                    idx for idx in sys_idx
                    if not isinstance(idx, int) or idx < 0 or idx > max_idx
                )
            if invalid:
                diagnostics.append(_diagnostic(
                    _find_key_line(text, "model_devi_jobs"),
                    0,
                    f"model_devi_jobs[{job_index}].sys_idx contains invalid indices {invalid}; "
                    f"valid range is 0..{max_idx}",
                    severity="error",
                    code="model_devi_jobs.sys_idx",
                    category="semantic",
                ))

    return diagnostics


def _lint_simplify_workflow(data: dict, text: str, base_dir: Path | None) -> list[dict]:
    """Checks specific to dpgen simplify parameter files.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""
    diagnostics: list[dict] = []

    for key in ("init_pick_number", "iter_pick_number"):
        value = data.get(key)
        if isinstance(value, int) and value <= 0:
            diagnostics.append(_lint_simple(
                key,
                f"{key} should be greater than 0",
                "semantic",
                text,
            ))

    pick_data = data.get("pick_data")
    if isinstance(pick_data, str) and base_dir is not None:
        resolved = base_dir / pick_data
        if not resolved.exists():
            diagnostics.append(_diagnostic(
                _find_key_line(text, "pick_data"),
                0,
                f"pick_data path does not exist: {pick_data} (resolved to {resolved})",
                severity="error",
                code="path.pick_data",
                category="semantic",
                fix_hints=[f"Create '{pick_data}' or update pick_data"],
            ))

    return diagnostics


def _lint_init_workflow(workflow: str, data: dict, text: str) -> list[dict]:
    """Checks specific to dpgen init_* parameter files.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""
    diagnostics: list[dict] = []

    stages = data.get("stages")
    if workflow in {"init_bulk", "init_surf"}:
        if not isinstance(stages, list) or not stages:
            diagnostics.append(_lint_simple(
                "stages",
                "stages should be a non-empty list for init workflows",
                "semantic",
                text,
            ))
        elif any(not isinstance(stage, int) or stage <= 0 for stage in stages):
            diagnostics.append(_lint_simple(
                "stages",
                "stages should contain positive integer stage numbers",
                "semantic",
                text,
            ))

    init_fp_style = data.get("init_fp_style")
    if workflow == "init_bulk" and isinstance(init_fp_style, str) and init_fp_style.upper() not in {"VASP", "ABACUS"}:
        diagnostics.append(_lint_simple(
            "init_fp_style",
            "init_fp_style should be VASP or ABACUS for init_bulk",
            "semantic",
            text,
        ))

    if workflow == "init_reaction":
        dataset_size = data.get("dataset_size")
        if isinstance(dataset_size, int) and dataset_size <= 0:
            diagnostics.append(_lint_simple(
                "dataset_size",
                "dataset_size should be greater than 0",
                "semantic",
                text,
            ))
        cutoff = data.get("cutoff")
        if isinstance(cutoff, (int, float)) and cutoff <= 0:
            diagnostics.append(_lint_simple(
                "cutoff",
                "cutoff should be greater than 0",
                "semantic",
                text,
            ))

    return diagnostics


# ── PR2: CP2K FP semantic lint ───────────────────────────────────────────


def _lint_cp2k_fp(data: dict, text: str) -> list[dict]:
    """CP2K-specific semantic checks for fp_params.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""
    diagnostics: list[dict] = []

    fp_style = data.get("fp_style")
    if fp_style != "cp2k":
        return diagnostics

    fp_params = data.get("fp_params", {})
    if not isinstance(fp_params, dict):
        return diagnostics

    # Check PRINT_LEVEL in GLOBAL
    global_section = fp_params.get("GLOBAL", {})
    if isinstance(global_section, dict):
        print_level = global_section.get("PRINT_LEVEL")
        if print_level is None or str(print_level).upper() not in ("MEDIUM", "LOW", "HIGH"):
            line = _find_key_line(text, "fp_params")
            diagnostics.append(_diagnostic(
                line, 0,
                "CP2K fp_params missing or invalid GLOBAL%PRINT_LEVEL. "
                "Set to MEDIUM or LOW to reduce output verbosity.",
                severity="warning",
                code="PRINT_LEVEL.lint",
                category="suggestion",
                fix_hints=[
                    "Add 'GLOBAL': {'PRINT_LEVEL': 'MEDIUM'} to fp_params"
                ],
                blocking=False,
            ))

    # Check STRESS_TENSOR in MOTION%PRINT
    motion_print = fp_params.get("MOTION", {}).get("PRINT", {})
    if isinstance(motion_print, dict):
        has_stress = "STRESS_TENSOR" in motion_print
        if not has_stress:
            line = _find_key_line(text, "fp_params")
            diagnostics.append(_diagnostic(
                line, 0,
                "CP2K fp_params missing MOTION%PRINT%STRESS_TENSOR. "
                "Virial/stress data will not be collected.",
                severity="warning",
                code="STRESS_TENSOR.lint",
                category="semantic",
                fix_hints=[
                    "Add &STRESS_TENSOR subsection under &MOTION/&PRINT "
                    "with EACH {MD} 1"
                ],
                blocking=False,
            ))

    return diagnostics


# ── PR3: Path existence preflight ────────────────────────────────────────


def _lint_path_existence(
    data: dict, text: str, base_dir: Path
) -> list[dict]:
    """Check that referenced paths (init_data_sys, sys_configs) exist.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""
    diagnostics: list[dict] = []

    # init_data_sys — required for training
    init_data_sys = data.get("init_data_sys", [])
    if isinstance(init_data_sys, list):
        for i, p in enumerate(init_data_sys):
            if not isinstance(p, str):
                continue
            resolved = base_dir / p
            if not resolved.exists():
                line = _find_key_line(text, "init_data_sys")
                diagnostics.append(_diagnostic(
                    line, 0,
                    f"init_data_sys[{i}] path does not exist: {p} "
                    f"(resolved to {resolved})",
                    severity="error",
                    code="path.init_data_sys",
                    category="semantic",
                    fix_hints=[
                        f"Create directory '{p}' or run AIMD to generate training data first"
                    ],
                ))

    # sys_configs — required for exploration
    sys_configs = data.get("sys_configs", [])
    if isinstance(sys_configs, list):
        for i, p in enumerate(sys_configs):
            if not isinstance(p, str):
                continue
            resolved = base_dir / p
            if not resolved.exists():
                line = _find_key_line(text, "sys_configs")
                diagnostics.append(_diagnostic(
                    line, 0,
                    f"sys_configs[{i}] path does not exist: {p} "
                    f"(resolved to {resolved})",
                    severity="error",
                    code="path.sys_configs",
                    category="semantic",
                    fix_hints=[
                        f"Create POSCAR file at '{p}' or update the path"
                    ],
                ))

    return diagnostics


# ── PR4: Bohrium machine type whitelist ──────────────────────────────────


def _lint_machine_type_whitelist(data: dict, text: str) -> list[dict]:
    """Warn if scass_type doesn't match known Bohrium machine types.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""
    diagnostics: list[dict] = []

    all_known = set()
    for types in KNOWN_BOHRIUM_MACHINES.values():
        all_known.update(types)

    # Track which scass_type occurrences we've already reported
    used_lines: set[int] = set()

    # machine.json: train/model_devi/fp are lists of task configs
    for section_name in ("train", "model_devi", "fp"):
        section_data = data.get(section_name)
        if not isinstance(section_data, list):
            continue

        for task in section_data:
            if not isinstance(task, dict):
                continue
            # Check machine.remote_profile.input_data.scass_type
            machine = task.get("machine", {})
            if not isinstance(machine, dict):
                continue
            remote_profile = machine.get("remote_profile", {})
            if not isinstance(remote_profile, dict):
                continue
            input_data = remote_profile.get("input_data", {})
            if not isinstance(input_data, dict):
                continue
            scass_type = input_data.get("scass_type")
            if isinstance(scass_type, str) and scass_type not in all_known:
                line = _find_next_key_line(text, "scass_type", used_lines)
                used_lines.add(line)
                known_list = ", ".join(sorted(all_known))
                diagnostics.append(_diagnostic(
                    line, 0,
                    f"scass_type '{scass_type}' not in known Bohrium machine types. "
                    f"Known types: {known_list}",
                    severity="warning",
                    code=f"machine.{section_name}.scass_type",
                    category="suggestion",
                    fix_hints=[
                        f"Use one of the known scass_type values for section '{section_name}'"
                    ],
                    blocking=False,
                ))

    return diagnostics


# ── Public API ────────────────────────────────────────────────────────────


def lint(text: str, uri: str = "", base_dir: Path | None = None) -> list[dict]:
    """
    Run semantic lint checks on dpgen JSON input.
    
    Returns list of diagnostic dicts with category 'semantic' or 'suggestion'.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""
    diagnostics: list[dict] = []

    if not text.strip():
        return diagnostics

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # JSON parse errors are handled by DiagnosticProvider
        return diagnostics

    workflow = detect_workflow(text)

    # General semantic checks
    diagnostics.extend(_lint_general_checks(data, text))

    if workflow == "run":
        diagnostics.extend(_lint_run_workflow(data, text))
    elif workflow == "simplify":
        diagnostics.extend(_lint_simplify_workflow(data, text, base_dir))
    elif workflow.startswith("init_"):
        diagnostics.extend(_lint_init_workflow(workflow, data, text))

    # CP2K-specific checks
    diagnostics.extend(_lint_cp2k_fp(data, text))

    # Path existence checks (if base_dir provided)
    if base_dir is not None:
        diagnostics.extend(_lint_path_existence(data, text, base_dir))

    # Machine type whitelist (for machine.json)
    diagnostics.extend(_lint_machine_type_whitelist(data, text))

    return diagnostics


class LintProvider:
    """Provider for semantic lint checks.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""

    def lint(self, text: str, uri: str = "", base_dir: Path | None = None) -> list[dict]:
        """Run semantic lint checks on dpgen JSON input.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""
        return lint(text, uri, base_dir)