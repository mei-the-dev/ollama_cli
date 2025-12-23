# Import necessary libraries
import json
from dataclasses import asdict
from datetime import datetime
class DateTimeEncoder(json.JSONEncoder):
    # Custom JSON encoder to handle datetime objects
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)
def serialize_dataclass_to_json(dataclass_instance):
    # Convert dataclass instance to dictionary and then to JSON string
    data_dict = asdict(dataclass_instance)
    json_string = json.dumps(data_dict, cls=DateTimeEncoder)
    return json_string