"""LSP rename handler."""

from typing import Any

from lsprotocol.types import Position, Range, TextEdit, WorkspaceEdit

from .json_utils import get_document_text, iter_json_key_occurrences, key_at_position


_SCHEMA_KEYS = {
    "type_map",
    "mass_map",
    "init_data_sys",
    "sys_configs",
    "numb_models",
    "default_training_param",
    "model_devi_jobs",
    "fp_style",
    "fp_task_max",
    "fp_task_min",
}


def rename(ls: Any, params: Any) -> Any:
    uri = params.text_document.uri
    text = get_document_text(ls, uri)
    if not text:
        return None

    occ = key_at_position(text, params.position.line, params.position.character)
    if occ is None or occ.key in _SCHEMA_KEYS:
        return None

    edits: list[TextEdit] = []
    for other in iter_json_key_occurrences(text):
        if other.key != occ.key:
            continue
        edits.append(TextEdit(
            range=Range(
                start=Position(line=other.line, character=other.character),
                end=Position(line=other.line, character=other.end_character),
            ),
            new_text=params.new_name,
        ))

    return WorkspaceEdit(changes={uri: edits}) if edits else None


def prepare_rename(ls: Any, params: Any) -> Any:
    text = get_document_text(ls, params.text_document.uri)
    if not text:
        return None

    occ = key_at_position(text, params.position.line, params.position.character)
    if occ is None or occ.key in _SCHEMA_KEYS:
        return None

    return Range(
        start=Position(line=occ.line, character=occ.character),
        end=Position(line=occ.line, character=occ.end_character),
    )