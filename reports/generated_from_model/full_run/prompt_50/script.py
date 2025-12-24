#!/usr/bin/env python3
import signal
import sys


def cleanup_handler(signum, frame):
    # Perform any necessary cleanup here
    print(f"Received {signal.Signals(signum).name}, performing cleanup...")
    sys.exit(0)


# Register the signal handlers for SIGINT and SIGTERM
signal.signal(signal.SIGINT, cleanup_handler)
signal.signal(signal.SIGTERM, cleanup_handler)


def main():
    # Your main task logic here
    while True:
        pass


if __name__ == "__main__":
    main()
