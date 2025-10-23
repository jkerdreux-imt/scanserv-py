#!/usr/bin/env python3

import requests
import os
import argparse
from datetime import datetime
import sys
import tomli
from pathlib import Path

__version__ = '0.1.0'

def get_config_path():
    """Get the path to the config file based on the platform"""
    if os.name == 'nt':  # Windows
        config_dir = os.path.join(os.getenv('APPDATA'), 'scanserv')
    else:  # Linux/Mac
        config_dir = os.path.join(os.path.expanduser('~'), '.config', 'scanserv')
    
    return os.path.join(config_dir, 'config.toml')

def load_config():
    """Load configuration from file, returns defaults if no file exists"""
    config_path = get_config_path()
    
    defaults = {
        'server': 'http://scan.home',
        'device': 1,
        'scan': {
            'resolution': 200,
            'mode': 'Color',
            'quality': 'high'
        },
        'files': {
            'output_dir': 'scans'
        }
    }
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'rb') as f:
                config = tomli.load(f)
                # Merge with defaults to ensure all keys exist
                if 'scan' not in config:
                    config['scan'] = defaults['scan']
                if 'files' not in config:
                    config['files'] = defaults['files']
                if 'device' not in config:
                    config['device'] = defaults['device']
                return config
        except Exception as e:
            print(f"Warning: Error reading config file: {e}")
            return defaults
    return defaults

