# json_stream_parser.py

import ijson


def parse_large_json(file_path):
    """
    Parses a large JSON file using ijson to stream the data without loading it all into memory.

    Args:
        file_path (str): The path to the JSON file to be parsed.

    Yields:
        dict: Each JSON object in the file as a dictionary.
    """
    with open(file_path, "rb") as file:
        # Use ijson to parse the file incrementally
        parser = ijson.parse(file)
        current_object = {}
        keys = []
        for prefix, event, value in parser:
            if (prefix, event) == ("item", "map_key"):
                keys.append(value)
            elif event == "string":
                current_object[keys[-1]] = value
            elif event == "number":
                current_object[keys[-1]] = value
            elif event == "end_map":
                yield current_object
                current_object = {}
                keys = []


if __name__ == "__main__":
    # Example usage: replace '/path/to/large.json' with the path to your JSON file
    for obj in parse_large_json("/path/to/large.json"):
        print(obj)
