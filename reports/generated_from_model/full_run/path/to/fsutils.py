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
        print(f'Directory created: {path}')
    else:
        print(f'Directory already exists: {path}')

# tests.py
import unittest
from fsutils import ensure_dir
import tempfile
import shutil

class TestFSUtils(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_ensure_dir_exists(self):
        # Create a directory and check if ensure_dir does not recreate it
        os.makedirs(os.path.join(self.temp_dir, 'testdir'))
        ensure_dir(os.path.join(self.temp_dir, 'testdir'))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, 'testdir')))

    def test_ensure_dir_not_exists(self):
        # Check if ensure_dir creates a directory that does not exist
        dir_path = os.path.join(self.temp_dir, 'newdir')
        ensure_dir(dir_path)
        self.assertTrue(os.path.exists(dir_path))

if __name__ == '__main__':
    unittest.main()
