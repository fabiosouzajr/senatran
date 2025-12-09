"""
Setup script for uBlock Origin adblock extension.
This script helps download and set up the extension for use with the browser automation.
"""

import sys
from pathlib import Path
from adblock_helper import setup_ublock_origin, UBLOCK_EXTENSION_DIR, EXTENSIONS_DIR

def main():
    """Main setup function."""
    print("="*70)
    print("uBlock Origin Adblock Extension Setup")
    print("="*70)
    print()
    
    try:
        extension_path = setup_ublock_origin()
        print()
        print("="*70)
        print("✓ SUCCESS: uBlock Origin extension is ready!")
        print("="*70)
        print(f"Extension location: {extension_path}")
        print()
        print("The extension will be automatically loaded when you run the main script.")
        print("You can disable it by setting ENABLE_ADBLOCK=false in your .env file.")
        print()
        
    except FileNotFoundError as e:
        print()
        print("="*70)
        print("EXTENSION NOT FOUND")
        print("="*70)
        print()
        print("Please download uBlock Origin manually:")
        print()
        print("METHOD 1 - Download CRX file:")
        print("1. Visit: https://chrome.google.com/webstore/detail/ublock-origin/cjpalhdlnbpafiamejdnhcphjbkeiagm")
        print("2. Use a CRX downloader tool (e.g., https://crxextractor.com/)")
        print(f"3. Save the downloaded .crx file as: {EXTENSIONS_DIR / 'ublock_origin.crx'}")
        print("4. Run this script again: python setup_adblock.py")
        print()
        print("METHOD 2 - Download ZIP from GitHub:")
        print("1. Visit: https://github.com/gorhill/uBlock/releases")
        print("2. Download the latest source code .zip file")
        print(f"3. Extract it to: {UBLOCK_EXTENSION_DIR}")
        print("4. Run this script again: python setup_adblock.py")
        print()
        print("METHOD 3 - Manual installation in browser:")
        print("1. Install uBlock Origin in a regular Chrome/Chromium browser")
        print("2. Find the extension directory in your browser's user data folder")
        print("3. Copy it to the location above")
        print()
        sys.exit(1)
        
    except Exception as e:
        print()
        print("="*70)
        print("ERROR")
        print("="*70)
        print(f"Failed to set up extension: {e}")
        print()
        sys.exit(1)

if __name__ == "__main__":
    main()