class Scanner:
    def __init__(self, server_url="http://scan.home"):
        self.server_url = server_url
        self.device_id = None
        self.devices = []

    def list_scanners(self):
        """List all available scanners and return them"""
        try:
            response = requests.get(f"{self.server_url}/api/v1/context")
            if response.status_code == 200:
                data = response.json()
                self.devices = data.get('devices', [])
                
                print("Available scanners:")
                for i, device in enumerate(self.devices, 1):
                    print(f"{i}. ID: {device['id']}")
                    print(f"   Name: {device['name']}")
                    print()
                    
                return self.devices
            else:
                print(f"Error: {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"Connection error: {e}")
            return []

    def select_scanner(self, device_number):
        """Select scanner by its number (1-based index)"""
        if not self.devices:
            self.list_scanners()
            
        if not self.devices:
            print("No scanners found")
            sys.exit(1)
            
        try:
            index = int(device_number) - 1
            if 0 <= index < len(self.devices):
                self.device_id = self.devices[index]['id']
                print(f"Selected scanner: {self.devices[index]['name']}")
            else:
                print(f"Invalid scanner number. Please choose between 1 and {len(self.devices)}")
                sys.exit(1)
        except ValueError:
            print("Invalid scanner number")
            sys.exit(1)

    def list_files(self):
        """List all scanned files on the server"""
        try:
            response = requests.get(f"{self.server_url}/api/v1/files")
            if response.status_code == 200:
                files = response.json()
                if files:
                    print("\nFiles on server:")
                    for file_info in files:
                        print(f"- {file_info['name']} ({file_info['sizeString']})")
                    print()
                return files
            else:
                print(f"Error: {response.status_code}")
                return []
        except requests.exceptions.RequestException as e:
            print(f"Connection error: {e}")
            return []

    def download_file(self, filename, output_dir=None):
        """Download a specific file from the server
        
        Args:
            filename (str): Name of the file to download
            output_dir (str, optional): Directory to save the file. If None, use current directory
        
        Returns:
            str: Path to downloaded file or None if failed
        """
        try:
            file_url = f"{self.server_url}/api/v1/files/{filename}"
            response = requests.get(file_url)
            
            if response.status_code == 200:
                # If no output_dir specified, use current directory
                local_path = os.path.join(output_dir, filename) if output_dir else filename
                
                # Create output directory if needed
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                    
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                return local_path
            else:
                print(f"Error downloading {filename}: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Connection error downloading {filename}: {e}")
            return None

    def download_all(self, output_dir=None):
        """Download all files from the server
        
        Args:
            output_dir (str, optional): Directory to save files. If None, use current directory
        """
        # Create output directory if specified and doesn't exist
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # Get list of files
        files = self.list_files()
        if not files:
            print("No files found on server")
            return

        print(f"Found {len(files)} files")
        
        # Download each file
        for file_info in files:
            filename = file_info['name']
            print(f"Downloading {filename}...")
            local_path = self.download_file(filename, output_dir)
            if local_path:
                print(f"Saved to: {local_path}")

    def scan_a4(self, output_dir=None, resolution=200, mode="Color", quality="high"):
        """Scan an A4 document and optionally download it
        
        Args:
            output_dir (str, optional): Directory to save scanned files. If None, don't download
            resolution (int): DPI resolution (default: 200)
            mode (str): Color mode - "Color", "Gray" (default: "Color")
            quality (str): Quality level - "high", "medium", or "low" (default: "high")
        
        Returns:
            str: Path to downloaded file or None if failed or no download requested
        """
        if not self.device_id:
            print("No scanner selected. Use --device to select a scanner.")
            return None

        # Create output directory if specified and doesn't exist
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # A4 dimensions in mm
        width = 210
        height = 297
        
        scan_request = {
            "params": {
                "deviceId": self.device_id,
                "resolution": resolution,
                "mode": mode,
                "width": width,
                "height": height,
                "pageWidth": width,
                "pageHeight": height,
                "top": 0,
                "left": 0
            },
            "pipeline": f"JPG | @:pipeline.{quality}-quality"
        }

        try:
            # Send scan request
            print("Scanning...")
            response = requests.post(f"{self.server_url}/api/v1/scan", json=scan_request)
            
            if response.status_code == 200:
                result = response.json()
                if "file" in result:
                    filename = result['file']['name']
                    print(f"Scan successful!")
                    print(f"File on server: {filename}")
                    
                    # Download the file if requested
                    if output_dir is not None:  # Download if output_dir is specified (even if empty string)
                        print("Downloading...")
                        local_path = self.download_file(filename, output_dir)
                        if local_path:
                            print(f"Saved to: {local_path}")
                            return local_path
                    return None
                else:
                    print("Scan completed but no file information returned")
                    return None
            else:
                print(f"Error: {response.status_code}")
                print(response.text)
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Connection error: {e}")
            return None

def main():
    # Load configuration
    config = load_config()
    
    parser = argparse.ArgumentParser(description='Scanner command line interface')
    
    parser.add_argument('--server', default=config.get('server'),
                      help=f'Scanner server URL (default: {config.get("server")})')
    parser.add_argument('--device', type=int, default=config.get('device'),
                      help=f'Scanner number (default: {config.get("device")})')
    parser.add_argument('--list', action='store_true',
                      help='List available scanners')
    parser.add_argument('--scan', action='store_true',
                      help='Scan a document')
    parser.add_argument('--no-download', action='store_true',
                      help='Do not download the scanned file locally')
    parser.add_argument('--download-all', action='store_true',
                      help='Download all scanned files from server')
    parser.add_argument('--download', type=str, metavar='FILENAME',
                      help='Download a specific file from server')
    parser.add_argument('--output-dir', default=config['files'].get('output_dir'),
                      help=f'Output directory for downloaded files (default: {config["files"].get("output_dir")})')
    parser.add_argument('--resolution', type=int, default=config['scan'].get('resolution'),
                      help=f'Scan resolution in DPI (default: {config["scan"].get("resolution")})')
    parser.add_argument('--mode', choices=['Color', 'Gray'], 
                      default=config['scan'].get('mode'),
                      help=f'Color mode (default: {config["scan"].get("mode")})')
    parser.add_argument('--quality', choices=['high', 'medium', 'low'], 
                      default=config['scan'].get('quality'),
                      help=f'Image quality (default: {config["scan"].get("quality")})')

    args = parser.parse_args()

    # Create scanner instance
    scanner = Scanner(server_url=args.server)

    # By default or with --list, show available scanners and files
    if not len(sys.argv) > 1 or args.list:
        scanner.list_scanners()
        scanner.list_files()
        return

    if args.scan:
        # Select scanner
        scanner.select_scanner(args.device)
        scanner.scan_a4(
            output_dir=None if args.no_download else args.output_dir,
            resolution=args.resolution,
            mode=args.mode,
            quality=args.quality
        )

    if args.download_all:
        scanner.download_all(output_dir=args.output_dir)

    if args.download:
        if scanner.download_file(args.download, args.output_dir):
            dest = f"to {args.output_dir}" if args.output_dir else "to current directory"
            print(f"Downloaded {args.download} {dest}")

if __name__ == "__main__":
    main()
