"""
Unit tests for the remover module.

Tests package removal functionality with mocked apt commands.
"""

import unittest
from unittest.mock import patch, MagicMock
import subprocess

from kernsweep.remover import (
    check_sudo,
    generate_apt_command,
    remove_packages,
    RemovalStatus,
)


class TestCheckSudo(unittest.TestCase):
    """Tests for check_sudo function."""
    
    @patch('kernsweep.remover.os.geteuid')
    def test_check_sudo_as_root(self, mock_geteuid):
        """Test sudo check when running as root."""
        mock_geteuid.return_value = 0
        
        result = check_sudo()
        
        self.assertTrue(result)
    
    @patch('kernsweep.remover.os.geteuid')
    def test_check_sudo_as_user(self, mock_geteuid):
        """Test sudo check when running as normal user."""
        mock_geteuid.return_value = 1000
        
        result = check_sudo()
        
        self.assertFalse(result)
    
    @patch('kernsweep.remover.os.geteuid')
    def test_check_sudo_attribute_error(self, mock_geteuid):
        """Test sudo check on systems without geteuid (Windows)."""
        mock_geteuid.side_effect = AttributeError()
        
        result = check_sudo()
        
        self.assertFalse(result)


class TestGenerateAptCommand(unittest.TestCase):
    """Tests for generate_apt_command function."""
    
    def test_generate_apt_command_basic(self):
        """Test basic apt command generation."""
        packages = ["linux-image-5.15.0-75-generic", "linux-headers-5.15.0-75-generic"]
        
        result = generate_apt_command(packages)
        
        self.assertEqual(result[0], "apt-get")
        self.assertEqual(result[1], "-y")
        self.assertEqual(result[2], "remove")
        self.assertEqual(result[3], "--autoremove")
        self.assertEqual(result[4], "--purge")
        self.assertIn("linux-image-5.15.0-75-generic", result)
        self.assertIn("linux-headers-5.15.0-75-generic", result)
    
    def test_generate_apt_command_empty_packages(self):
        """Test error handling with empty package list."""
        with self.assertRaises(ValueError) as ctx:
            generate_apt_command([])
        
        self.assertIn("No packages", str(ctx.exception))
    
    def test_generate_apt_command_single_package(self):
        """Test command generation with single package."""
        result = generate_apt_command(["test-package"])
        
        # apt-get -y remove --autoremove --purge test-package
        self.assertEqual(len(result), 6)
        self.assertEqual(result[-1], "test-package")
        self.assertEqual(result[1], "-y")
        self.assertEqual(result[2], "remove")
        self.assertEqual(result[3], "--autoremove")
        self.assertEqual(result[4], "--purge")


class TestRemovePackages(unittest.TestCase):
    """Tests for remove_packages function."""
    
    @patch('kernsweep.remover.check_sudo')
    def test_remove_packages_dry_run(self, mock_sudo):
        """Test dry-run mode (no actual removal)."""
        packages = ["linux-image-5.15.0-75-generic", "linux-headers-5.15.0-75-generic"]
        
        results = remove_packages(packages, dry_run=True)
        
        # Dry run should not check sudo
        mock_sudo.assert_not_called()
        
        # All packages should succeed in dry run
        self.assertEqual(len(results), 2)
        for pkg, status in results:
            self.assertEqual(status, RemovalStatus.SUCCESS)
    
    @patch('kernsweep.remover.check_sudo')
    def test_remove_packages_no_sudo(self, mock_sudo):
        """Test error when running without sudo."""
        mock_sudo.return_value = False
        packages = ["linux-image-5.15.0-75-generic"]
        
        with self.assertRaises(PermissionError) as ctx:
            remove_packages(packages, dry_run=False)
        
        self.assertIn("Root privileges required", str(ctx.exception))
    
    @patch('kernsweep.remover.subprocess.run')
    @patch('kernsweep.remover.check_sudo')
    def test_remove_packages_success(self, mock_sudo, mock_run):
        """Test successful package removal."""
        mock_sudo.return_value = True
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Packages removed successfully\n",
            stderr="",
        )
        
        packages = ["linux-image-5.15.0-75-generic"]
        results = remove_packages(packages, dry_run=False)
        
        # Check apt-get was called
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        self.assertEqual(call_args[0], "apt-get")
        self.assertEqual(call_args[1], "-y")
        self.assertEqual(call_args[2], "remove")
        self.assertEqual(call_args[3], "--autoremove")
        self.assertEqual(call_args[4], "--purge")
        self.assertIn("linux-image-5.15.0-75-generic", call_args)
        
        # Check results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], "linux-image-5.15.0-75-generic")
        self.assertEqual(results[0][1], RemovalStatus.SUCCESS)
    
    @patch('kernsweep.remover.subprocess.run')
    @patch('kernsweep.remover.check_sudo')
    def test_remove_packages_apt_failure(self, mock_sudo, mock_run):
        """Test handling of apt command failure."""
        mock_sudo.return_value = True
        mock_run.return_value = MagicMock(
            returncode=100,
            stdout="",
            stderr="E: Unable to locate package\n",
        )
        
        packages = ["nonexistent-package"]
        
        with self.assertRaises(RuntimeError) as ctx:
            remove_packages(packages, dry_run=False)
        
        self.assertIn("apt-get remove failed", str(ctx.exception))
        self.assertIn("100", str(ctx.exception))
    
    @patch('kernsweep.remover.subprocess.run')
    @patch('kernsweep.remover.check_sudo')
    def test_remove_packages_subprocess_error(self, mock_sudo, mock_run):
        """Test handling of subprocess execution error."""
        mock_sudo.return_value = True
        mock_run.side_effect = subprocess.SubprocessError("Command not found")
        
        packages = ["linux-image-5.15.0-75-generic"]
        
        with self.assertRaises(RuntimeError) as ctx:
            remove_packages(packages, dry_run=False)
        
        self.assertIn("Failed to execute apt-get", str(ctx.exception))
    
    def test_remove_packages_empty_list(self):
        """Test removal with empty package list."""
        results = remove_packages([], dry_run=True)
        
        self.assertEqual(len(results), 0)
    
    @patch('kernsweep.remover.subprocess.run')
    @patch('kernsweep.remover.check_sudo')
    def test_remove_packages_multiple(self, mock_sudo, mock_run):
        """Test removal of multiple packages."""
        mock_sudo.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        packages = [
            "linux-image-5.15.0-75-generic",
            "linux-image-5.15.0-70-generic",
            "linux-headers-5.15.0-75-generic",
        ]
        results = remove_packages(packages, dry_run=False)
        
        # All packages should be in single apt command
        call_args = mock_run.call_args[0][0]
        for pkg in packages:
            self.assertIn(pkg, call_args)
        
        # Check results
        self.assertEqual(len(results), 3)
        for _, status in results:
            self.assertEqual(status, RemovalStatus.SUCCESS)


if __name__ == '__main__':
    unittest.main()
