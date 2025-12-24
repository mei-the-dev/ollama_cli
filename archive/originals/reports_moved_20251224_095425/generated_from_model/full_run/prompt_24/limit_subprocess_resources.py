#!/usr/bin/env python3
import subprocess
from resource import RLIMIT_AS, setrlimit
from signal import SIGKILL


def limit_subprocess_resources(command, timeout=10, memory_limit_mb=512):
    # Convert memory limit from MB to bytes
    memory_limit_bytes = memory_limit_mb * 1024 * 1024

    # Start the subprocess with resource limits
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=lambda: setrlimit(RLIMIT_AS, (memory_limit_bytes, memory_limit_bytes)),
    )

    try:
        # Wait for the process to complete with a timeout
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        # If the process times out, kill it and return an error message
        process.kill()
        return None, f"Process timed out after {timeout} seconds"

    # Return the output and any errors from the process
    return stdout.decode(), stderr.decode()


if __name__ == "__main__":
    command = ["your_command_here"]  # Replace with your actual command
    stdout, stderr = limit_subprocess_resources(command)
    if stdout:
        print("Output:\n", stdout)
    if stderr:
        print("Errors:\n", stderr)
