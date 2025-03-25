import re


def snake_to_pascal(input: str) -> str:
    # for part in re.split(r'[-_]', input):
    """Convert a snake_case string to PascalCase."""
    return "".join(
        part.title() if part.islower() else part for part in re.split(r"[_-]", input)
    )
