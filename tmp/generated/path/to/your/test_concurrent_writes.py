#!/usr/bin/env python3
import threading
import time
import os

def write_to_file(file_path, content):
    with open(file_path, 'a') as file:
        file.write(content)
        time.sleep(0.1)  # Simulate some processing time

def test_concurrent_writes():
    file_path = '/tmp/test_concurrent_writes.txt'
    os.remove(file_path) if os.path.exists(file_path) else None
    threads = []
    for i in range(5):
        thread = threading.Thread(target=write_to_file, args=(file_path, f'Write {i}\n'))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()
    with open(file_path, 'r') as file:
        content = file.read()
    assert len(content.splitlines()) == 5, "The number of lines written should be equal to the number of threads"
    print("All tests passed!")

if __name__ == '__main__':
    test_concurrent_writes()