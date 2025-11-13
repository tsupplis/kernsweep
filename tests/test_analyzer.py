"""
Unit tests for the analyzer module.

Tests kernel version comparison and analysis logic.
"""

import unittest

from kernsweep.analyzer import (
    compare_kernel_versions,
    analyze_kernels,
    match_headers_to_kernels,
    AnalysisResult,
)
from kernsweep.detector import KernelInfo


class TestCompareKernelVersions(unittest.TestCase):
    """Tests for compare_kernel_versions function."""
    
    def test_compare_equal_versions(self):
        """Test comparison of equal versions."""
        result = compare_kernel_versions("5.15.0-82-generic", "5.15.0-82-generic")
        self.assertEqual(result, 0)
    
    def test_compare_different_build_numbers(self):
        """Test comparison of versions with different build numbers."""
        result = compare_kernel_versions("5.15.0-82-generic", "5.15.0-91-generic")
        self.assertEqual(result, -1)
        
        result = compare_kernel_versions("5.15.0-91-generic", "5.15.0-82-generic")
        self.assertEqual(result, 1)
    
    def test_compare_different_patch_versions(self):
        """Test comparison of versions with different patch levels."""
        result = compare_kernel_versions("5.15.1-82-generic", "5.15.0-82-generic")
        self.assertEqual(result, 1)
        
        result = compare_kernel_versions("5.15.0-82-generic", "5.15.1-82-generic")
        self.assertEqual(result, -1)
    
    def test_compare_different_minor_versions(self):
        """Test comparison of versions with different minor versions."""
        result = compare_kernel_versions("5.14.0-82-generic", "5.15.0-82-generic")
        self.assertEqual(result, -1)
        
        result = compare_kernel_versions("5.16.0-82-generic", "5.15.0-82-generic")
        self.assertEqual(result, 1)
    
    def test_compare_different_major_versions(self):
        """Test comparison of versions with different major versions."""
        result = compare_kernel_versions("4.15.0-82-generic", "5.15.0-82-generic")
        self.assertEqual(result, -1)
        
        result = compare_kernel_versions("6.15.0-82-generic", "5.15.0-82-generic")
        self.assertEqual(result, 1)
    
    def test_compare_lowlatency_vs_generic(self):
        """Test comparison with different kernel flavors."""
        result = compare_kernel_versions("5.15.0-82-lowlatency", "5.15.0-82-generic")
        # Should compare numerically and be equal
        self.assertEqual(result, 0)
    
    def test_compare_invalid_format_fallback(self):
        """Test fallback to string comparison for invalid formats."""
        result = compare_kernel_versions("custom-kernel-a", "custom-kernel-b")
        self.assertEqual(result, -1)
    
    def test_compare_very_long_version_string(self):
        """Test comparison with very long version strings."""
        result = compare_kernel_versions(
            "5.15.0-82-generic-with-very-long-suffix-abcdefghijklmnopqrstuvwxyz",
            "5.15.0-91-generic-with-very-long-suffix-abcdefghijklmnopqrstuvwxyz"
        )
        self.assertEqual(result, -1)  # 82 < 91
    
    def test_compare_missing_build_number(self):
        """Test comparison when build number is missing."""
        result = compare_kernel_versions("5.15.0-generic", "5.15.0-82-generic")
        # Should fall back to string comparison
        self.assertIsInstance(result, int)
    
    def test_compare_three_digit_major_version(self):
        """Test comparison with three-digit major version."""
        result = compare_kernel_versions("100.15.0-82-generic", "5.15.0-82-generic")
        self.assertEqual(result, 1)  # 100 > 5
    
    def test_compare_pve_kernel_format(self):
        """Test comparison with Proxmox VE kernel format."""
        result = compare_kernel_versions("6.8.12-1-pve", "6.8.12-2-pve")
        self.assertEqual(result, -1)  # 1 < 2
    
    def test_compare_debian_cloud_kernel(self):
        """Test comparison with Debian cloud kernel format."""
        result = compare_kernel_versions("5.10.0-21-cloud-amd64", "5.10.0-23-cloud-amd64")
        self.assertEqual(result, -1)
    
    def test_compare_zero_versions(self):
        """Test comparison with zero in version components."""
        result = compare_kernel_versions("0.0.0-1-generic", "0.0.0-2-generic")
        self.assertEqual(result, -1)


