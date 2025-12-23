import time
import random
from functools import wraps
def retry_with_exponential_backoff_and_jitter(max_retries=5, initial_delay=1, backoff_factor=2, max_delay=60):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f'Attempt {retries + 1} failed: {e}')
                    if retries >= max_retries - 1:
                        raise
                    delay = min(initial_delay * (backoff_factor ** retries), max_delay) + random.uniform(0, 0.5)
                    time.sleep(delay)
                    retries += 1
        return wrapper
    return decorator