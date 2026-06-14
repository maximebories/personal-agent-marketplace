---
name: antigravity-gui-linux-updater
description: >-
  Checks for updates to the manual Antigravity GUI installation, downloads
  the latest version from the official repository, backs up the current
  installation, and safely performs the upgrade.
---

# Antigravity GUI Auto-Updater

## Overview
This skill allows agents to check for updates and update the manual installation of the Antigravity GUI text editor/IDE on the local system.

## Dependencies
None.

## Quick Start
To check for updates without installing:
```bash
uv run .agents/skills/antigravity-gui-linux-updater/update_antigravity.py --check-only
```

To perform the update:
```bash
uv run .agents/skills/antigravity-gui-linux-updater/update_antigravity.py
```

## Utility Scripts
The updater script `update_antigravity.py` provides the following CLI flags:

* `--check-only`: (Optional) Only verify if a new version exists and print version info, but do not download or install.
* `--force`: (Optional) Force installation of the retrieved version even if it is the same or older than the installed version.
* `--target-dir PATH`: (Optional) Override the default installation directory (defaults to `~/.local/share/antigravity`).
* `--bin-dir PATH`: (Optional) Override the directory where the shell execution wrapper is created (defaults to `~/.local/bin`).

## Common Mistakes
1. **Running while Antigravity is open**: Upgrading files while the application is active might cause file locks or app instability. The script attempts to detect and close running processes, but it is best to close the editor before updating.
2. **Missing shell script permissions**: Ensure that the wrapper script directory `~/.local/bin` is in the user's `$PATH` so the updated `antigravity` command is available system-wide.
