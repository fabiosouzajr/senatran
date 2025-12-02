#!/usr/bin/env python3
"""
Test script for authentication with certificate configuration.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from auth_handler import AuthHandler
from playwright.sync_api import sync_playwright
from config import BROWSER_CONFIG, CERTIFICATE_CONFIG

def test_authentication():
    """Test the authentication flow with certificate configuration."""
    print("="*60)
    print("TESTING AUTHENTICATION WITH CERTIFICATE CONFIGURATION")
    print("="*60)
    print()
    
    # Check certificate configuration
    cert_path = CERTIFICATE_CONFIG.get('certificate_path')
    print(f"Certificate path configured: {cert_path}")
    if cert_path:
        cert_path_obj = Path(cert_path) if isinstance(cert_path, str) else cert_path
        if cert_path_obj.exists():
            print(f"✓ Certificate file found: {cert_path_obj}")
        else:
            print(f"✗ Certificate file not found: {cert_path_obj}")
    print()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=1000)
        context = browser.new_context(
            viewport=BROWSER_CONFIG['viewport'],
            user_agent=BROWSER_CONFIG['user_agent']
        )
        page = context.new_page()
        
        print("Browser initialized")
        print("Creating authentication handler...")
        auth_handler = AuthHandler(page)
        print("✓ Authentication handler initialized\n")
        
        print("Starting login process...")
        print("-" * 60)
        result = auth_handler.login()
        print("-" * 60)
        
        print()
        print("="*60)
        print("AUTHENTICATION TEST RESULTS")
        print("="*60)
        print(f"Login successful: {result}")
        print(f"Is authenticated: {auth_handler.is_authenticated}")
        print(f"Current URL: {page.url}")
        print()
        
        if result:
            print("✓ Authentication test PASSED")
            print("\nWaiting 5 seconds before closing browser...")
            time.sleep(5)
        else:
            print("✗ Authentication test FAILED")
            print("\nWaiting 10 seconds for inspection...")
            time.sleep(10)
        
        browser.close()
        print("\nBrowser closed")
        return result

if __name__ == "__main__":
    success = test_authentication()
    sys.exit(0 if success else 1)

