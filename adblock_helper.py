"""
Adblock extension helper for Playwright browser automation.
Downloads and sets up uBlock Origin extension for Chromium browsers.
"""

import os
import zipfile
import shutil
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# uBlock Origin Chrome Web Store ID
UBLOCK_ORIGIN_ID = "cjpalhdlnbpafiamejdnhcphjbkeiagm"

# Extension directory
EXTENSIONS_DIR = Path(__file__).parent / ".extensions"
UBLOCK_EXTENSION_DIR = EXTENSIONS_DIR / "ublock_origin"


def download_ublock_origin() -> Path:
    """
    Attempt to download uBlock Origin extension.
    Note: Automatic download may not work reliably. Manual setup is recommended.
    
    Returns:
        Path to the extracted extension directory
    
    Raises:
        Exception: If download or extraction fails
    """
    if UBLOCK_EXTENSION_DIR.exists() and any(UBLOCK_EXTENSION_DIR.iterdir()):
        logger.info(f"uBlock Origin extension already exists at {UBLOCK_EXTENSION_DIR}")
        return UBLOCK_EXTENSION_DIR
    
    EXTENSIONS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check if CRX file already exists
    crx_file = EXTENSIONS_DIR / "ublock_origin.crx"
    zip_file = EXTENSIONS_DIR / "ublock_origin.zip"
    
    # Try to use existing CRX or ZIP file
    source_file = None
    if crx_file.exists():
        source_file = crx_file
        logger.info(f"Found existing CRX file: {crx_file}")
    elif zip_file.exists():
        source_file = zip_file
        logger.info(f"Found existing ZIP file: {zip_file}")
    
    if not source_file:
        # Provide instructions for manual download
        print("\n" + "="*70)
        print("UBLOCK ORIGIN EXTENSION SETUP")
        print("="*70)
        print("\nTo install uBlock Origin adblock extension:")
        print("\nOPTION 1 - Manual Download (Recommended):")
        print("1. Visit: https://chrome.google.com/webstore/detail/ublock-origin/cjpalhdlnbpafiamejdnhcphjbkeiagm")
        print("2. Use a CRX downloader (e.g., https://crxextractor.com/)")
        print(f"3. Save the .crx file as: {crx_file}")
        print("4. Run the script again")
        print("\nOPTION 2 - Download ZIP directly:")
        print("1. Visit: https://github.com/gorhill/uBlock/releases")
        print("2. Download the latest .zip file")
        print(f"3. Extract it to: {UBLOCK_EXTENSION_DIR}")
        print("4. Run the script again")
        print("\n" + "="*70 + "\n")
        raise FileNotFoundError(
            f"uBlock Origin extension not found. Please download it manually to {crx_file} or {zip_file}"
        )
    
    # Extract the file
    try:
        logger.info(f"Extracting uBlock Origin from {source_file.name}...")
        UBLOCK_EXTENSION_DIR.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(source_file, 'r') as zip_ref:
            zip_ref.extractall(UBLOCK_EXTENSION_DIR)
        
        # Verify extraction (check for manifest.json)
        manifest_file = UBLOCK_EXTENSION_DIR / "manifest.json"
        if not manifest_file.exists():
            raise ValueError("Extracted extension missing manifest.json - may be corrupted")
        
        logger.info(f"✓ uBlock Origin extracted to {UBLOCK_EXTENSION_DIR}")
        
        # Optionally remove source file after successful extraction
        # source_file.unlink()
        
        return UBLOCK_EXTENSION_DIR
        
    except zipfile.BadZipFile:
        raise ValueError(f"Invalid ZIP/CRX file: {source_file}. Please re-download.")
    except Exception as e:
        logger.error(f"Failed to extract uBlock Origin: {e}")
        raise


def setup_ublock_origin() -> Path:
    """
    Set up uBlock Origin extension. Attempts to download/extract if not present.
    
    Returns:
        Path to the extension directory
    
    Raises:
        FileNotFoundError: If extension is not found and cannot be downloaded
    """
    # Check if extension is already set up
    if UBLOCK_EXTENSION_DIR.exists():
        # Verify it has manifest.json (indicates valid extension)
        manifest_file = UBLOCK_EXTENSION_DIR / "manifest.json"
        if manifest_file.exists():
            logger.debug("uBlock Origin extension already set up")
            return UBLOCK_EXTENSION_DIR
        else:
            # Directory exists but is empty or invalid - try to set up again
            logger.warning("Extension directory exists but appears invalid, attempting setup...")
            try:
                shutil.rmtree(UBLOCK_EXTENSION_DIR)
            except Exception as e:
                logger.warning(f"Could not remove invalid extension directory: {e}")
    
    try:
        return download_ublock_origin()
    except FileNotFoundError:
        # Re-raise with clearer message
        raise FileNotFoundError(
            f"uBlock Origin extension not found. Please download it manually.\n"
            f"See instructions above or visit: "
            f"https://chrome.google.com/webstore/detail/ublock-origin/{UBLOCK_ORIGIN_ID}"
        )
    except Exception as e:
        logger.error(f"Failed to set up uBlock Origin: {e}")
        raise


def get_adblock_extension_path() -> Path | None:
    """
    Get the path to the adblock extension if available.
    
    Returns:
        Path to extension directory, or None if not available
    """
    if UBLOCK_EXTENSION_DIR.exists() and any(UBLOCK_EXTENSION_DIR.iterdir()):
        return UBLOCK_EXTENSION_DIR
    return None


def is_adblock_available() -> bool:
    """
    Check if adblock extension is available.
    
    Returns:
        True if extension is available, False otherwise
    """
    return get_adblock_extension_path() is not None
