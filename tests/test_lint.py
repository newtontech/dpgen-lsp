"""Tests for semantic lint checks."""

import json
from pathlib import Path

from dpgen_lsp.features.lint import lint


def _codes(text: str, base_dir: Path | None = None) -> set[str]:
    return {diag["code"] for diag in lint(text, base_dir=base_dir)}


def test_lint_training_iter0_model_path_matches_numb_models():
    data = {
        "type_map": ["H"],
        "numb_models": 4,
        "training_iter0_model_path": ["graph.000.pb"],
    }

    assert "training_iter0_model_path.lint" in _codes(json.dumps(data))


def test_lint_model_devi_sys_idx_range():
    data = {
        "type_map": ["H"],
        "numb_models": 4,
        "sys_configs": ["sys-000/POSCAR"],
        "model_devi_jobs": [{"sys_idx": [0, 2]}],
    }

    assert "model_devi_jobs.sys_idx" in _codes(json.dumps(data))


def test_lint_simplify_pick_data_path_and_positive_counts(tmp_path):
    data = {
        "pick_data": "missing-data",
        "init_pick_number": 0,
        "iter_pick_number": -1,
    }

    codes = _codes(json.dumps(data), base_dir=tmp_path)
    assert "path.pick_data" in codes
    assert "init_pick_number.lint" in codes
    assert "iter_pick_number.lint" in codes


def test_lint_init_bulk_stages_and_fp_style():
    data = {
        "stages": [1, "bad"],
        "md_nstep": 10,
        "init_fp_style": "QE",
    }

    codes = _codes(json.dumps(data))
    assert "stages.lint" in codes
    assert "init_fp_style.lint" in codes


def test_lint_init_reaction_positive_values():
    data = {
        "type_map": ["C"],
        "reaxff": {},
        "dataset_size": 0,
        "cutoff": -1,
    }

    codes = _codes(json.dumps(data))
    assert "dataset_size.lint" in codes
    assert "cutoff.lint" in codes
