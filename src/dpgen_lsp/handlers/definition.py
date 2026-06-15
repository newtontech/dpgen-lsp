"""LSP go-to-definition handler."""

from __future__ import annotations

from typing import Any

from lsprotocol.types import Location

from ..schema.loader import detect_workflow
from ..schema.official_rules import manual_ref_for
from .text_utils import empty_range, get_document_text, word_at


def definition(ls: Any, params: Any) -> list[Location] | None:
    text = get_document_text(ls, params.text_document.uri)
    if not text:
        return None

    selected = word_at(text, params.position.line, params.position.character)
    if selected is None:
        return None
    token, _ = selected
    workflow = "machine" if "machine" in params.text_document.uri.lower() else detect_workflow(text)
    manual_ref = manual_ref_for(workflow, field=token)
    if not manual_ref:
        return None
    return [Location(uri=manual_ref, range=empty_range())]
