#!/usr/bin/env python3

import unittest
from subprocess import run, PIPE

class TestCLIExitCodes(unittest.TestCase):
    def test_success_case(self):
        # Run the CLI command that should succeed
        result = run(['your-cli-command', '--success'], stdout=PIPE, stderr=PIPE)
        self.assertEqual(result.returncode, 0, 'Success case should return exit code 0')
        self.assertIn(b'Success message', result.stdout, 'Expected success message in stdout')

    def test_failure_case(self):
        # Run the CLI command that should fail
        result = run(['your-cli-command', '--failure'], stdout=PIPE, stderr=PIPE)
        self.assertEqual(result.returncode, 1, 'Failure case should return exit code 1')
        self.assertIn(b'Error message', result.stderr, 'Expected error message in stderr')

if __name__ == '__main__':
    unittest.main()
