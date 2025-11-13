"""
Unit tests for utility functions.
"""

import unittest
from unittest.mock import patch, MagicMock
import subprocess
from kernsweep.utils import run_command, needs_reboot


class TestRunCommand(unittest.TestCase):
    """Test command execution wrapper."""
    
    @patch('subprocess.run')
    def test_run_command_success(self, mock_run):
        """Test successful command execution."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="output text",
            stderr=""
        )
        
        returncode, stdout, stderr = run_command(["echo", "test"])
        
        self.assertEqual(returncode, 0)
        self.assertEqual(stdout, "output text")
        self.assertEqual(stderr, "")
        
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        self.assertEqual(call_args[0][0], ["echo", "test"])
    
    @patch('subprocess.run')
    def test_run_command_failure(self, mock_run):
        """Test failed command execution."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error message"
        )
        
        returncode, stdout, stderr = run_command(["false"])
        
        self.assertEqual(returncode, 1)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "error message")
    
    @patch('subprocess.run')
    def test_run_command_exception_check_true(self, mock_run):
        """Test command execution with exception and check=True (default)."""
        mock_run.side_effect = subprocess.CalledProcessError(127, ["nonexistent"])
        
        with self.assertRaises(subprocess.CalledProcessError):
            run_command(["nonexistent"])
    
    @patch('subprocess.run')
    def test_run_command_exception_check_false(self, mock_run):
        """Test command execution with exception and check=False."""
        error = subprocess.CalledProcessError(127, ["nonexistent"])
        error.stdout = ""
        error.stderr = "command not found"
        mock_run.side_effect = error
        
        returncode, stdout, stderr = run_command(["nonexistent"], check=False)
        
        self.assertEqual(returncode, 127)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "command not found")


class TestNeedsReboot(unittest.TestCase):
    """Test reboot detection."""
    
    @patch('os.path.exists')
    def test_needs_reboot_true(self, mock_exists):
        """Test when reboot is needed."""
        mock_exists.return_value = True
        
        result = needs_reboot()
        
        self.assertTrue(result)
        mock_exists.assert_called_once_with("/var/run/reboot-required")
    
    @patch('os.path.exists')
    def test_needs_reboot_false(self, mock_exists):
        """Test when reboot is not needed."""
        mock_exists.return_value = False
        
        result = needs_reboot()
        
        self.assertFalse(result)
        mock_exists.assert_called_once_with("/var/run/reboot-required")
    
    @patch('os.path.exists')
    def test_needs_reboot_oserror(self, mock_exists):
        """Test when OS error occurs checking reboot file."""
        mock_exists.side_effect = OSError("Permission denied")
        
        result = needs_reboot()
        
        # Should return False on error
        self.assertFalse(result)
    
    @patch('os.path.exists')
    def test_needs_reboot_permission_error(self, mock_exists):
        """Test when permission error occurs checking reboot file."""
        mock_exists.side_effect = PermissionError("Access denied")
        
        result = needs_reboot()
        
        # Should return False on error
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
