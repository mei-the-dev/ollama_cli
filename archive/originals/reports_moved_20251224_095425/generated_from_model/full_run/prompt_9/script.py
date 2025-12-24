#!/usr/bin/env python3
import subprocess


def run_shell_command(command):
    """
    Safely runs a shell command and captures stdout/stderr.

    Args:
        command (list): A list of strings representing the command and its arguments.

    Returns:
        tuple: A tuple containing the return code, stdout, and stderr as strings.
    """
    try:
        # Run the command using subprocess.run with capture_output=True to capture stdout and stderr
        result = subprocess.run(command, check=False, capture_output=True, text=True)

        # Return the return code, stdout, and stderr
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        # Handle any exceptions that occur during command execution
        return -1, "", f"An error occurred: {str(e)}"


if __name__ == "__main__":
    # Example usage of the run_shell_command function
    command = ["ls", "-l"]  # Replace with your desired shell command and arguments
    return_code, stdout, stderr = run_shell_command(command)

    print(f"Return Code: {return_code}")
    print("Standard Output:")
    print(stdout)
    print("Standard Error:")
    print(stderr)
