#!/usr/bin/env python3
import threading
import os
import unittest

class ConcurrentWriteTest(unittest.TestCase):
    def setUp(self):
        self.file_path = 'test_file.txt'
        # Ensure the file is empty before each test
        open(self.file_path, 'w').close()

    def tearDown(self):
        # Clean up after each test
        os.remove(self.file_path)

    def write_to_file(self, content):
        with open(self.file_path, 'a') as f:
            f.write(content)

    def test_concurrent_writes(self):
        # Define the number of threads and the content to write
        num_threads = 10
        content = 'Test Content\n'

        # Create a list to hold all threads
        threads = []

        # Start multiple threads writing to the file concurrently
        for _ in range(num_threads):
            thread = threading.Thread(target=self.write_to_file, args=(content,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Read the content of the file after all writes are done
        with open(self.file_path, 'r') as f:
            written_content = f.read()

        # Assert that each write was atomic and correct
        expected_content = content * num_threads
        self.assertEqual(written_content, expected_content)

if __name__ == '__main__':
    unittest.main()