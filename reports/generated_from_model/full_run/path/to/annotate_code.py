# Function to annotate code with line numbers and show a snippet for diagnostics

def annotate_code(code_snippet, start_line=1):
    """
    Annotates a given piece of code with line numbers starting from `start_line`.
    Returns the annotated code as a string.

    :param code_snippet: A multi-line string containing the code to be annotated.
    :param start_line: The line number to start annotation from (default is 1).
    :return: Annotated code as a string.
    """
    lines = code_snippet.split('\n')
    annotated_lines = [f'{start_line + i}: {line}' for i, line in enumerate(lines)]
    return '\n'.join(annotated_lines)

# Example usage:
if __name__ == '__main__':
    code = """
def hello_world():
    print('Hello, world!')
hello_world()"""
    annotated_code = annotate_code(code, start_line=10)
    print(annotated_code)