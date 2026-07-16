"""Code action provider for dpgen JSON input files.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""

from __future__ import annotations

from typing import Any


class CodeActionProvider:

    def get_code_actions(
        self,
        text: str,
        line: int,
        character: int,
        diagnostics: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Return quick-fix suggestions for known dpgen diagnostics.

        LLM Wiki: wiki/synthesis/openqc-agent-context.md
        """
        actions: list[dict[str, Any]] = []

        for diagnostic in diagnostics or []:
            code = str(diagnostic.get("code", ""))
            message = str(diagnostic.get("message", ""))

            if code == "fp_task_max.lint":
                actions.append(
                    {
                        "title": "Set fp_task_max to be at least fp_task_min",
                        "kind": "quickfix",
                        "command": "dpgen-lsp.fix.fp_task_max",
                        "diagnostic": diagnostic,
                    }
                )
            elif code == "model_devi_f_trust_lo.lint":
                actions.append(
                    {
                        "title": "Review model deviation trust bounds",
                        "kind": "quickfix",
                        "command": "dpgen-lsp.fix.trust_bounds",
                        "diagnostic": diagnostic,
                    }
                )
            elif code == "numb_models.lint":
                actions.append(
                    {
                        "title": "Use recommended numb_models = 4",
                        "kind": "quickfix",
                        "command": "dpgen-lsp.fix.numb_models",
                        "diagnostic": diagnostic,
                    }
                )
            elif code in {"PRINT_LEVEL.lint", "STRESS_TENSOR.lint"}:
                actions.append(
                    {
                        "title": "Apply recommended CP2K fp_params setting",
                        "kind": "quickfix",
                        "command": f"dpgen-lsp.fix.{code.removesuffix('.lint')}",
                        "diagnostic": diagnostic,
                    }
                )
            elif "length should match type_map length" in message:
                actions.append(
                    {
                        "title": "Adjust list length to match type_map",
                        "kind": "quickfix",
                        "command": "dpgen-lsp.fix.match_type_map_length",
                        "diagnostic": diagnostic,
                    }
                )

        if not actions:
            actions.append(
                {
                    "title": "Open DP-GEN input documentation",
                    "kind": "quickfix",
                    "command": "dpgen-lsp.docs.open",
                    "arguments": ["https://docs.deepmodeling.com/projects/dpgen/"],
                }
            )

        return actions

    def execute_command(self, command: str, arguments: list) -> Any:
        """Placeholder command execution hook for editor clients.

        LLM Wiki: wiki/synthesis/openqc-agent-context.md
        """
        return {"command": command, "arguments": arguments}
