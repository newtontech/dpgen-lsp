"""LSP rename handler."""

from __future__ import annotations

from typing import Any

from lsprotocol.types import TextEdit, WorkspaceEdit

from .text_utils import find_token_ranges, get_document_text, word_at


def rename(ls: Any, params: Any) -> WorkspaceEdit | None:
    uri = params.text_document.uri
    text = get_document_text(ls, uri)
    if not text:
        return None

    selected = word_at(text, params.position.line, params.position.character)
    if selected is None:
        return None
    token, _ = selected
    edits = [
        TextEdit(range=token_range, new_text=params.new_name)
        for token_range in find_token_ranges(text, token)
    ]
    return WorkspaceEdit(changes={uri: edits}) if edits else None


def prepare_rename(ls: Any, params: Any) -> Any:
    text = get_document_text(ls, params.text_document.uri)
    selected = word_at(text, params.position.line, params.position.character)
    if selected is None:
        return None
    _, token_range = selected
    return token_range
