# Function to annotate code with line numbers and show a snippet for diagnostics


def annotate_code(code_snippet, start_line=1):
    """
    Annotates a given piece of code with line numbers starting from the specified start_line.
    Returns a string with each line prefixed by its line number followed by a colon and a space.

    :param code_snippet: A multi-line string containing the code to be annotated.
    :param start_line: The line number to start annotation from. Default is 1.
    :return: A string with each line of the code snippet prefixed by its line number.
    """
    lines = code_snippet.split("\n")
    annotated_lines = [f"{start_line + i}: {line}" for i, line in enumerate(lines)]
    return "\n".join(annotated_lines)


# Example usage:
if __name__ == "__main__":
    code = """
def hello_world():
    print('Hello, world!')
hello_world()"""
    annotated_code = annotate_code(code, start_line=10)
    print(annotated_code)
