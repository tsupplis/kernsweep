"""
Unit tests for the detector module.

Tests kernel and header detection functionality with mocked system calls.
"""

import unittest
from unittest.mock import patch, MagicMock
import subprocess

from kernsweep.detector import (
    get_running_kernel,
    get_installed_kernels,
    get_installed_headers,
    KernelInfo,
)


class TestGetRunningKernel(unittest.TestCase):
    """Tests for get_running_kernel function."""
    
    @patch('kernsweep.detector.subprocess.run')
    def test_get_running_kernel_success(self, mock_run):
        """Test successful kernel detection."""
        mock_run.return_value = MagicMock(
            stdout="5.15.0-82-generic\n",
            returncode=0,
        )
        
        result = get_running_kernel()
        
        self.assertEqual(result, "5.15.0-82-generic")
        mock_run.assert_called_once_with(
            ["uname", "-r"],
            capture_output=True,
            text=True,
            check=True,
        )
    
    @patch('kernsweep.detector.subprocess.run')
    def test_get_running_kernel_empty_output(self, mock_run):
        """Test handling of empty uname output."""
        mock_run.return_value = MagicMock(
            stdout="",
            returncode=0,
        )
        
        with self.assertRaises(RuntimeError) as ctx:
            get_running_kernel()
        
        self.assertIn("empty", str(ctx.exception).lower())
    
    @patch('kernsweep.detector.subprocess.run')
    def test_get_running_kernel_command_failure(self, mock_run):
        """Test handling of command execution failure."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "uname")
        
        with self.assertRaises(RuntimeError) as ctx:
            get_running_kernel()
        
        self.assertIn("Failed to detect", str(ctx.exception))


class TestGetInstalledKernels(unittest.TestCase):
    """Tests for get_installed_kernels function."""
    
    @patch('kernsweep.detector.subprocess.run')
    def test_get_installed_kernels_success(self, mock_run):
        """Test successful kernel package detection."""
        mock_run.return_value = MagicMock(
            stdout="""ii  linux-image-5.15.0-82-generic   5.15.0-82.91  amd64
ii  linux-image-5.15.0-91-generic   5.15.0-91.101 amd64
ii  linux-image-generic             5.15.0.91.89  amd64
ii  some-other-package              1.0.0         amd64
""",
            returncode=0,
        )
        
        result = get_installed_kernels()
        
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], KernelInfo)
        
        versions = {k.version for k in result}
        self.assertIn("5.15.0-82-generic", versions)
        self.assertIn("5.15.0-91-generic", versions)
        
        packages = {k.package_name for k in result}
        self.assertIn("linux-image-5.15.0-82-generic", packages)
        self.assertIn("linux-image-5.15.0-91-generic", packages)
    
    @patch('kernsweep.detector.subprocess.run')
    def test_get_installed_kernels_no_kernels(self, mock_run):
        """Test handling when no kernel packages found (container/LXC)."""
        mock_run.return_value = MagicMock(
            stdout="ii  some-other-package  1.0.0  amd64\n",
            returncode=0,
        )
        
        # Should return empty list, not raise error (container environment)
        result = get_installed_kernels()
        
        self.assertEqual(len(result), 0)
    
    @patch('kernsweep.detector.subprocess.run')
    def test_get_installed_kernels_filters_metapackages(self, mock_run):
        """Test that meta-packages without versions are filtered out."""
        mock_run.return_value = MagicMock(
            stdout="""ii  linux-image-5.15.0-82-generic   5.15.0-82.91  amd64
ii  linux-image-generic             5.15.0.91.89  amd64
ii  linux-image-lowlatency          5.15.0.91.89  amd64
""",
            returncode=0,
        )
        
        result = get_installed_kernels()
        
        # Should only get the versioned package, not the meta-packages
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].version, "5.15.0-82-generic")


class TestGetInstalledHeaders(unittest.TestCase):
    """Tests for get_installed_headers function."""
    
    @patch('kernsweep.detector.subprocess.run')
    def test_get_installed_headers_success(self, mock_run):
        """Test successful header package detection."""
        mock_run.return_value = MagicMock(
            stdout="""ii  linux-headers-5.15.0-82-generic   5.15.0-82.91  amd64
