#!/usr/bin/env python3
import platform


def detect_os():
    """
    Detects the OS distribution and version, then prints a friendly message.
    """
    os_name = platform.system()
    if os_name == "Linux":
        distro = platform.linux_distribution()[0]
        version = platform.linux_distribution()[1]
        print(f"Welcome to {distro} {version}!")
    elif os_name == "Windows":
        version = platform.version()
        print(f"Welcome to Windows {version}!")
    elif os_name == "Darwin":
        print("Welcome to macOS!")
    else:
        print("Welcome to an unknown OS!")


if __name__ == "__main__":
    detect_os()
