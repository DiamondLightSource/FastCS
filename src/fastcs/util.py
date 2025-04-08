import re


def snake_to_pascal(name: str) -> str:
    """Converts string from snake case to Pascal case.
    If string is not a valid snake case it will be returned unchanged
    """
    if re.fullmatch(r"[a-z]+(?:_[a-z]+|_[0-9]+)*", name):
        name = re.sub(
            r"(?:^|_)([a-z]|[0-9])", lambda match: match.group(1).upper(), name
        )
    return name
