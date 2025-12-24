# fsutils.py
import os


def ensure_dir(path):
    """
    Ensure that the directory at the specified path exists.
    If it does not exist, create it.

    Args:
        path (str): The path to the directory.
    """
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Directory created: {path}")
    else:
        print(f"Directory already exists: {path}")


import shutil
import tempfile

# tests.py
import unittest

from fsutils import ensure_dir


class TestFSUtils(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_ensure_dir_exists(self):
        ensure_dir(self.test_dir)
        self.assertTrue(os.path.exists(self.test_dir))

    def test_ensure_dir_created(self):
        new_dir = os.path.join(self.test_dir, "new_subdir")
        ensure_dir(new_dir)
        self.assertTrue(os.path.exists(new_dir))


if __name__ == "__main__":
    unittest.main()
