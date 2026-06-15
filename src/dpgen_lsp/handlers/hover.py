"""LSP hover handler.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""

from typing import Any

from lsprotocol.types import Hover, HoverParams, MarkupContent, MarkupKind

from ..features.hover import hover_contents
from .json_utils import get_document_text


def hover(ls: Any, params: HoverParams) -> Hover | None:
    uri = params.text_document.uri
    text = get_document_text(ls, uri)
    if not text:
        return None

    line = params.position.line
    character = params.position.character

    contents = hover_contents(text, line, character)
    if contents is None:
        return None

    return Hover(
        contents=MarkupContent(kind=MarkupKind.Markdown, value=contents),
    )