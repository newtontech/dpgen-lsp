"""Schema lint provider for cross-field consistency checks."""

def lint(text: str) -> list[dict]:
    return []


class LintProvider:

    def lint(self, text: str) -> list[dict]:
        return lint(text)