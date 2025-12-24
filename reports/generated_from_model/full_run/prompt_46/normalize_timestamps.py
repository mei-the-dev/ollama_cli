#!/usr/bin/env python3
import datetime


def normalize_to_timezone_aware_iso(timestamp):
    """
    Normalize a given timestamp to timezone-aware ISO format.

    Args:
        timestamp (datetime.datetime): The input timestamp which may or may not be timezone-aware.

    Returns:
        str: A string representing the timestamp in timezone-aware ISO format.
    """
    if timestamp.tzinfo is None:
        # Assume UTC if no timezone information is present
        timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
    return timestamp.isoformat()
