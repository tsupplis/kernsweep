#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: kernsweep
short_description: Detect and remove obsolete Linux kernels
version_added: "0.1.0"
description:
    - Detects obsolete Linux kernel packages on Debian/Ubuntu systems
    - Protects running kernel and latest installed kernel
    - Removes old kernel images and headers to free disk space
    - Provides safety checks to prevent system boot failures
options:
    state:
        description:
            - Whether to remove obsolete kernels or just report them
        type: str
        choices: [ absent, present ]
        default: present
    verbosity:
        description:
            - Output verbosity level
        type: str
        choices: [ quiet, normal, verbose ]
        default: normal
author:
    - KernSweep Contributors
notes:
    - Requires root privileges to remove packages
    - Always protects the running kernel and latest installed kernel
    - Uses apt-get with --autoremove and --purge flags
requirements:
    - python >= 3.7
    - dpkg (Debian/Ubuntu package management)
'''

EXAMPLES = r'''
# Check what kernels would be removed (check mode)
- name: Check for obsolete kernels
  kernsweep:
    state: present
  check_mode: yes

# Remove obsolete kernels
- name: Clean up old kernels
  kernsweep:
    state: absent

# Remove obsolete kernels with verbose output
- name: Clean up old kernels (verbose)
  kernsweep:
    state: absent
    verbosity: verbose

# Just report status quietly
- name: Check kernel status
  kernsweep:
    state: present
    verbosity: quiet
'''

RETURN = r'''
changed:
    description: Whether any kernels were removed
    type: bool
    returned: always
    sample: true
failed:
    description: Whether the operation failed
    type: bool
    returned: always
    sample: false
msg:
    description: Human readable message about what happened
    type: str
    returned: always
    sample: "Successfully removed 2 obsolete kernel package(s)"
removed_packages:
    description: List of package names that were removed
    type: list
    elements: str
    returned: when changed
    sample: ["linux-image-6.12.41+deb13-amd64", "linux-headers-6.12.41+deb13-amd64"]
obsolete_count:
    description: Number of obsolete packages found
    type: int
    returned: always
    sample: 2
running_kernel:
    description: Currently running kernel version
    type: str
    returned: always
    sample: "6.12.43+deb13-amd64"
latest_kernel:
    description: Latest installed kernel version
    type: str
    returned: always
    sample: "6.12.48+deb13-amd64"
reboot_required:
    description: Whether a reboot is required to use the latest kernel
    type: bool
    returned: always
    sample: true
'''

from ansible.module_utils.basic import AnsibleModule


# ===== EMBEDDED KERNSWEEP CODE =====
# The following code is embedded from the kernsweep package

import subprocess
import os
import re
from typing import List, Set, Tuple, Optional
from enum import Enum
from dataclasses import dataclass, field


# ===== From kernsweep/utils.py =====

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

# ===== From kernsweep/detector.py =====

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

# ===== From kernsweep/analyzer.py =====

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

# ===== From kernsweep/remover.py =====

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

# ===== END EMBEDDED KERNSWEEP CODE =====


# Kernsweep is now available (embedded above)
KERNSWEEP_AVAILABLE = True
KERNSWEEP_IMPORT_ERROR = None




def run_module():
    """Main Ansible module execution."""
    module_args = dict(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        verbosity=dict(type='str', default='normal', choices=['quiet', 'normal', 'verbose']),
    )

    result = dict(
        changed=False,
        failed=False,
        msg='',
        removed_packages=[],
        obsolete_count=0,
        running_kernel='',
        latest_kernel='',
        reboot_required=False,
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    # Check if kernsweep is available
    if not KERNSWEEP_AVAILABLE:
        result['msg'] = f"Failed to import kernsweep: {KERNSWEEP_IMPORT_ERROR}"
        result['failed'] = True
        module.fail_json(**result)

    # Check for root privileges when not in check mode and state is absent
    if module.params['state'] == 'absent' and not module.check_mode:
        if not check_sudo():
            result['msg'] = "Root privileges required for package removal"
            result['failed'] = True
            module.fail_json(**result)

    try:
        # Step 1: Detect running kernel
        running_kernel_version = get_running_kernel()
        result['running_kernel'] = running_kernel_version

        # Step 2: Detect installed kernels
        installed_kernels = get_installed_kernels()

        # Mark the running kernel
        for kernel in installed_kernels:
            if kernel.version == running_kernel_version:
                kernel.is_running = True
                break

        # Step 3: Analyze kernels
        analysis = analyze_kernels(installed_kernels)
        result['latest_kernel'] = analysis.latest_kernel

        # Step 4: Detect headers and match to kernels
        installed_headers = get_installed_headers()
        protected_versions = {analysis.running_kernel, analysis.latest_kernel}
        obsolete_headers = match_headers_to_kernels(installed_headers, protected_versions)
        analysis.obsolete_headers = obsolete_headers

        # Check if reboot is required
        result['reboot_required'] = needs_reboot() or analysis.running_kernel != analysis.latest_kernel

        # Collect obsolete packages
        all_obsolete = analysis.obsolete_kernels + analysis.obsolete_headers
        result['obsolete_count'] = len(all_obsolete)

        if len(all_obsolete) == 0:
            result['msg'] = "No obsolete kernels or headers found"
            module.exit_json(**result)

        # Handle state logic
        if module.params['state'] == 'present':
            # Just report what's there
            result['msg'] = f"Found {len(all_obsolete)} obsolete package(s)"
            result['removed_packages'] = all_obsolete
            module.exit_json(**result)

        # state == 'absent' - remove packages
        if module.check_mode:
            # Check mode - don't actually remove
            result['changed'] = True
            result['msg'] = f"Would remove {len(all_obsolete)} obsolete package(s)"
            result['removed_packages'] = all_obsolete
            module.exit_json(**result)

        # Actually remove packages
        results = remove_packages(all_obsolete, dry_run=False)

        # Count successes and failures
        success_count = sum(1 for _, status in results if status == RemovalStatus.SUCCESS)
        failed_count = len(results) - success_count

        if failed_count > 0:
            result['failed'] = True
            result['msg'] = f"Failed to remove {failed_count} package(s), successfully removed {success_count}"
            module.fail_json(**result)

        # Success
        result['changed'] = True
        result['msg'] = f"Successfully removed {success_count} obsolete package(s)"
        result['removed_packages'] = all_obsolete

        module.exit_json(**result)

    except Exception as e:
        result['failed'] = True
        result['msg'] = f"Error: {str(e)}"
        module.fail_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
