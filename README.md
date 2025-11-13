# KernSweep

A lightweight command-line tool to detect and remove obsolete Linux kernels and headers.

## Overview

KernSweep helps keep your Linux system clean by identifying and removing old kernel packages that are no longer needed, while protecting the currently running kernel and the latest installed kernel.

## Features

- 🔍 Detects currently running kernel
- 📦 Identifies all installed kernels and headers
- 🧹 Safely removes obsolete kernels (keeping running and latest)
- 🛡️ Built-in safety checks to prevent system breakage
- 📊 apt-style output and reporting
- 🔄 Reboot detection
- 🧪 Dry-run mode for safe testing
- 🐍 Pure Python with no external dependencies

## Installation

### From source

```bash
git clone https://github.com/yourusername/kernsweep.git
cd kernsweep
pip install -e .
```

### For development

```bash
pip install -e ".[dev]"
```

## Usage

### Show help

```bash
kernsweep
# or
kernsweep --help
```

### Dry run (see what would be removed)

```bash
kernsweep --dry-run
```

### Remove obsolete kernels

```bash
sudo kernsweep --remove
```

### Remove with automatic yes to prompts

```bash
sudo kernsweep --remove --yes
```

### Verbose output

```bash
kernsweep --dry-run --verbose
```

## Command-line Options

- `--dry-run` - Show what would be removed without actually removing anything
- `--remove` - Remove obsolete kernels and headers (requires sudo)
- `-v, --verbose` - Enable verbose output
- `-q, --quiet` - Suppress non-essential output
- `--yes` - Assume yes to all prompts (use with --remove)
- `--version` - Show version information

## Exit Codes

KernSweep uses meaningful exit codes for automation and scripting:

- `0` - Success (removal completed or dry-run found work to do)
- `1` - Nothing to do (no obsolete packages found)
- `-1` - Insufficient privileges (not running as root)
- `-2` - APT command failed during removal
- `2` - Reboot required (successful removal but system needs restart)

## Safety Features

KernSweep includes multiple safety mechanisms to prevent system breakage:

1. **Protected Kernels**: Never removes the running kernel or the latest installed kernel
2. **Double-Check Validation**: Validates removal list before execution to ensure protected kernels are not included
3. **Minimum Kernel Protection**: Ensures at least one kernel remains on the system after removal
4. **Bulk Removal Warning**: Prevents accidental removal of excessive numbers of kernels (>5)
5. **Reboot Detection**: Detects when system requires reboot after kernel updates
6. **Dry-run Mode**: Test operations before making changes
7. **Confirmation Prompts**: Asks for confirmation before removal (unless `--yes` is used)
8. **Privilege Checks**: Ensures proper permissions before attempting removal

## Requirements

- Python 3.7 or higher
- Linux system with apt package manager
- sudo privileges (for removal operations)

## Test Coverage

The project includes comprehensive unit tests with 89% code coverage:
- 26 tests for kernel detection and analysis (including edge cases)
- 16 tests for output formatting and reporting
- 15 tests for package removal operations
- 13 tests for system detection
- 10 tests for safety validation
- 9 tests for CLI integration
- 8 tests for utility functions

**Total: 95 tests, all passing ✅**

Coverage by module:
- remover.py: 100%
- analyzer.py: 98%
- utils.py: 95%
- reporter.py: 93%
- detector.py: 91%
- cli.py: 78%

## Ansible Integration

KernSweep includes a self-contained Ansible module for automated kernel cleanup across multiple hosts.

### Building the Ansible Module

```bash
python3 build-ansible-module.py
```

This creates a self-contained module in `dist/kernsweep.py` with all dependencies embedded.

### Using with Ansible

```yaml
- name: Remove obsolete kernels
  hosts: all
  become: yes
  tasks:
    - name: Clean up old kernels
      kernsweep:
        state: absent
```

Run the playbook:

```bash
ANSIBLE_LIBRARY=dist ansible-playbook playbooks/simple-cleanup.yml
```

### Module Parameters

- `state` - `present` (report only) or `absent` (remove obsolete kernels)
- `verbosity` - `quiet`, `normal`, or `verbose`

### Module Return Values

- `changed` - Whether any kernels were removed
- `msg` - Human readable status message
- `removed_packages` - List of removed package names
- `obsolete_count` - Number of obsolete packages found
- `running_kernel` - Currently running kernel version
- `latest_kernel` - Latest installed kernel version
- `reboot_required` - Whether a reboot is needed

### Check Mode Support

The module fully supports Ansible's `--check` mode to preview changes without making them.

See `playbooks/cleanup-kernels.yml` for a complete example.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Disclaimer

Always backup your system before removing kernel packages. While KernSweep includes safety checks, kernel management is a critical system operation.
