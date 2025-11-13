"""
Utility functions.

Shared helper functions used across kernsweep modules.
"""

import subprocess
from typing import List, Tuple


def run_command(cmd: List[str], check: bool = True) -> Tuple[int, str, str]:
    """
    Run a shell command and capture output.
    
    Args:
        cmd: Command as list of arguments
        check: If True, raise exception on non-zero exit code
        
    Returns:
        Tuple[int, str, str]: (exit_code, stdout, stderr)
        
    Raises:
        subprocess.CalledProcessError: If check=True and command fails
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=check,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        if check:
            raise
        return e.returncode, e.stdout or "", e.stderr or ""


def parse_package_size(dpkg_output: str) -> int:
    """
    Parse package size from dpkg output.
    
    Args:
        dpkg_output: Output from dpkg-query
        
    Returns:
        int: Package size in bytes
    """
    # TODO: Implement when needed
    raise NotImplementedError()


def needs_reboot() -> bool:
    """
    Check if a system reboot is needed.
    
    Checks for the presence of /var/run/reboot-required file,
    which is created by Debian/Ubuntu systems when a reboot is needed.
    
    Returns:
        bool: True if reboot is needed
    """
    import os  # Local import to avoid unused import at module level
    
    # Check for Debian/Ubuntu reboot-required file
    reboot_required_file = "/var/run/reboot-required"
    
    try:
        return os.path.exists(reboot_required_file)
    except (OSError, PermissionError):
        # If we can't check, assume no reboot needed
        return False
