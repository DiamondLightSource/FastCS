def snake_to_pascal(input: str) -> str:
    """Convert a snake_case string to PascalCase."""
    return "".join(
        part.title() if part.islower() else part for part in input.split("_")
    )

def unpack_status_arrays(parameter: list, uri: list[list[str]]):
    """Takes a list of parameters and a list of special uri. Search the parameter
    for elements that match the values in the uri list and split them into one
    new odinParameter for each value.

    Args:
        parameter: List of parameters
        uri: List of special uris to search and replace

    Returns:
        list[parameters]

    """
    removelist = []
    for el in parameter:
        if el.uri in uri:
            status_list = (
                el.metadata["value"]
                .replace(",", "")
                .replace("'", "")
                .replace("[", "")
                .replace("]", "")
                .split()
            )
            for idx, value in enumerate(status_list):
                metadata = {
                    "value": value,
                    "type": el.metadata["type"],
                    "writeable": el.metadata["writeable"],
                }
                od_parameter = OdinParameter(uri=el.uri + [str(idx)], metadata=metadata)
                parameter.append(od_parameter)
            removelist.append(el)

    for value in removelist:
        parameter.remove(value)

    return parameter
