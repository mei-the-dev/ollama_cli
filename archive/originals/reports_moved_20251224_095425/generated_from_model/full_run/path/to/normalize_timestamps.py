# Import necessary libraries
import datetime


def normalize_to_timezone_aware_iso(timestamp):
    """
    Normalize a given timestamp to timezone-aware ISO format.

    Args:
        timestamp (datetime.datetime): The timestamp to be normalized.

    Returns:
        str: The timezone-aware ISO formatted string of the timestamp.
    """
    if timestamp.tzinfo is None:
        # Assume UTC if no timezone information is present
        timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
    return timestamp.isoformat()
