# json_streaming_parser.py
import ijson

def parse_large_json(file_path):
    """
    Parses a large JSON file using ijson to stream through the data without loading it all into memory.
    
    Args:
        file_path (str): The path to the JSON file to be parsed.
    
    Yields:
        dict: Each JSON object in the file as a dictionary.
    """
    with open(file_path, 'rb') as file:
        # Create an ijson parser object
        parser = ijson.parse(file)
        current_object = {}
        keys_stack = []
        
        for prefix, event, value in parser:
            if (prefix, event) == ('item', 'map_key'):
                keys_stack.append(value)
            elif event == 'string':
                key = keys_stack.pop()
                current_object[key] = value
            elif event == 'number':
                key = keys_stack.pop()
                current_object[key] = value
            elif event == 'end_map':
                if len(keys_stack) == 0:
                    yield current_object
                    current_object = {}
                else:
                    key = keys_stack[-1]
                    current_object[key] = current_object
                    current_object = {}

if __name__ == '__main__':
    file_path = 'path/to/large_json_file.json'
    for json_obj in parse_large_json(file_path):
        print(json_obj)
