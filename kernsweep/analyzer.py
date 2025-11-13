"""
Kernel analysis module.

Provides functionality to analyze installed kernels and determine
which ones are obsolete and safe to remove.
"""

import re
from typing import List, Set, Tuple
from dataclasses import dataclass

from .detector import KernelInfo


@dataclass
class AnalysisResult:
    """
    Result of kernel analysis.
    
    Attributes:
        running_kernel: Version of the currently running kernel
        latest_kernel: Version of the latest installed kernel
        obsolete_kernels: List of kernel packages safe to remove
        obsolete_headers: List of header packages safe to remove
        protected_kernels: List of kernels that must be kept
    """
    running_kernel: str
    latest_kernel: str
    obsolete_kernels: List[str]
    obsolete_headers: List[str]
    protected_kernels: List[str]


def compare_kernel_versions(version1: str, version2: str) -> int:
    """
    Compare two kernel version strings.
    
    Parses version strings like '5.15.0-82-generic' and compares them
    numerically component by component.
    
    Args:
        version1: First kernel version (e.g., '5.15.0-82-generic')
        version2: Second kernel version (e.g., '5.15.0-91-generic')
        
    Returns:
        int: -1 if version1 < version2, 0 if equal, 1 if version1 > version2
    """
    # Extract numeric components from version strings
    # Pattern: major.minor.patch-build
    pattern = r'^(\d+)\.(\d+)\.(\d+)-(\d+)'
    
    match1 = re.match(pattern, version1)
    match2 = re.match(pattern, version2)
    
    if not match1 or not match2:
        # Fallback to string comparison if format doesn't match
        if version1 < version2:
            return -1
        elif version1 > version2:
            return 1
        else:
            return 0
    
    # Extract components as integers
    v1_parts = [int(match1.group(i)) for i in range(1, 5)]
    v2_parts = [int(match2.group(i)) for i in range(1, 5)]
    
    # Compare component by component
    for v1, v2 in zip(v1_parts, v2_parts):
        if v1 < v2:
            return -1
        elif v1 > v2:
            return 1
    
    return 0


def analyze_kernels(kernels: List[KernelInfo]) -> AnalysisResult:
    """
    Analyze installed kernels and identify obsolete ones.
    
    Identifies the running kernel, latest kernel, and marks all others
    as obsolete. Never marks running or latest kernels for removal.
    
    Args:
        kernels: List of installed kernels
        
    Returns:
        AnalysisResult: Analysis results with removal recommendations
        
    Raises:
        ValueError: If no running kernel found in the list
    """
    if not kernels:
        raise ValueError("No kernels provided for analysis")
    
    # Find running kernel
    running_kernel = None
    for kernel in kernels:
        if kernel.is_running:
            running_kernel = kernel
            break
    
    if not running_kernel:
        raise ValueError("Running kernel not found in installed kernels list")
    
    # Find latest kernel by version comparison
    latest_kernel = kernels[0]
    for kernel in kernels[1:]:
        if compare_kernel_versions(kernel.version, latest_kernel.version) > 0:
            latest_kernel = kernel
    
    latest_kernel.is_latest = True
    
    # Identify obsolete kernels (not running and not latest)
    protected_versions = {running_kernel.version, latest_kernel.version}
    obsolete_kernels = []
    protected_kernels = []
    
    for kernel in kernels:
        if kernel.version in protected_versions:
            protected_kernels.append(kernel.package_name)
        else:
            obsolete_kernels.append(kernel.package_name)
    
    # Final safety validation before returning results
    is_safe, error_msg = validate_removal_safety(
        packages_to_remove=obsolete_kernels,
        running_kernel=running_kernel.version,
        latest_kernel=latest_kernel.version,
        all_kernels=kernels
    )
    
    if not is_safe:
        raise ValueError(error_msg)
    
    return AnalysisResult(
        running_kernel=running_kernel.version,
        latest_kernel=latest_kernel.version,
        obsolete_kernels=obsolete_kernels,
        obsolete_headers=[],  # Will be filled by match_headers_to_kernels
        protected_kernels=protected_kernels,
    )


def match_headers_to_kernels(headers: List[str], kernel_versions: Set[str]) -> List[str]:
    """
    Match header packages to kernel versions to find orphaned headers.
    
    Identifies header packages whose corresponding kernel is not in the
    protected kernel versions set.
    
    Args:
        headers: List of installed header packages (e.g., 'linux-headers-5.15.0-82-generic')
        kernel_versions: Set of kernel versions to keep (e.g., {'5.15.0-91-generic'})
        
    Returns:
        List[str]: List of header packages that can be removed
    """
    obsolete_headers = []
    
    for header in headers:
        # Extract version from header package name
        # linux-headers-5.15.0-82-generic -> 5.15.0-82-generic
        version = header.replace("linux-headers-", "")
        
        # If the version is not in the protected set, mark for removal
        if version not in kernel_versions:
            obsolete_headers.append(header)
    
    return obsolete_headers


def validate_removal_safety(
    packages_to_remove: List[str],
    running_kernel: str,
    latest_kernel: str,
    all_kernels: List[KernelInfo]
) -> Tuple[bool, str]:
    """
    Validate that the proposed package removal is safe.
    
    Performs safety checks to ensure:
    - Running kernel is not being removed
    - Latest kernel is not being removed
    - At least one kernel will remain after removal
    
    Args:
        packages_to_remove: List of packages marked for removal
        running_kernel: Version of the currently running kernel
        latest_kernel: Version of the latest installed kernel
        all_kernels: List of all installed kernels
        
    Returns:
        Tuple[bool, str]: (is_safe, error_message)
            is_safe: True if removal is safe
            error_message: Description of safety violation (empty if safe)
    """
    # Check if running kernel package is in removal list
    running_pkg = f"linux-image-{running_kernel}"
    if running_pkg in packages_to_remove:
        return False, f"Safety check failed: Running kernel {running_kernel} is marked for removal"
    
    # Check if latest kernel package is in removal list
    latest_pkg = f"linux-image-{latest_kernel}"
    if latest_pkg in packages_to_remove:
        return False, f"Safety check failed: Latest kernel {latest_kernel} is marked for removal"
    
    # Count how many kernel image packages will be removed
    kernel_images_to_remove = [pkg for pkg in packages_to_remove if "linux-image-" in pkg]
    remaining_kernels = len(all_kernels) - len(kernel_images_to_remove)
    
    if remaining_kernels < 1:
        return False, "Safety check failed: No kernels would remain after removal"
    
    # Warn if removing many kernels at once (more than 5)
    if len(kernel_images_to_remove) > 5:
        return False, f"Safety check warning: Attempting to remove {len(kernel_images_to_remove)} kernels at once. This seems excessive."
    
    return True, ""


def get_protected_packages(running_kernel: str, latest_kernel: str) -> Set[str]:
    """
    Get a set of package names that must never be removed.
    
    Args:
        running_kernel: Version of the currently running kernel
        latest_kernel: Version of the latest installed kernel
        
    Returns:
        Set[str]: Set of protected package names
    """
    protected = set()
    
    # Protect running kernel and its headers
    protected.add(f"linux-image-{running_kernel}")
    protected.add(f"linux-headers-{running_kernel}")
    
    # Protect latest kernel and its headers
    protected.add(f"linux-image-{latest_kernel}")
    protected.add(f"linux-headers-{latest_kernel}")
    
    return protected
