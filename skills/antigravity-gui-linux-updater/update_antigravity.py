#!/usr/bin/env python3
"""
Antigravity Auto-Updater Script
This script checks for updates to the manual Antigravity GUI installation,
downloads the latest version from the official distribution repository,
takes a backup of the current installation, and extracts the new version.
"""

import argparse
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import urllib.error
from pathlib import Path

DEFAULT_TARGET_DIR = Path.home() / ".local" / "share" / "antigravity"
DEFAULT_BIN_DIR = Path.home() / ".local" / "bin"
DOWNLOAD_PAGE_URL = "https://antigravity.google/download?app=antigravity"
BASE_URL = "https://antigravity.google"

def get_installed_version(target_dir: Path) -> str:
    """Gets the version of the currently installed Antigravity application."""
    asar_archive = target_dir / "resources" / "app.asar"
    binary_path = target_dir / "antigravity"
    
    if not asar_archive.exists() or not binary_path.exists():
        return "0.0.0"
    
    # Run Node/Electron to read package.json version inside ASAR
    try:
        env = os.environ.copy()
        env["ELECTRON_RUN_AS_NODE"] = "1"
        asar_package_json = asar_archive / "package.json"
        cmd = [
            str(binary_path),
            "-e",
            "console.log(JSON.parse(require('fs').readFileSync(process.argv[1], 'utf8')).version)",
            str(asar_package_json)
        ]
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except Exception as e:
        # Fallback to checking product.json if app.asar parsing failed
        product_json_path = target_dir / "resources" / "app" / "product.json"
        if product_json_path.exists():
            try:
                with open(product_json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("ideVersion", "0.0.0")
            except Exception:
                pass
        return "0.0.0"

def parse_version(version_str: str):
    """Parses a version string into a tuple of integers for comparison."""
    # Matches numbers, e.g. "2.1.4" -> (2, 1, 4)
    return tuple(map(int, re.findall(r"\d+", version_str)))

def fetch_latest_release_info():
    """Scrapes the download page to find the latest version and download URL."""
    try:
        # Step 1: Fetch the download page HTML
        headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
        req = urllib.request.Request(DOWNLOAD_PAGE_URL, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            raw_content = response.read()
            if response.info().get('Content-Encoding') == 'gzip':
                raw_content = gzip.decompress(raw_content)
            html = raw_content.decode("utf-8", errors="ignore")
            
        # Step 2: Find the main javascript bundle
        js_match = re.search(r'src="([^"]*main[^"]*\.js)"', html)
        if not js_match:
            # Fallback regex if it lacks a hyphen
            js_match = re.search(r'src="([^"]*main\.js)"', html)
            
        if not js_match:
            raise ValueError("Could not find the main JavaScript bundle on the download page.")
            
        js_path = js_match.group(1)
        if js_path.startswith("/"):
            js_url = f"{BASE_URL}{js_path}"
        elif js_path.startswith("http"):
            js_url = js_path
        else:
            js_url = f"{BASE_URL}/{js_path}"
            
        # Step 3: Fetch the Javascript bundle
        req_js = urllib.request.Request(js_url, headers=headers)
        with urllib.request.urlopen(req_js, timeout=10) as response:
            raw_js = response.read()
            if response.info().get('Content-Encoding') == 'gzip':
                raw_js = gzip.decompress(raw_js)
            js_content = raw_js.decode("utf-8", errors="ignore")
            
        # Step 4: Parse out the latest linux-x64 .tar.gz URL
        # Pattern like: https://storage.googleapis.com/antigravity-public/antigravity-hub/2.1.4-6481382726303744/linux-x64/Antigravity.tar.gz
        url_pattern = r'(https://storage\.googleapis\.com/antigravity-public/antigravity-hub/([^/]+)/linux-x64/Antigravity\.tar\.gz)'
        url_match = re.search(url_pattern, js_content)
        
        if not url_match:
            raise ValueError("Could not find the Antigravity linux-x64 download URL in the javascript bundle.")
            
        download_url = url_match.group(1)
        raw_version_dir = url_match.group(2) # e.g. "2.1.4-6481382726303744"
        
        # Extract version number (e.g. 2.1.4)
        version_num_match = re.match(r"^(\d+\.\d+\.\d+)", raw_version_dir)
        version = version_num_match.group(1) if version_num_match else raw_version_dir
        
        return {
            "version": version,
            "url": download_url,
            "raw_version_dir": raw_version_dir
        }
    except Exception as e:
        print(f"Error fetching release info: {e}", file=sys.stderr)
        raise

def is_running(target_dir: Path) -> bool:
    """Checks if Antigravity is currently running from the target directory."""
    binary_path = target_dir / "antigravity"
    if not binary_path.exists():
        return False
    try:
        # Check running processes using pgrep
        result = subprocess.run(["pgrep", "-f", str(binary_path)], capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False

def kill_running_processes(target_dir: Path):
    """Kills any running Antigravity processes from the target directory."""
    binary_path = target_dir / "antigravity"
    if not binary_path.exists():
        return
    print("Stopping running Antigravity processes...")
    try:
        subprocess.run(["pkill", "-f", str(binary_path)], check=False)
    except Exception as e:
        print(f"Warning: Could not kill running processes: {e}", file=sys.stderr)

def download_file(url: str, dest: Path):
    """Downloads a file with a basic progress indicator."""
    print(f"Downloading from {url}...")
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024 * 1024 # 1 MB
            downloaded = 0
            
            with open(dest, "wb") as f:
                while True:
                    block = response.read(block_size)
                    if not block:
                        break
                    f.write(block)
                    downloaded += len(block)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"Progress: {percent:.1f}% ({downloaded // (1024*1024)}MB / {total_size // (1024*1024)}MB)", end="\r")
                    else:
                        print(f"Downloaded: {downloaded // (1024*1024)}MB", end="\r")
            print("\nDownload complete.")
    except Exception as e:
        print(f"\nDownload failed: {e}", file=sys.stderr)
        raise

def setup_launchers(target_dir: Path, bin_dir: Path):
    """Ensures the wrapper script in bin_dir and the desktop file in local applications exist."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    wrapper_path = bin_dir / "antigravity"
    
    # Write wrapper script
    print(f"Setting up wrapper script at {wrapper_path}...")
    wrapper_content = f"""#!/bin/bash
exec {target_dir}/antigravity "$@"
"""
    with open(wrapper_path, "w", encoding="utf-8") as f:
        f.write(wrapper_content)
    wrapper_path.chmod(0o755)
    
    # Write desktop shortcut file
    desktop_dir = Path.home() / ".local" / "share" / "applications"
    desktop_dir.mkdir(parents=True, exist_ok=True)
    desktop_path = desktop_dir / "antigravity.desktop"
    
    print(f"Setting up desktop shortcut at {desktop_path}...")
    desktop_content = f"""[Desktop Entry]
Type=Application
Name=Antigravity
Comment=Antigravity Coding Assistant & IDE
Exec={wrapper_path} %U
Icon={target_dir}/icon.png
Terminal=false
Categories=Development;IDE;
MimeType=x-scheme-handler/antigravity;
StartupWMClass=antigravity
"""
    with open(desktop_path, "w", encoding="utf-8") as f:
        f.write(desktop_content)
    desktop_path.chmod(0o755)

def main():
    parser = argparse.ArgumentParser(description="Auto-updater for local Antigravity installation")
    parser.add_argument("--target-dir", type=str, default=str(DEFAULT_TARGET_DIR),
                        help=f"Installation directory (default: {DEFAULT_TARGET_DIR})")
    parser.add_argument("--bin-dir", type=str, default=str(DEFAULT_BIN_DIR),
                        help=f"Local bin directory (default: {DEFAULT_BIN_DIR})")
    parser.add_argument("--check-only", action="store_true",
                        help="Only check if an update is available without installing")
    parser.add_argument("--force", action="store_true",
                        help="Force update even if version is current or newer")
    args = parser.parse_args()
    
    target_dir = Path(args.target_dir)
    bin_dir = Path(args.bin_dir)
    
    print("Checking installed version...")
    installed_ver = get_installed_version(target_dir)
    print(f"Installed Version: {installed_ver}")
    
    print("Checking latest release info...")
    try:
        latest_info = fetch_latest_release_info()
    except Exception:
        print("Failed to check for updates. Please check your network connection.", file=sys.stderr)
        sys.exit(1)
        
    latest_ver = latest_info["version"]
    download_url = latest_info["url"]
    print(f"Latest Version:    {latest_ver}")
    
    # Compare versions
    is_newer = parse_version(latest_ver) > parse_version(installed_ver)
    
    if args.check_only:
        if is_newer:
            print(f"Update available! {installed_ver} -> {latest_ver}")
            print(f"Download URL: {download_url}")
        else:
            print("Antigravity is already up to date.")
        sys.exit(0)
        
    if not is_newer and not args.force:
        print("Antigravity is already up to date. Use --force to reinstall.")
        sys.exit(0)
        
    print(f"Updating Antigravity: {installed_ver} -> {latest_ver}")
    
    # Check if application is running
    if is_running(target_dir):
        print("Warning: Antigravity is currently running.", file=sys.stderr)
        print("Please close Antigravity before updating.", file=sys.stderr)
        # Attempt to kill processes
        kill_running_processes(target_dir)
        
    # Download tarball
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        tar_path = tmp_dir_path / "Antigravity.tar.gz"
        
        try:
            download_file(download_url, tar_path)
        except Exception:
            sys.exit(1)
            
        print("Extracting package...")
        try:
            with tarfile.open(tar_path, "r:gz") as tar:
                tar.extractall(path=tmp_dir_path)
        except Exception as e:
            print(f"Extraction failed: {e}", file=sys.stderr)
            sys.exit(1)
            
        # The tarball extracts to Antigravity/Antigravity-x64/ or similar
        # Let's locate the directory containing the 'antigravity' executable
        extracted_app_dir = None
        for root, dirs, files in os.walk(tmp_dir_path):
            if "antigravity" in files and "resources" in dirs:
                extracted_app_dir = Path(root)
                break
                
        if not extracted_app_dir:
            print("Error: Extracted package does not contain valid Antigravity files.", file=sys.stderr)
            sys.exit(1)
            
        print(f"Found extracted application at: {extracted_app_dir}")
        
        # Backup existing installation
        backup_dir = target_dir.with_name(f"{target_dir.name}.bak")
        if target_dir.exists():
            print(f"Backing up current installation to {backup_dir}...")
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            shutil.move(str(target_dir), str(backup_dir))
            
        # Move new installation to target
        print(f"Installing new version to {target_dir}...")
        try:
            target_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(extracted_app_dir), str(target_dir))
            
            # Make sure main binary is executable
            (target_dir / "antigravity").chmod(0o755)
            if (target_dir / "chrome-sandbox").exists():
                # Electron's chrome-sandbox requires setuid or root permissions, or 755
                (target_dir / "chrome-sandbox").chmod(0o4755)
                
            # If there was a custom icon we need to restore, or copy the new logo
            # The app package contains a logo at resources/app/resources/linux/code.png or resources/linux/code.png
            icon_source = target_dir / "resources" / "app" / "resources" / "linux" / "code.png"
            if not icon_source.exists():
                # fallback check
                icon_source = target_dir / "resources" / "linux" / "code.png"
            if icon_source.exists():
                shutil.copy(str(icon_source), str(target_dir / "icon.png"))
                
            print("Setting up system launchers and shortcuts...")
            setup_launchers(target_dir, bin_dir)
            
            # Clean up backup
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
                
            print(f"Successfully updated Antigravity to version {latest_ver}!")
            
        except Exception as e:
            print(f"Installation failed: {e}", file=sys.stderr)
            if backup_dir.exists():
                print("Restoring from backup...", file=sys.stderr)
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                shutil.move(str(backup_dir), str(target_dir))
            sys.exit(1)

if __name__ == "__main__":
    main()
