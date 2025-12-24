#!/usr/bin/env python3
import subprocess
from resource import RLIMIT_AS, RLIMIT_CPU, setrlimit


def limit_subprocess_resources(command, timeout=10, memory_limit_mb=512):
    # Convert memory limit from MB to bytes
    memory_limit_bytes = memory_limit_mb * 1024 * 1024

    # Set resource limits for the subprocess
    setrlimit(RLIMIT_AS, (memory_limit_bytes, memory_limit_bytes))
    setrlimit(RLIMIT_CPU, (timeout, timeout))

    try:
        # Start the subprocess with limited resources
        process = subprocess.run(command, check=True, capture_output=True, text=True)
        return process.stdout
    except subprocess.CalledProcessError as e:
        return f"Command failed with error: {e.stderr}"
    except Exception as e:
        return f"An error occurred: {str(e)}"


def main():
    command = ["python", "-c", 'import time; time.sleep(5); print("Hello, World!")']
    result = limit_subprocess_resources(command)
    print(result)


if __name__ == "__main__":
    main()