ii  linux-headers-5.15.0-91-generic   5.15.0-91.101 amd64
ii  linux-headers-generic             5.15.0.91.89  amd64
""",
            returncode=0,
        )
        
        result = get_installed_headers()
        
        self.assertEqual(len(result), 2)
        self.assertIn("linux-headers-5.15.0-82-generic", result)
        self.assertIn("linux-headers-5.15.0-91-generic", result)
    
    @patch('kernsweep.detector.subprocess.run')
    def test_get_installed_headers_empty(self, mock_run):
        """Test when no header packages are installed."""
        mock_run.return_value = MagicMock(
            stdout="ii  some-other-package  1.0.0  amd64\n",
            returncode=0,
        )
        
        result = get_installed_headers()
        
        self.assertEqual(len(result), 0)
    
    @patch('kernsweep.detector.subprocess.run')
    def test_get_installed_headers_filters_metapackages(self, mock_run):
        """Test that header meta-packages are filtered out."""
        mock_run.return_value = MagicMock(
            stdout="""ii  linux-headers-5.15.0-82-generic   5.15.0-82.91  amd64
ii  linux-headers-generic             5.15.0.91.89  amd64
""",
            returncode=0,
        )
        
        result = get_installed_headers()
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], "linux-headers-5.15.0-82-generic")
    
    @patch('kernsweep.detector.subprocess.run')
    def test_get_installed_headers_malformed_output(self, mock_run):
        """Test handling of malformed dpkg output."""
        mock_run.return_value = MagicMock(
            stdout="""broken line without proper format
ii linux-headers-incomplete
ii  linux-headers-5.15.0-82-generic   5.15.0-82.91  amd64
malformed entry
""",
            returncode=0,
        )
        
        result = get_installed_headers()
        
        # Should still parse the valid line
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], "linux-headers-5.15.0-82-generic")


class TestGetInstalledKernelsEdgeCases(unittest.TestCase):
    """Additional edge case tests for kernel detection."""
    
    @patch('kernsweep.detector.subprocess.run')
    def test_get_installed_kernels_very_long_package_name(self, mock_run):
        """Test with very long package names."""
        long_suffix = "a" * 100
        mock_run.return_value = MagicMock(
            stdout=f"ii  linux-image-5.15.0-82-{long_suffix}   5.15.0-82.91  amd64\n",
            returncode=0,
        )
        
        result = get_installed_kernels()
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].version, f"5.15.0-82-{long_suffix}")
    
    @patch('kernsweep.detector.subprocess.run')
    def test_get_installed_kernels_mixed_architectures(self, mock_run):
        """Test with multiple architectures (should only get amd64)."""
        mock_run.return_value = MagicMock(
            stdout="""ii  linux-image-5.15.0-82-generic   5.15.0-82.91  amd64
ii  linux-image-5.15.0-82-generic   5.15.0-82.91  i386
ii  linux-image-5.15.0-91-generic   5.15.0-91.101 amd64
""",
            returncode=0,
        )
        
        result = get_installed_kernels()
        
        # Should detect both, dpkg returns installed packages
        self.assertGreaterEqual(len(result), 2)
    
    @patch('kernsweep.detector.subprocess.run')
    def test_get_installed_kernels_with_whitespace_variations(self, mock_run):
        """Test with various whitespace patterns."""
        mock_run.return_value = MagicMock(
            stdout="""ii  linux-image-5.15.0-82-generic    5.15.0-82.91   amd64
ii   linux-image-5.15.0-91-generic  5.15.0-91.101  amd64
""",
            returncode=0,
        )
        
        result = get_installed_kernels()
        
        self.assertEqual(len(result), 2)


if __name__ == '__main__':
    unittest.main()
