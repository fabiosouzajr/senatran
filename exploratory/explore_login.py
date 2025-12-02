#!/usr/bin/env python3
"""
Exploratory script to understand the Senatran login flow and certificate authentication.
This script will help identify the elements and flow needed for automation.
"""

import time
import sys
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# URLs
SENATRAN_HOME = "https://portalservicos.senatran.serpro.gov.br/#/home"
SSO_LOGIN_URL = "https://sso.acesso.gov.br/login"

def explore_login_flow(headless=False):
    """
    Explore the login flow to understand:
    1. The "Entrar com" button location
    2. SSO redirect behavior
    3. Certificate selection dialog trigger
    4. Authentication completion indicators
    """
    print("Starting login flow exploration...")
    print(f"Target URL: {SENATRAN_HOME}")
    print(f"Headless mode: {headless}\n")
    
    with sync_playwright() as p:
        # Launch browser (Chromium for better certificate support)
        browser = p.chromium.launch(headless=headless, slow_mo=1000)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()
        
        try:
            # Step 1: Navigate to Senatran home
            print("Step 1: Navigating to Senatran home page...")
            try:
                page.goto(SENATRAN_HOME, wait_until="load", timeout=60000)
            except PlaywrightTimeoutError:
                print("  'load' timeout, trying 'domcontentloaded'...")
                try:
                    page.goto(SENATRAN_HOME, wait_until="domcontentloaded", timeout=60000)
                except PlaywrightTimeoutError:
                    print("  Navigation timeout, proceeding anyway...")
                    page.goto(SENATRAN_HOME, timeout=10000)
            time.sleep(3)
            print(f"Current URL: {page.url}")
            print(f"Page title: {page.title()}\n")
            
            # Step 2: Find and analyze the "Entrar com" button
            print("Step 2: Looking for 'Entrar com' button...")
            try:
                # Try to find button with span class="ml-1" and text "Entrar com"
                entrar_button = page.locator('span.ml-1:has-text("Entrar com")')
                if entrar_button.count() > 0:
                    print(f"Found 'Entrar com' button (count: {entrar_button.count()})")
                    # Get parent element (likely a button or link)
                    parent = entrar_button.locator('..')
                    print(f"Parent tag: {parent.evaluate('el => el.tagName')}")
                    print(f"Parent text: {parent.inner_text()}")
                    print(f"Parent href (if link): {parent.get_attribute('href') if parent.evaluate('el => el.tagName').lower() == 'a' else 'N/A'}")
                else:
                    # Try alternative selectors
                    print("Trying alternative selectors...")
                    buttons = page.locator('button, a').filter(has_text="Entrar")
                    print(f"Found {buttons.count()} elements with 'Entrar' text")
                    for i in range(min(buttons.count(), 5)):
                        print(f"  Element {i}: {buttons.nth(i).inner_text()}")
            except Exception as e:
                print(f"Error finding button: {e}")
            
            print("\nWaiting 5 seconds for manual inspection...")
            time.sleep(5)
            
            # Step 3: Click the button and observe redirect
            print("\nStep 3: Attempting to click 'Entrar com' button...")
            try:
                entrar_button = page.locator('span.ml-1:has-text("Entrar com")').locator('..')
                if entrar_button.count() > 0:
                    entrar_button.first.click()
                    print("Button clicked, waiting for navigation...")
                    try:
                        page.wait_for_load_state("load", timeout=30000)
                    except PlaywrightTimeoutError:
                        page.wait_for_load_state("domcontentloaded", timeout=15000)
                    time.sleep(3)
                    print(f"Current URL after click: {page.url}")
                    
                    # Check if redirected to SSO
                    if "sso.acesso.gov.br" in page.url:
                        print("✓ Successfully redirected to SSO login page")
                        
                        # Step 4: Analyze SSO page structure
                        print("\nStep 4: Analyzing SSO page structure...")
                        print(f"Page title: {page.title()}")
                        
                        # Look for certificate selection element
                        print("\nLooking for certificate selection element...")
                        try:
                            cert_element = page.locator('#cert-digital')
                            if cert_element.count() > 0:
                                print("✓ Found #cert-digital element")
                                print(f"  Tag: {cert_element.evaluate('el => el.tagName')}")
                                print(f"  Text: {cert_element.inner_text()}")
                                print(f"  Visible: {cert_element.is_visible()}")
                            else:
                                print("✗ #cert-digital not found, trying alternative selectors...")
                                # Try other common patterns
                                cert_links = page.locator('a, button, div').filter(has_text="certificado")
                                print(f"Found {cert_links.count()} elements with 'certificado' text")
                        except Exception as e:
                            print(f"Error finding certificate element: {e}")
                        
                        # Take a screenshot for reference
                        page.screenshot(path="sso_page.png")
                        print("\nScreenshot saved as 'sso_page.png'")
                        
                        print("\nWaiting 10 seconds for manual certificate selection...")
                        print("(In production, this will be automated)")
                        time.sleep(10)
                        
                        # Check if redirected back to Senatran
                        print(f"\nCurrent URL after waiting: {page.url}")
                        if "portalservicos.senatran" in page.url:
                            print("✓ Successfully authenticated and redirected back to Senatran")
                            
                            # Check for login indicators
                            print("\nChecking for login success indicators...")
                            # Look for user menu, logout button, or user name
                            user_indicators = page.locator('text=/sair|logout|usuário|user/i')
                            if user_indicators.count() > 0:
                                print(f"Found {user_indicators.count()} potential login indicators")
                        else:
                            print("Still on SSO page - authentication may not be complete")
                    else:
                        print(f"Unexpected redirect to: {page.url}")
                else:
                    print("Could not find 'Entrar com' button")
            except PlaywrightTimeoutError:
                print("Timeout waiting for navigation")
            except Exception as e:
                print(f"Error during click/navigation: {e}")
            
            # Final state analysis
            print("\n" + "="*60)
            print("FINAL STATE ANALYSIS")
            print("="*60)
            print(f"Final URL: {page.url}")
            print(f"Page title: {page.title()}")
            
            # Get all cookies
            cookies = context.cookies()
            print(f"\nCookies found: {len(cookies)}")
            for cookie in cookies[:5]:  # Show first 5
                print(f"  - {cookie['name']}: {cookie['domain']}")
            
            print("\nWaiting 10 seconds before closing for final inspection...")
            time.sleep(10)
            
        except Exception as e:
            print(f"\nError during exploration: {e}")
            import traceback
            traceback.print_exc()
        finally:
            browser.close()
    
    print("\nExploration complete!")

if __name__ == "__main__":
    # Allow headless mode via command line argument
    headless = "--headless" in sys.argv
    explore_login_flow(headless=headless)