class TestAnalyzeKernels(unittest.TestCase):
    """Tests for analyze_kernels function."""
    
    def test_analyze_kernels_basic(self):
        """Test basic kernel analysis with running and latest different."""
        kernels = [
            KernelInfo("5.15.0-82-generic", "linux-image-5.15.0-82-generic", is_running=True),
            KernelInfo("5.15.0-91-generic", "linux-image-5.15.0-91-generic"),
            KernelInfo("5.15.0-75-generic", "linux-image-5.15.0-75-generic"),
        ]
        
        result = analyze_kernels(kernels)
        
        self.assertEqual(result.running_kernel, "5.15.0-82-generic")
        self.assertEqual(result.latest_kernel, "5.15.0-91-generic")
        self.assertEqual(len(result.obsolete_kernels), 1)
        self.assertIn("linux-image-5.15.0-75-generic", result.obsolete_kernels)
        self.assertEqual(len(result.protected_kernels), 2)
    
    def test_analyze_kernels_running_is_latest(self):
        """Test when running kernel is also the latest."""
        kernels = [
            KernelInfo("5.15.0-91-generic", "linux-image-5.15.0-91-generic", is_running=True),
            KernelInfo("5.15.0-82-generic", "linux-image-5.15.0-82-generic"),
            KernelInfo("5.15.0-75-generic", "linux-image-5.15.0-75-generic"),
        ]
        
        result = analyze_kernels(kernels)
        
        self.assertEqual(result.running_kernel, "5.15.0-91-generic")
        self.assertEqual(result.latest_kernel, "5.15.0-91-generic")
        self.assertEqual(len(result.obsolete_kernels), 2)
        self.assertEqual(len(result.protected_kernels), 1)
    
    def test_analyze_kernels_only_two_kernels(self):
        """Test with only running and one other kernel."""
        kernels = [
            KernelInfo("5.15.0-82-generic", "linux-image-5.15.0-82-generic", is_running=True),
            KernelInfo("5.15.0-91-generic", "linux-image-5.15.0-91-generic"),
        ]
        
        result = analyze_kernels(kernels)
        
        self.assertEqual(len(result.obsolete_kernels), 0)
        self.assertEqual(len(result.protected_kernels), 2)
    
    def test_analyze_kernels_no_running_kernel(self):
        """Test error handling when no running kernel is marked."""
        kernels = [
            KernelInfo("5.15.0-82-generic", "linux-image-5.15.0-82-generic"),
            KernelInfo("5.15.0-91-generic", "linux-image-5.15.0-91-generic"),
        ]
        
        with self.assertRaises(ValueError) as ctx:
            analyze_kernels(kernels)
        
        self.assertIn("Running kernel not found", str(ctx.exception))
    
    def test_analyze_kernels_empty_list(self):
        """Test handling of empty kernel list (e.g., container environment)."""
        result = analyze_kernels([])
        
        # Should return empty result, not raise an error
        self.assertEqual(result.running_kernel, "")
        self.assertEqual(result.latest_kernel, "")
        self.assertEqual(len(result.obsolete_kernels), 0)
        self.assertEqual(len(result.protected_kernels), 0)
    
    def test_analyze_kernels_all_same_version(self):
        """Test when all kernels have the same version (edge case)."""
        kernels = [
            KernelInfo("5.15.0-82-generic", "linux-image-5.15.0-82-generic", is_running=True),
            KernelInfo("5.15.0-82-generic", "linux-image-5.15.0-82-generic-alt"),
        ]
        
        result = analyze_kernels(kernels)
        
        # Both should be protected (running and latest are the same)
        self.assertEqual(result.running_kernel, "5.15.0-82-generic")
        self.assertEqual(result.latest_kernel, "5.15.0-82-generic")
    
    def test_analyze_kernels_many_obsolete(self):
        """Test with many obsolete kernels - should fail due to bulk removal protection."""
        kernels = [
            KernelInfo("5.15.0-100-generic", "linux-image-5.15.0-100-generic", is_running=True),
        ] + [
            KernelInfo(f"5.15.0-{i}-generic", f"linux-image-5.15.0-{i}-generic")
            for i in range(50, 60)
        ]
        
        # Should raise ValueError due to bulk removal warning (>5 kernels)
        with self.assertRaises(ValueError) as ctx:
            analyze_kernels(kernels)
        
        self.assertIn("10 kernels", str(ctx.exception))
        self.assertIn("excessive", str(ctx.exception))
    
    def test_analyze_kernels_single_kernel_only(self):
        """Test with only one kernel (running and latest)."""
        kernels = [
            KernelInfo("5.15.0-82-generic", "linux-image-5.15.0-82-generic", is_running=True),
        ]
        
        result = analyze_kernels(kernels)
        
        self.assertEqual(result.running_kernel, "5.15.0-82-generic")
        self.assertEqual(result.latest_kernel, "5.15.0-82-generic")
        self.assertEqual(len(result.obsolete_kernels), 0)


