import json

def extract_value_after_return(s, h):
    """
    Extracts the value associated with "returnValue" following a specific hash in a string.

    Parameters:
    s (str): The input string containing the hash and data.
    h (str): The hash to locate in the string.

    Returns:
    any: The parsed value of "returnValue", which could be a dictionary, array, int, float, null, or string.
    """
    # Find the starting index of the hash in the string
    hash_index = s.find(h)
    if hash_index == -1:
        return None

    # The substring starts immediately after the hash
    start_index = hash_index + len(h)
    target_substring = s[start_index:]

    # Ensure the substring starts with '{"returnValue":'
    if target_substring.startswith('{"returnValue":'):
        value_start = len('{"returnValue":')

        # Extract the value by finding the matching closing brace
        brace_count = 0
        value_end = None
        for i, char in enumerate(target_substring[value_start:], start=value_start):
            if char == '{':
                brace_count += 1
            elif char == '}':
                if brace_count == 0:
                    value_end = i
                    break
                brace_count -= 1
        if value_end is None:
            return None

        # Extract the raw value
        raw_value = target_substring[value_start:value_end].strip()

        # Try to parse the raw value
        try:
            return json.loads(raw_value)
        except json.JSONDecodeError:
            # Try removing the last character if it's a closing brace
            if raw_value.endswith('}'):
                try:
                    return json.loads(raw_value[:-1].strip())
                except json.JSONDecodeError:
                    return raw_value
            # Fall back to returning the raw string
            return raw_value

    return None