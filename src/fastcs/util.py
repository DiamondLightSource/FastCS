def snake_to_pascal(input: str) -> str:
    """Convert a snake_case or UPPER_SNAKE_CASE string to PascalCase."""
    return input.lower().replace("_", " ").title().replace(" ", "")
