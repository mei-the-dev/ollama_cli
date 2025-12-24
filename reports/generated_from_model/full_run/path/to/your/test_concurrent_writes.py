#!/usr/bin/env python3
import os
import threading
import time


def write_to_file(filename, content):
    with open(filename, "a") as f:
        f.write(content)


def test_concurrent_writes():
    filename = "testfile.txt"
    # Clear the file before starting tests
    if os.path.exists(filename):
        os.remove(filename)

    # Define a simple write operation
    def write_operation(id):
        for _ in range(10):
            write_to_file(filename, f"Write from thread {id}\n")
            time.sleep(0.01)  # Simulate some delay

    # Create multiple threads to simulate concurrent writes
    threads = [threading.Thread(target=write_operation, args=(i,)) for i in range(5)]

    # Start all threads
    for thread in threads:
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Read the file content and check for atomicity and correctness
    with open(filename, "r") as f:
        content = f.read()

    # Check that each write operation is correctly recorded
    expected_lines = set(f"Write from thread {i}\n" for i in range(5))
    actual_lines = set(content.split("\n")) - {""}  # Remove empty lines if any

    assert actual_lines == expected_lines, f"Expected {expected_lines}, but got {actual_lines}"

    print("All tests passed!")


if __name__ == "__main__":
    test_concurrent_writes()
