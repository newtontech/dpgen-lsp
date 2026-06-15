"""LSP code action handler."""

from typing import Any

from lsprotocol.types import CodeAction, CodeActionKind, CodeActionParams, Command

from .json_utils import get_document_text


def code_action(ls: Any, params: CodeActionParams) -> list[CodeAction] | None:
    text = get_document_text(ls, params.text_document.uri)
    if not text:
        return None

    raw_diagnostics = []
    for diagnostic in params.context.diagnostics or []:
        raw_diagnostics.append({
            "code": getattr(diagnostic, "code", ""),
            "message": getattr(diagnostic, "message", ""),
            "severity": str(getattr(diagnostic, "severity", "")),
        })

    provider = getattr(ls, "code_action_provider", None)
    if provider is None:
        return None

    line = params.range.start.line
    character = params.range.start.character
    actions = provider.get_code_actions(text, line, character, raw_diagnostics)

    result: list[CodeAction] = []
    for action in actions:
        result.append(CodeAction(
            title=action.get("title", "DP-GEN action"),
            kind=CodeActionKind.QuickFix,
            command=Command(
                title=action.get("title", "DP-GEN action"),
                command=action.get("command", "dpgen-lsp.noop"),
                arguments=action.get("arguments", []),
            ),
        ))

    return result or None