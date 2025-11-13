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

# Import kernsweep - it should be installed as a package
try:
    from kernsweep.detector import get_running_kernel, get_installed_kernels, get_installed_headers
    from kernsweep.analyzer import analyze_kernels, match_headers_to_kernels
    from kernsweep.remover import remove_packages, check_sudo, RemovalStatus
    from kernsweep.utils import needs_reboot
    KERNSWEEP_AVAILABLE = True
except ImportError as e:
    KERNSWEEP_AVAILABLE = False
    KERNSWEEP_IMPORT_ERROR = str(e)


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
