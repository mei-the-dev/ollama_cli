# Function to read the contents of a file


def read_file(path):
    """
    Reads and returns the contents of a file.

    Args:
        path (str): The path to the file to be read.

    Returns:
        str: The contents of the file.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        IOError: If an error occurs while reading the file.
    """
    try:
        with open(path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"The file {path} does not exist.")
    except IOError as e:
        raise IOError(f"An error occurred while reading the file: {e}")
