import json
from dataclasses import asdict
from datetime import datetime


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


def serialize_dataclass_to_json(dataclass_instance):
    """
    Serialize a dataclass instance to JSON string with support for datetime objects.
    :param dataclass_instance: An instance of a dataclass
    :return: A JSON string representation of the dataclass
    """
    return json.dumps(asdict(dataclass_instance), cls=DateTimeEncoder)
