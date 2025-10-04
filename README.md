# scanserv

A CLI and Python module for [scanservjs](https://github.com/sbs20/scanservjs), an awesome web-based UI for SANE scanners. scanservjs is a fantastic piece of software that makes scanning on Linux a breeze - it's one of those tools that just works perfectly!

## Installation

```bash
# Install directly from GitHub
pipx install git+https://github.com/jkerdreux-imt/scanserv-py.git

# Or from local source
pipx install .
```

## Configuration

Create a configuration file:
- Linux/Mac: `~/.config/scanserv/config.toml`
- Windows: `%APPDATA%/scanserv/config.toml`

Example configuration:
```toml
# Server settings
server = "http://scan.home"

# Default scan settings
[scan]
resolution = 200
mode = "Color"     # Color, Gray, or Lineart
quality = "high"   # high, medium, or low

# Default file settings
[files]
output_dir = "scans"  # Default download directory
```

## CLI Usage

List scanners and files (default):
```bash
scanserv
```

Scan a document:
```bash
scanserv --scan
scanserv --scan --mode Gray --resolution 300
scanserv --scan --no-download  # Keep file on server only
```

Download files:
```bash
scanserv --download "scan_2023.jpg"      # Download specific file
scanserv --download-all                   # Download all files
scanserv --download-all --output-dir docs # Download to specific directory
```

All options:
```bash
scanserv --help
```

## Python Module Usage

```python
from scanserv import Scanner

# Create scanner instance
scanner = Scanner(server_url="http://scan.home")

# List available scanners
devices = scanner.list_scanners()

# Scan document
scanner.scan_a4(
    resolution=300,
    mode="Color",  # or "Gray" or "Lineart"
    quality="high" # or "medium" or "low"
)

# Download files
scanner.download_all(output_dir="scans")
```