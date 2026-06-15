"""LSP code action handler."""

from __future__ import annotations

from typing import Any

from lsprotocol.types import CodeAction, CodeActionKind, CodeActionParams

from ..features.diagnostic import DiagnosticProvider
from .text_utils import get_document_text


def code_action(ls: Any, params: CodeActionParams) -> list[CodeAction] | None:
    uri = params.text_document.uri
    text = get_document_text(ls, uri)
    if not text:
        return None

    diagnostics = DiagnosticProvider().get_diagnostics(text, uri)
    actions: list[CodeAction] = []
    for diagnostic in diagnostics:
        hints = diagnostic.get("fix_hints") or [
            "Review this DP-GEN diagnostic before launching the workflow."
        ]
        for index, hint in enumerate(hints[:3]):
            actions.append(
                CodeAction(
                    title=str(hint),
                    kind=CodeActionKind.QuickFix,
                    data={
                        "source": "dpgen-lsp",
                        "diagnosticCode": diagnostic.get("code"),
                        "hintIndex": index,
                        "manualRef": diagnostic.get("manual_ref"),
                        "safeToAutoApply": False,
                    },
                )
            )
    return actions or None
