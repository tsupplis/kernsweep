"""
Unit tests for safety validation functions.
"""

import unittest
from kernsweep.analyzer import validate_removal_safety, get_protected_packages
from kernsweep.detector import KernelInfo


class TestValidateRemovalSafety(unittest.TestCase):
    """Test safety validation logic."""
    
    def setUp(self):
        """Set up test kernels."""
        self.all_kernels = [
            KernelInfo("5.15.0-91-generic", "linux-image-5.15.0-91-generic", True, False),
            KernelInfo("5.15.0-89-generic", "linux-image-5.15.0-89-generic", False, False),
            KernelInfo("5.15.0-87-generic", "linux-image-5.15.0-87-generic", False, False),
            KernelInfo("5.15.0-82-generic", "linux-image-5.15.0-82-generic", False, False),
        ]
        self.running_kernel = "5.15.0-91-generic"
        self.latest_kernel = "5.15.0-91-generic"
    
    def test_safe_removal(self):
        """Test that safe removal passes validation."""
        packages_to_remove = [
            "linux-image-5.15.0-89-generic",
            "linux-image-5.15.0-87-generic",
        ]
        
        is_safe, error_msg = validate_removal_safety(
            packages_to_remove,
            self.running_kernel,
            self.latest_kernel,
            self.all_kernels
        )
        
        self.assertTrue(is_safe)
        self.assertEqual(error_msg, "")
    
    def test_running_kernel_protection(self):
        """Test that running kernel cannot be removed."""
        packages_to_remove = [
            "linux-image-5.15.0-91-generic",  # Running kernel
            "linux-image-5.15.0-89-generic",
        ]
        
        is_safe, error_msg = validate_removal_safety(
            packages_to_remove,
            self.running_kernel,
            self.latest_kernel,
            self.all_kernels
        )
        
        self.assertFalse(is_safe)
        self.assertIn("Running kernel", error_msg)
        self.assertIn("5.15.0-91-generic", error_msg)
    
    def test_latest_kernel_protection(self):
        """Test that latest kernel cannot be removed."""
        # Make running != latest
        all_kernels = [
            KernelInfo("5.15.0-95-generic", "linux-image-5.15.0-95-generic", False, True),
            KernelInfo("5.15.0-91-generic", "linux-image-5.15.0-91-generic", True, False),
            KernelInfo("5.15.0-89-generic", "linux-image-5.15.0-89-generic", False, False),
        ]
        
        packages_to_remove = [
            "linux-image-5.15.0-95-generic",  # Latest kernel
        ]
        
        is_safe, error_msg = validate_removal_safety(
            packages_to_remove,
            "5.15.0-91-generic",
            "5.15.0-95-generic",
            all_kernels
        )
        
        self.assertFalse(is_safe)
        self.assertIn("Latest kernel", error_msg)
        self.assertIn("5.15.0-95-generic", error_msg)
    
    def test_minimum_kernel_protection(self):
        """Test that at least one kernel must remain."""
        # Only two kernels, both protected
        all_kernels = [
            KernelInfo("5.15.0-91-generic", "linux-image-5.15.0-91-generic", True, True),
            KernelInfo("5.15.0-89-generic", "linux-image-5.15.0-89-generic", False, False),
        ]
        
        # Try to remove the non-protected one (would leave only protected)
        packages_to_remove = [
            "linux-image-5.15.0-89-generic",
        ]
        
        # This should actually pass - we're left with 1 kernel
        is_safe, error_msg = validate_removal_safety(
            packages_to_remove,
            "5.15.0-91-generic",
            "5.15.0-91-generic",
            all_kernels
        )
        
        self.assertTrue(is_safe)
    
    def test_no_kernels_remaining(self):
        """Test that removal fails if no kernels would remain."""
        # Only one kernel
        all_kernels = [
            KernelInfo("5.15.0-91-generic", "linux-image-5.15.0-91-generic", True, True),
        ]
        
        # Try to remove it (shouldn't be possible but let's test the check)
        packages_to_remove = [
            "linux-image-5.15.0-91-generic",
        ]
        
        is_safe, error_msg = validate_removal_safety(
            packages_to_remove,
            "5.15.0-91-generic",
            "5.15.0-91-generic",
            all_kernels
        )
        
        # Should fail on running kernel check first
        self.assertFalse(is_safe)
        self.assertIn("Running kernel", error_msg)
    
    def test_bulk_removal_warning(self):
        """Test that removing many kernels triggers warning."""
        # Create 8 kernels
        all_kernels = [
            KernelInfo(f"5.15.0-{90+i}-generic", f"linux-image-5.15.0-{90+i}-generic", 
                      i == 7, i == 7)
            for i in range(8)
        ]
        
        # Try to remove 6 of them
        packages_to_remove = [
            f"linux-image-5.15.0-{90+i}-generic" for i in range(6)
        ]
        
        is_safe, error_msg = validate_removal_safety(
            packages_to_remove,
            "5.15.0-97-generic",
            "5.15.0-97-generic",
            all_kernels
        )
        
        self.assertFalse(is_safe)
        self.assertIn("6 kernels", error_msg)
        self.assertIn("excessive", error_msg)
    
    def test_headers_in_removal_list(self):
        """Test that headers don't interfere with safety checks."""
        packages_to_remove = [
            "linux-image-5.15.0-89-generic",
            "linux-headers-5.15.0-89-generic",
            "linux-image-5.15.0-87-generic",
            "linux-headers-5.15.0-87-generic",
        ]
        
        is_safe, error_msg = validate_removal_safety(
            packages_to_remove,
            self.running_kernel,
            self.latest_kernel,
            self.all_kernels
        )
        
        # Should be safe - only 2 kernel images being removed, not excessive
        self.assertTrue(is_safe)
        self.assertEqual(error_msg, "")


class TestGetProtectedPackages(unittest.TestCase):
    """Test protected package identification."""
    
    def test_same_kernel_running_and_latest(self):
        """Test when running kernel is also latest."""
        protected = get_protected_packages(
            "5.15.0-91-generic",
            "5.15.0-91-generic"
        )
        
        expected = {
            "linux-image-5.15.0-91-generic",
            "linux-headers-5.15.0-91-generic",
        }
        
        self.assertEqual(protected, expected)
    
    def test_different_kernels(self):
        """Test when running and latest are different."""
        protected = get_protected_packages(
            "5.15.0-89-generic",
            "5.15.0-91-generic"
        )
        
        expected = {
            "linux-image-5.15.0-89-generic",
            "linux-headers-5.15.0-89-generic",
            "linux-image-5.15.0-91-generic",
            "linux-headers-5.15.0-91-generic",
        }
        
        self.assertEqual(protected, expected)
    
    def test_lowlatency_kernel(self):
        """Test with lowlatency kernel variant."""
        protected = get_protected_packages(
            "5.15.0-91-lowlatency",
            "5.15.0-91-generic"
        )
        
        expected = {
            "linux-image-5.15.0-91-lowlatency",
            "linux-headers-5.15.0-91-lowlatency",
            "linux-image-5.15.0-91-generic",
            "linux-headers-5.15.0-91-generic",
        }
        
        self.assertEqual(protected, expected)


if __name__ == "__main__":
    unittest.main()
