import re


def snake_to_pascal(name: str) -> str:
    """Converts string from snake case to Pascal case.
    If string already in Pascal case it's returned unchanged
    """
    if re.fullmatch(r"[a-z]+(?:_[a-z]+|_[0-9]+)*", name):
        name = re.sub(
            r"(?:^|_)([a-z]|[0-9])", lambda match: match.group(1).upper(), name
        )
    return name
