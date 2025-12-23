# fsutils.py
import os

def ensure_dir(path):
    """
    Ensure that the directory specified by `path` exists.
    If it does not exist, create it.
    
    Args:
        path (str): The directory path to ensure.
    """
    if not os.path.exists(path):
        os.makedirs(path)

# tests.py
import unittest
from fsutils import ensure_dir
temp_dir = '/tmp/test_fsutils'

class TestFSUtils(unittest.TestCase):
    def setUp(self):
        # Ensure the temp directory does not exist before each test
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

    def tearDown(self):
        # Clean up the temp directory after each test
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

    def test_ensure_dir_exists(self):
        ensure_dir(temp_dir)
        self.assertTrue(os.path.exists(temp_dir))

    def test_ensure_dir_nested(self):
        nested_dir = '/tmp/test_fsutils/nested'
        ensure_dir(nested_dir)
        self.assertTrue(os.path.exists(nested_dir))

if __name__ == '__main__':
    unittest.main()
