"""Type/value checking for dpgen input parameters."""

def typecheck(text: str) -> list[dict]:
    return []


class TypecheckProvider:

    def typecheck(self, text: str) -> list[dict]:
        return typecheck(text)