"""
Kernel detection module.

Provides functionality to detect the currently running kernel and
discover all installed kernels and headers on the system.
"""

import re
import subprocess
from typing import List
from dataclasses import dataclass


@dataclass
class KernelInfo:
    """
    Information about an installed kernel.
    
    Attributes:
        version: Full kernel version string (e.g., '5.15.0-82-generic')
        package_name: Package name (e.g., 'linux-image-5.15.0-82-generic')
        is_running: True if this is the currently running kernel
        is_latest: True if this is the latest installed kernel
    """
    version: str
    package_name: str
    is_running: bool = False
    is_latest: bool = False


def get_running_kernel() -> str:
    """
    Detect the currently running kernel version.
    
    Returns:
        str: Running kernel version string (e.g., '5.15.0-82-generic')
        
    Raises:
        RuntimeError: If unable to detect the running kernel
    """
    try:
        # Use uname -r to get the kernel release version
        result = subprocess.run(
            ["uname", "-r"],
            capture_output=True,
            text=True,
            check=True,
        )
        kernel_version = result.stdout.strip()
        
        if not kernel_version:
            raise RuntimeError("uname returned empty kernel version")
        
        return kernel_version
    
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to detect running kernel: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error detecting running kernel: {e}")


def get_installed_kernels() -> List[KernelInfo]:
    """
    Get list of all installed kernel packages.
    
    Returns:
        List[KernelInfo]: List of installed kernels with metadata
        
    Raises:
        RuntimeError: If unable to query installed packages
    """
    try:
        # Query dpkg for installed linux-image packages
        # Format: package name, status
        result = subprocess.run(
            ["dpkg", "-l"],
            capture_output=True,
            text=True,
            check=True,
        )
        
        kernels = []
        # Pattern to match linux-image packages
        # Example: linux-image-5.15.0-82-generic
        pattern = re.compile(r'^ii\s+(linux-image-[\d\.\-]+\S*)\s+')
        
        for line in result.stdout.splitlines():
            match = pattern.match(line)
            if match:
                package_name = match.group(1)
                # Extract version from package name
                # linux-image-5.15.0-82-generic -> 5.15.0-82-generic
                version = package_name.replace("linux-image-", "")
                
                # Skip meta-packages (generic, lowlatency, etc. without version numbers)
                if re.match(r'^\d+\.', version):
                    kernels.append(KernelInfo(
                        version=version,
                        package_name=package_name,
                    ))
        
        if not kernels:
            raise RuntimeError("No kernel packages found")
        
        return kernels
    
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to query installed kernels: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error querying installed kernels: {e}")


def get_installed_headers() -> List[str]:
    """
    Get list of all installed kernel header packages.
    
    Returns:
        List[str]: List of kernel header package names
        
    Raises:
        RuntimeError: If unable to query installed packages
    """
    try:
        # Query dpkg for installed linux-headers packages
        result = subprocess.run(
            ["dpkg", "-l"],
            capture_output=True,
            text=True,
            check=True,
        )
        
        headers = []
        # Pattern to match linux-headers packages
        # Example: linux-headers-5.15.0-82-generic
        pattern = re.compile(r'^ii\s+(linux-headers-[\d\.\-]+\S*)\s+')
        
        for line in result.stdout.splitlines():
            match = pattern.match(line)
            if match:
                package_name = match.group(1)
                # Extract version to check if it's a specific version package
                version = package_name.replace("linux-headers-", "")
                
                # Skip meta-packages (generic, lowlatency, etc. without version numbers)
                if re.match(r'^\d+\.', version):
                    headers.append(package_name)
        
        return headers
    
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to query installed headers: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error querying installed headers: {e}")
