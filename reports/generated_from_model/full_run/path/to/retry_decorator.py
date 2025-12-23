import time
import random
from functools import wraps
def retry_with_exponential_backoff_and_jitter(max_retries=5, base_delay=1, max_delay=60):
    """
    Decorator to implement exponential backoff with jitter for network calls.
    
    Args:
        max_retries (int): Maximum number of retries.
        base_delay (float): Initial delay between retries in seconds.
        max_delay (float): Maximum delay between retries in seconds.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            while attempt < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f'Attempt {attempt + 1} failed: {e}')
                    if attempt == max_retries - 1:
                        raise
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = random.uniform(0, delay / 2)
                    time.sleep(delay + jitter)
                    attempt += 1
        return wrapper
    return decorator