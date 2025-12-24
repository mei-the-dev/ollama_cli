import json
from dataclasses import asdict
from datetime import datetime


def serialize_dataclass_to_json(dataclass_instance):
    # Convert the dataclass to a dictionary
    data_dict = asdict(dataclass_instance)

    # Custom encoder for datetime objects
    def custom_encoder(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

    # Serialize the dictionary to a JSON string with the custom encoder
    json_string = json.dumps(data_dict, default=custom_encoder)
    return json_string
