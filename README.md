# Personal Agent Tools & Skills Marketplace

Welcome to my personal marketplace for agent tools, skills, and plugins! This repository serves as a centralized hub for custom extensions and automation scripts to enhance agent capabilities.

---

## Directory Structure

* **`skills/`**: Standalone agent skills that can be copied directly into local or global agent directories.
* **`plugins/`**: Fully packaged agent plugins containing metadata (`plugin.json`) and complex logic.

---

## Available Skills

### 1. Antigravity GUI Linux Updater (`antigravity-gui-linux-updater`)
Checks for updates to manual `.tar.gz` installations of the Antigravity IDE on Linux, downloads the latest archive, takes a backup of the current installation, extracts the new version, and restores configuration shortcuts.

#### Usage
To check for updates:
```bash
uv run skills/antigravity-gui-linux-updater/update_antigravity.py --check-only
```

To perform the update:
```bash
uv run skills/antigravity-gui-linux-updater/update_antigravity.py
```

---

## How to Install Skills from this Marketplace

To copy a skill into your current repository workspace's local agent folder:

```bash
# 1. Download/clone the marketplace source to a temporary folder
git clone --depth 1 https://github.com/maximebories/personal-agent-marketplace.git /tmp/marketplace

# 2. Ensure target local skills directory exists
mkdir -p .agents/skills/

# 3. Copy the specific skill folder
cp -r /tmp/marketplace/skills/antigravity-gui-linux-updater .agents/skills/

# 4. Clean up temporary files
rm -rf /tmp/marketplace
```
