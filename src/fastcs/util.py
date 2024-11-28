def snake_to_pascal(input: str) -> str:
    """Convert a snake_case string to PascalCase."""
    return "".join(
        part.title() if part.islower() else part for part in input.split("_")
    )
