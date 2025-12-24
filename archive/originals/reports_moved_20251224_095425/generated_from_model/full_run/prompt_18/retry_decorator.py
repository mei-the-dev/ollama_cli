import random
import time
from functools import wraps


def retry_with_exponential_backoff_and_jitter(max_retries=5, initial_delay=1, backoff_factor=2, max_delay=60):
    """
    Decorator to implement exponential backoff with jitter for network calls.

    Args:
        max_retries (int): Maximum number of retries.
        initial_delay (float): Initial delay in seconds before the first retry.
        backoff_factor (float): Factor by which the delay is multiplied after each retry.
        max_delay (float): Maximum delay between retries.

    Returns:
        function: Decorated function with retry logic.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries:
                        raise e
                    print(f"Retry {attempt + 1} failed: {e}. Retrying in {delay:.2f} seconds.")
                    time.sleep(delay)
                    delay = min(max_delay, delay * backoff_factor) + random.uniform(0, delay / 4)

        return wrapper

    return decorator
