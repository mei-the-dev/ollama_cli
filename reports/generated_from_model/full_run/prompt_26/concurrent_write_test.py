#!/usr/bin/env python3
import os
import threading
import unittest


class TestConcurrentWrites(unittest.TestCase):
    def setUp(self):
        self.file_path = "testfile.txt"
        # Ensure the file is empty before each test
        open(self.file_path, "w").close()

    def tearDown(self):
        # Clean up after each test
        os.remove(self.file_path)

    def write_to_file(self, content):
        with open(self.file_path, "a") as f:
            f.write(content)

    def test_concurrent_writes(self):
        num_threads = 10
        threads = []
        expected_content = "test" * num_threads

        # Create and start multiple threads to write to the file concurrently
        for _ in range(num_threads):
            thread = threading.Thread(target=self.write_to_file, args=("test",))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Read the content of the file after all writes are done
        with open(self.file_path, "r") as f:
            actual_content = f.read()

        # Assert that the content is correct and atomic
        self.assertEqual(actual_content, expected_content)


if __name__ == "__main__":
    unittest.main()
