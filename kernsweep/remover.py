"""
Package removal module.

Provides functionality to remove kernel and header packages using apt.
"""

import os
import subprocess
from typing import List, Tuple
from enum import Enum


class RemovalStatus(Enum):
    """Status of a package removal operation."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


def check_sudo() -> bool:
    """
    Check if the current process has sudo privileges.
    
    Returns:
        bool: True if running with sudo/root, False otherwise
    """
    try:
        # On Unix systems, root has UID 0
        return os.geteuid() == 0
    except AttributeError:
        # os.geteuid() not available on Windows
        return False


def _execute_apt_removal(cmd: List[str], packages: List[str]) -> List[Tuple[str, RemovalStatus]]:
    """
    Execute apt-get removal command and return results.
    
    Args:
        cmd: apt-get command to execute
        packages: List of package names being removed
        
    Returns:
        List[Tuple[str, RemovalStatus]]: List of (package, status) tuples
        
    Raises:
        RuntimeError: If apt command fails
    """
    try:
        # Execute apt-get remove (output visible to user)
        result = subprocess.run(
            cmd,
            check=False,  # Don't raise on non-zero exit
        )
        
        if result.returncode == 0:
            return [(pkg, RemovalStatus.SUCCESS) for pkg in packages]
        
        # Failure - mark all as failed
        raise RuntimeError(
            f"apt-get remove failed with exit code {result.returncode}"
        )
    
    except subprocess.SubprocessError as e:
        # Command execution failed
        raise RuntimeError(f"Failed to execute apt-get: {e}")


def remove_packages(packages: List[str], dry_run: bool = False) -> List[Tuple[str, RemovalStatus]]:
    """
    Remove packages using apt.
    
    Args:
        packages: List of package names to remove
        dry_run: If True, simulate removal without actually removing
        
    Returns:
        List[Tuple[str, RemovalStatus]]: List of (package, status) tuples
        
    Raises:
        PermissionError: If not running with sufficient privileges
        RuntimeError: If apt command fails
    """
    if not packages:
        return []
    
    # In dry-run mode, just return success for all packages
    if dry_run:
        return [(pkg, RemovalStatus.SUCCESS) for pkg in packages]
    
    # Check for sudo privileges (not needed for dry-run)
    if not check_sudo():
        raise PermissionError(
            "Root privileges required. Please run with sudo."
        )
    
    # Generate apt command and execute
    cmd = generate_apt_command(packages)
    return _execute_apt_removal(cmd, packages)


def generate_apt_command(packages: List[str]) -> List[str]:
    """
    Generate the apt command to remove packages.
    
    Uses 'apt-get remove --autoremove --purge -y' to properly remove packages and their
    configuration files, and automatically remove any unused dependencies.
    The -y flag is always included to skip apt's confirmation prompt.
    
    Args:
        packages: List of package names to remove
        
    Returns:
        List[str]: Command as list of arguments
    """
    if not packages:
        raise ValueError("No packages provided for removal")
    
    # Build apt-get -y remove --autoremove --purge command
    cmd = ["apt-get", "-y", "remove", "--autoremove", "--purge"]
    
    # Add packages to remove
    cmd.extend(packages)
    
    return cmd