class TestMatchHeadersToKernels(unittest.TestCase):
    """Tests for match_headers_to_kernels function."""
    
    def test_match_headers_all_matched(self):
        """Test when all headers match protected kernels."""
        headers = [
            "linux-headers-5.15.0-82-generic",
            "linux-headers-5.15.0-91-generic",
        ]
        kernel_versions = {"5.15.0-82-generic", "5.15.0-91-generic"}
        
        result = match_headers_to_kernels(headers, kernel_versions)
        
        self.assertEqual(len(result), 0)
    
    def test_match_headers_some_obsolete(self):
        """Test when some headers are orphaned."""
        headers = [
            "linux-headers-5.15.0-82-generic",
            "linux-headers-5.15.0-91-generic",
            "linux-headers-5.15.0-75-generic",
        ]
        kernel_versions = {"5.15.0-82-generic", "5.15.0-91-generic"}
        
        result = match_headers_to_kernels(headers, kernel_versions)
        
        self.assertEqual(len(result), 1)
        self.assertIn("linux-headers-5.15.0-75-generic", result)
    
    def test_match_headers_all_obsolete(self):
        """Test when all headers are orphaned."""
        headers = [
            "linux-headers-5.15.0-75-generic",
            "linux-headers-5.15.0-70-generic",
        ]
        kernel_versions = {"5.15.0-82-generic", "5.15.0-91-generic"}
        
        result = match_headers_to_kernels(headers, kernel_versions)
        
        self.assertEqual(len(result), 2)
    
    def test_match_headers_empty_headers(self):
        """Test with no headers installed."""
        result = match_headers_to_kernels([], {"5.15.0-82-generic"})
        
        self.assertEqual(len(result), 0)
    
    def test_match_headers_different_flavors(self):
        """Test matching with different kernel flavors."""
        headers = [
            "linux-headers-5.15.0-82-generic",
            "linux-headers-5.15.0-82-lowlatency",
        ]
        kernel_versions = {"5.15.0-82-generic"}
        
        result = match_headers_to_kernels(headers, kernel_versions)
        
        # lowlatency headers should be marked obsolete
        self.assertEqual(len(result), 1)
        self.assertIn("linux-headers-5.15.0-82-lowlatency", result)
    
    def test_match_headers_common_packages(self):
        """Test that -common header packages are matched correctly against base version."""
        headers = [
            "linux-headers-6.12.48+deb13-amd64",
            "linux-headers-6.12.48+deb13-common",
            "linux-headers-6.12.41+deb13-amd64",
            "linux-headers-6.12.41+deb13-common",
        ]
        kernel_versions = {"6.12.48+deb13-amd64"}
        
        result = match_headers_to_kernels(headers, kernel_versions)
        
        # Should keep both 6.12.48 packages (amd64 and common), mark 6.12.41 as obsolete
        self.assertEqual(len(result), 2)
        self.assertIn("linux-headers-6.12.41+deb13-amd64", result)
        self.assertIn("linux-headers-6.12.41+deb13-common", result)
        self.assertNotIn("linux-headers-6.12.48+deb13-amd64", result)
        self.assertNotIn("linux-headers-6.12.48+deb13-common", result)


if __name__ == '__main__':
    unittest.main()
