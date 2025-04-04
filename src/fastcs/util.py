import re


def snake_to_pascal(name: str) -> str:
    """Converts string from snake case to Pascal case.
    If string already in Pascal case it's returned unchanged
    """
    name = re.sub(
        r"(?:^|_)([a-z])", lambda match: match.group(1).upper(), name
    ).replace("_", "")
    return re.sub(r"_(\d+)$", r"\1", name)
