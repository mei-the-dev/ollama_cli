# generator.py


def is_binary_file(file_path):
    """
    Check if a file is binary by reading the first few bytes.
    """
    with open(file_path, "rb") as f:
        chunk = f.read(1024)
        return b"\0" in chunk


def read_lines_with_encoding(file_path):
    """
    Read lines from a file while handling different encodings.
    Tries to decode with UTF-8 first, then falls back to ISO-8859-1.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                yield line
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="iso-8859-1") as f:
            for line in f:
                yield line


def file_line_generator(directory):
    """
    Generator that yields lines from text files in a directory.
    Skips binary files and handles different encodings.
    """
    import os

    for root, _, files in os.walk(directory):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            if not is_binary_file(file_path):
                yield from read_lines_with_encoding(file_path)
