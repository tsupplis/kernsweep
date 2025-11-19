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
    
    Supports both standard Debian/Ubuntu (linux-image-*) and Proxmox (proxmox-kernel-*) kernels.
    
    Returns:
        List[KernelInfo]: List of installed kernels with metadata
        
    Raises:
        RuntimeError: If unable to query installed packages
    """
    try:
        # Query dpkg for installed kernel packages
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
        linux_pattern = re.compile(r'^ii\s+(linux-image-[\d\.\-]+\S*)\s+')
        
        # Pattern to match proxmox-kernel packages
        # Example: proxmox-kernel-6.17.2-1-pve-signed
        proxmox_pattern = re.compile(r'^ii\s+(proxmox-kernel-([\d\.\-]+\S+?)(?:-signed)?)\s+')
        
        for line in result.stdout.splitlines():
            # Try linux-image pattern
            match = linux_pattern.match(line)
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
                continue
            
            # Try proxmox-kernel pattern
            match = proxmox_pattern.match(line)
            if match:
                package_name = match.group(1)
                version = match.group(2)
                
                # Proxmox versions are like: 6.17.2-1-pve (at least 3 components)
                # Skip meta-packages like proxmox-kernel-6.14 (only 2 components)
                if re.match(r'^\d+\.\d+\.\d+', version):
                    kernels.append(KernelInfo(
                        version=version,
                        package_name=package_name,
                    ))
        
        # Return empty list if no kernels found (e.g., container/LXC environment)
        return kernels
    
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to query installed kernels: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error querying installed kernels: {e}")


def get_installed_headers() -> List[str]:
    """
    Get list of all installed kernel header packages.
    
    Supports both standard Debian/Ubuntu (linux-headers-*) and Proxmox (proxmox-headers-*) headers.
    
    Returns:
        List[str]: List of kernel header package names
        
    Raises:
        RuntimeError: If unable to query installed packages
    """
    try:
        # Query dpkg for installed header packages
        result = subprocess.run(
            ["dpkg", "-l"],
            capture_output=True,
            text=True,
            check=True,
        )
        
        headers = []
        # Pattern to match linux-headers packages
        # Example: linux-headers-5.15.0-82-generic
        linux_pattern = re.compile(r'^ii\s+(linux-headers-[\d\.\-]+\S*)\s+')
        
        # Pattern to match proxmox-headers packages
        # Example: proxmox-headers-6.17.2-1-pve
        proxmox_pattern = re.compile(r'^ii\s+(proxmox-headers-[\d\.\-]+\S+)\s+')
        
        for line in result.stdout.splitlines():
            # Try linux-headers pattern
            match = linux_pattern.match(line)
            if match:
                package_name = match.group(1)
                # Extract version to check if it's a specific version package
                version = package_name.replace("linux-headers-", "")
                
                # Skip meta-packages (generic, lowlatency, etc. without version numbers)
                if re.match(r'^\d+\.', version):
                    headers.append(package_name)
                continue
            
            # Try proxmox-headers pattern
            match = proxmox_pattern.match(line)
            if match:
                package_name = match.group(1)
                version = package_name.replace("proxmox-headers-", "")
                
                if re.match(r'^\d+\.', version):
                    headers.append(package_name)
        
        return headers
    
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to query installed headers: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error querying installed headers: {e}")
