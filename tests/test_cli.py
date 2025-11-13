"""
Integration tests for the CLI.

Tests the complete workflow with mocked system calls.
"""

import unittest
from unittest.mock import patch, MagicMock, call
from io import StringIO

from kernsweep.cli import main


class TestCLIIntegration(unittest.TestCase):
    """Integration tests for the CLI workflow."""
    
    @patch('kernsweep.detector.subprocess.run')
    @patch('sys.stdout', new_callable=StringIO)
    def test_cli_dry_run_with_obsolete_kernels(self, mock_stdout, mock_run):
        """Test dry-run mode with obsolete kernels present."""
        # Mock system responses
        def mock_subprocess(cmd, **kwargs):
            if cmd[0] == "uname":
                return MagicMock(stdout="5.15.0-82-generic\n", returncode=0)
            elif cmd[0] == "dpkg":
                return MagicMock(
                    stdout="""ii  linux-image-5.15.0-75-generic   5.15.0-75.82  amd64
ii  linux-image-5.15.0-82-generic   5.15.0-82.91  amd64
ii  linux-image-5.15.0-91-generic   5.15.0-91.101 amd64
ii  linux-headers-5.15.0-75-generic  5.15.0-75.82  amd64
ii  linux-headers-5.15.0-82-generic  5.15.0-82.91  amd64
ii  linux-headers-5.15.0-91-generic  5.15.0-91.101 amd64
""",
                    returncode=0,
                )
        
        mock_run.side_effect = mock_subprocess
        
        # Run CLI with --dry-run
        exit_code = main(["--dry-run"])
        
        # Check results
        self.assertEqual(exit_code, 0)
        output = mock_stdout.getvalue()
        
        # Verify key information in output
        self.assertIn("5.15.0-75-generic", output)  # Obsolete kernel version
        self.assertIn("to remove", output)  # Apt-style message
        self.assertIn("DRY RUN", output)
    
    @patch('kernsweep.detector.subprocess.run')
    @patch('sys.stdout', new_callable=StringIO)
    def test_cli_no_obsolete_kernels(self, mock_stdout, mock_run):
        """Test when system is clean with no obsolete kernels."""
        # Mock system responses - only running and latest kernel
        def mock_subprocess(cmd, **kwargs):
            if cmd[0] == "uname":
                return MagicMock(stdout="5.15.0-91-generic\n", returncode=0)
            elif cmd[0] == "dpkg":
                return MagicMock(
                    stdout="""ii  linux-image-5.15.0-91-generic   5.15.0-91.101 amd64
ii  linux-headers-5.15.0-91-generic  5.15.0-91.101 amd64
""",
                    returncode=0,
                )
        
        mock_run.side_effect = mock_subprocess
        
        # Run CLI
        exit_code = main(["--dry-run"])

        # Check results - exit code 1 means nothing to do
        self.assertEqual(exit_code, 1)
        output = mock_stdout.getvalue()
        
        # Verify clean system message
        self.assertIn("No obsolete", output)
        self.assertIn("clean", output.lower())
    
    @patch('kernsweep.detector.subprocess.run')
    @patch('sys.stdout', new_callable=StringIO)
    def test_cli_verbose_mode(self, mock_stdout, mock_run):
        """Test verbose output mode."""
        def mock_subprocess(cmd, **kwargs):
            if cmd[0] == "uname":
                return MagicMock(stdout="5.15.0-82-generic\n", returncode=0)
            elif cmd[0] == "dpkg":
                return MagicMock(
                    stdout="""ii  linux-image-5.15.0-82-generic   5.15.0-82.91  amd64
ii  linux-image-5.15.0-91-generic   5.15.0-91.101 amd64
""",
                    returncode=0,
                )
        
        mock_run.side_effect = mock_subprocess
        
        # Run CLI with --verbose
        exit_code = main(["--dry-run", "--verbose"])

        # Check results - exit code 1 means nothing to do
        self.assertEqual(exit_code, 1)
        output = mock_stdout.getvalue()
        
        # Verify verbose messages
        self.assertIn("Detecting running kernel", output)
        self.assertIn("Scanning installed kernels", output)
        self.assertIn("Analyzing kernels", output)
    
    @patch('kernsweep.detector.subprocess.run')
    @patch('sys.stdout', new_callable=StringIO)
    def test_cli_quiet_mode(self, mock_stdout, mock_run):
        """Test quiet output mode."""
        def mock_subprocess(cmd, **kwargs):
            if cmd[0] == "uname":
                return MagicMock(stdout="5.15.0-82-generic\n", returncode=0)
            elif cmd[0] == "dpkg":
                return MagicMock(
                    stdout="""ii  linux-image-5.15.0-82-generic   5.15.0-82.91  amd64
""",
                    returncode=0,
                )
        
        mock_run.side_effect = mock_subprocess
        
        # Run CLI with --quiet
        exit_code = main(["--dry-run", "--quiet"])

        # Check results - exit code 1 means nothing to do
        self.assertEqual(exit_code, 1)
        output = mock_stdout.getvalue()
        
        # Verify minimal output
        self.assertEqual(output.strip(), "")
    
    @patch('kernsweep.detector.subprocess.run')
    def test_cli_running_is_latest(self, mock_run):
        """Test when running kernel is the latest."""
        def mock_subprocess(cmd, **kwargs):
            if cmd[0] == "uname":
                return MagicMock(stdout="5.15.0-91-generic\n", returncode=0)
            elif cmd[0] == "dpkg":
                return MagicMock(
                    stdout="""ii  linux-image-5.15.0-75-generic   5.15.0-75.82  amd64
ii  linux-image-5.15.0-82-generic   5.15.0-82.91  amd64
ii  linux-image-5.15.0-91-generic   5.15.0-91.101 amd64
""",
                    returncode=0,
                )
        
        mock_run.side_effect = mock_subprocess
        
        # Run CLI
        exit_code = main(["--dry-run"])
        
        # Should succeed and identify 2 obsolete kernels
        self.assertEqual(exit_code, 0)
    
    @patch('kernsweep.cli.check_sudo')
    @patch('subprocess.run')
    @patch('sys.stdout', new_callable=StringIO)
    def test_cli_remove_without_sudo(self, mock_stdout, mock_run, mock_sudo):
        """Test --remove without sudo privileges."""
        mock_sudo.return_value = False
        
        def mock_subprocess(cmd, **kwargs):
            if cmd[0] == "uname":
                return MagicMock(stdout="5.15.0-82-generic\n", returncode=0)
            elif cmd[0] == "dpkg":
                return MagicMock(
                    stdout="""ii  linux-image-5.15.0-82-generic   5.15.0-82.91  amd64
ii  linux-image-5.15.0-91-generic   5.15.0-91.101 amd64
ii  linux-image-5.15.0-75-generic   5.15.0-75.82  amd64
""",
                    returncode=0,
                )
        
        mock_run.side_effect = mock_subprocess
        
        # Run CLI with --remove
        exit_code = main(["--remove"])

        # Should fail with permission error - exit code -1
        self.assertEqual(exit_code, -1)        # apt-get should not have been called (only uname and dpkg)
        calls = [str(call) for call in mock_run.call_args_list]
        self.assertNotIn("apt-get", str(calls))
    
    @patch('builtins.input')
    @patch('kernsweep.remover.check_sudo')
    @patch('kernsweep.cli.check_sudo')
    @patch('subprocess.run')
    @patch('sys.stdout', new_callable=StringIO)
    def test_cli_remove_with_confirmation_yes(self, mock_stdout, mock_run, mock_cli_sudo, mock_remover_sudo, mock_input):
        """Test --remove with user confirmation (yes)."""
        mock_cli_sudo.return_value = True
        mock_remover_sudo.return_value = True
        mock_input.return_value = "y"
        
        def mock_subprocess(cmd, **kwargs):
            if cmd[0] == "uname":
                return MagicMock(stdout="5.15.0-82-generic\n", returncode=0)
            elif cmd[0] == "dpkg":
                return MagicMock(
                    stdout="""ii  linux-image-5.15.0-82-generic   5.15.0-82.91  amd64
ii  linux-image-5.15.0-91-generic   5.15.0-91.101 amd64
ii  linux-image-5.15.0-75-generic   5.15.0-75.82  amd64
""",
                    returncode=0,
                )
            elif cmd[0] == "apt-get":
                return MagicMock(returncode=0, stdout="", stderr="")
        
        mock_run.side_effect = mock_subprocess
        
        # Run CLI with --remove
        exit_code = main(["--remove"])

        # Should succeed with exit code 2 (reboot required since running != latest)
        self.assertEqual(exit_code, 2)        # User should be prompted
        mock_input.assert_called_once()
        
        # apt-get should have been called
        calls = [str(call) for call in mock_run.call_args_list]
        self.assertIn("apt-get", str(calls))
    
    @patch('builtins.input')
    @patch('kernsweep.cli.check_sudo')
    @patch('subprocess.run')
    @patch('sys.stdout', new_callable=StringIO)
    def test_cli_remove_with_confirmation_no(self, mock_stdout, mock_run, mock_sudo, mock_input):
        """Test --remove with user confirmation (no/abort)."""
        mock_sudo.return_value = True
        mock_input.return_value = "n"
        
        def mock_subprocess(cmd, **kwargs):
            if cmd[0] == "uname":
                return MagicMock(stdout="5.15.0-82-generic\n", returncode=0)
            elif cmd[0] == "dpkg":
                return MagicMock(
                    stdout="""ii  linux-image-5.15.0-82-generic   5.15.0-82.91  amd64
ii  linux-image-5.15.0-91-generic   5.15.0-91.101 amd64
ii  linux-image-5.15.0-75-generic   5.15.0-75.82  amd64
""",
                    returncode=0,
                )
        
        mock_run.side_effect = mock_subprocess
        
        # Run CLI with --remove
        exit_code = main(["--remove"])
        
        # Should succeed (user aborted)
        self.assertEqual(exit_code, 0)
        
        # User should be prompted
        mock_input.assert_called_once()
        
        # apt-get should NOT have been called (only uname and dpkg)
        calls = [str(call) for call in mock_run.call_args_list]
        self.assertNotIn("apt-get", str(calls))
        
        # Check for "Aborted" message
        output = mock_stdout.getvalue()
        self.assertIn("Aborted", output)
    
    @patch('kernsweep.remover.check_sudo')
    @patch('kernsweep.cli.check_sudo')
    @patch('subprocess.run')
    @patch('sys.stdout', new_callable=StringIO)
    def test_cli_remove_with_yes_flag(self, mock_stdout, mock_run, mock_cli_sudo, mock_remover_sudo):
        """Test --remove --yes (no confirmation prompt)."""
        mock_cli_sudo.return_value = True
        mock_remover_sudo.return_value = True
        
        def mock_subprocess(cmd, **kwargs):
            if cmd[0] == "uname":
                return MagicMock(stdout="5.15.0-82-generic\n", returncode=0)
            elif cmd[0] == "dpkg":
                return MagicMock(
                    stdout="""ii  linux-image-5.15.0-82-generic   5.15.0-82.91  amd64
ii  linux-image-5.15.0-91-generic   5.15.0-91.101 amd64
ii  linux-image-5.15.0-75-generic   5.15.0-75.82  amd64
ii  linux-headers-5.15.0-75-generic  5.15.0-75.82  amd64
""",
                    returncode=0,
                )
            elif cmd[0] == "apt-get":
                return MagicMock(returncode=0, stdout="", stderr="")
        
        mock_run.side_effect = mock_subprocess
        
        # Run CLI with --remove --yes
        exit_code = main(["--remove", "--yes"])

        # Should succeed with exit code 2 (reboot required)
        self.assertEqual(exit_code, 2)        # apt-get should have been called with -y flag
        apt_calls = [call for call in mock_run.call_args_list if call[0][0][0] == "apt-get"]
        self.assertEqual(len(apt_calls), 1)
        call_args = apt_calls[0][0][0]
        self.assertIn("-y", call_args)
        self.assertIn("linux-image-5.15.0-75-generic", call_args)
        self.assertIn("linux-headers-5.15.0-75-generic", call_args)


if __name__ == '__main__':
    unittest.main()
