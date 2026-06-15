"""LSP completion handler.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""

from typing import Any

from lsprotocol.types import (
    CompletionItem,
    CompletionList,
    CompletionParams,
    InsertTextFormat,
)

from ..features.completion import completion_items
from .json_utils import get_document_text


def completion(ls: Any, params: CompletionParams) -> CompletionList | list[CompletionItem] | None:
    uri = params.text_document.uri
    text = get_document_text(ls, uri)
    if not text:
        return None

    line = params.position.line
    character = params.position.character

    items = completion_items(text, line, character)

    result: list[CompletionItem] = []
    for item in items:
        ci = CompletionItem(
            label=item.get("label", ""),
            detail=item.get("detail"),
            documentation=item.get("documentation"),
            kind=item.get("kind", 1),
        )
        if "insertText" in item:
            ci.insert_text = item["insertText"]
            ci.insert_text_format = InsertTextFormat.Snippet
        result.append(ci)

    return result if result else None