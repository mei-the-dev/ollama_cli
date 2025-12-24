#!/usr/bin/env python3
import subprocess
import unittest


class TestCLIExitCodes(unittest.TestCase):
    def test_success_case(self):
        # Run the CLI command that should succeed
        result = subprocess.run(["your-cli-command", "--success"], capture_output=True)
        # Check if the exit code is 0 (success)
        self.assertEqual(result.returncode, 0)
        # Optionally, check the output for success message
        self.assertIn(b"Success message", result.stdout)

    def test_failure_case(self):
        # Run the CLI command that should fail
        result = subprocess.run(["your-cli-command", "--failure"], capture_output=True)
        # Check if the exit code is non-zero (failure)
        self.assertNotEqual(result.returncode, 0)
        # Optionally, check the output for failure message
        self.assertIn(b"Failure message", result.stderr)


if __name__ == "__main__":
    unittest.main()
