#!/usr/bin/env python3
"""
Exploratory script to understand the vehicle listing structure.
This script will help identify how vehicles are displayed and paginated.
"""

import time
import sys
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# URLs
VEHICLE_LIST_URL = "https://portalservicos.senatran.serpro.gov.br/#/infracoes/consultar/veiculo"

def explore_vehicle_list(headless=False):
    """
    Explore the vehicle list page to understand:
    1. How vehicles are displayed (table, list, cards)
    2. Vehicle identifier format (plate, ID, etc.)
    3. Pagination mechanism (if any)
    4. Navigation to individual vehicle fines
    """
    print("Starting vehicle list exploration...")
    print(f"Target URL: {VEHICLE_LIST_URL}")
    print(f"Headless mode: {headless}\n")
    print("NOTE: This script assumes you are already logged in.")
    print("Run explore_login.py first or log in manually.\n")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=1000)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()
        
        try:
            # Navigate to vehicle list page
            print("Step 1: Navigating to vehicle list page...")
            try:
                page.goto(VEHICLE_LIST_URL, wait_until="load", timeout=60000)
            except PlaywrightTimeoutError:
                print("  'load' timeout, trying 'domcontentloaded'...")
                try:
                    page.goto(VEHICLE_LIST_URL, wait_until="domcontentloaded", timeout=60000)
                except PlaywrightTimeoutError:
                    print("  Navigation timeout, proceeding anyway...")
                    page.goto(VEHICLE_LIST_URL, timeout=10000)
            time.sleep(3)
            print(f"Current URL: {page.url}")
            print(f"Page title: {page.title()}\n")
            
            # Take screenshot for reference
            page.screenshot(path="vehicle_list_page.png")
            print("Screenshot saved as 'vehicle_list_page.png'\n")
            
            # Step 2: Analyze page structure
            print("Step 2: Analyzing page structure...")
            
            # Look for tables
            tables = page.locator('table')
            print(f"Found {tables.count()} table(s)")
            if tables.count() > 0:
                for i in range(min(tables.count(), 3)):
                    print(f"\nTable {i+1}:")
                    rows = tables.nth(i).locator('tr')
                    print(f"  Rows: {rows.count()}")
                    if rows.count() > 0:
                        # Get header row
                        headers = rows.first.locator('th, td')
                        header_texts = [h.inner_text() for h in headers.all()]
                        print(f"  Headers: {header_texts}")
            
            # Look for lists or cards
            lists = page.locator('ul, ol, [class*="list"], [class*="card"]')
            print(f"\nFound {lists.count()} potential list/card containers")
            
            # Step 3: Look for vehicle identifiers
            print("\nStep 3: Looking for vehicle identifiers...")
            
            # Common patterns: plates (ABC-1234, ABC1234), IDs, links
            plate_patterns = [
                r'[A-Z]{3}-?\d{4}',
                r'[A-Z]{3}\d{1}[A-Z]\d{2}',  # Mercosul format
            ]
            
            # Look for clickable elements that might lead to vehicle details
            clickable_elements = page.locator('a, button, [role="button"], [onclick]')
            print(f"Found {clickable_elements.count()} clickable elements")
            
            # Look for text that might be vehicle plates
            all_text = page.inner_text('body')
            import re
            for pattern in plate_patterns:
                matches = re.findall(pattern, all_text, re.IGNORECASE)
                if matches:
                    print(f"  Found potential plates with pattern {pattern}: {matches[:10]}")
            
            # Step 4: Check for pagination
            print("\nStep 4: Checking for pagination...")
            pagination_selectors = [
                'nav[aria-label*="pagination"]',
                '[class*="pagination"]',
                '[class*="pager"]',
                'button:has-text("próximo")',
                'button:has-text("anterior")',
                'button:has-text("next")',
                'button:has-text("previous")',
                'a:has-text(">")',
                'a:has-text("<")',
            ]
            
            for selector in pagination_selectors:
                elements = page.locator(selector)
                if elements.count() > 0:
                    print(f"  Found pagination element: {selector} ({elements.count()} found)")
            
            # Step 5: Analyze DOM structure
            print("\nStep 5: Analyzing DOM structure...")
            
            # Get main content area
            main_content = page.locator('main, [role="main"], [class*="content"], [class*="container"]')
            if main_content.count() > 0:
                print(f"Found main content area: {main_content.first.evaluate('el => el.className')}")
            
            # Look for data attributes that might contain vehicle info
            data_elements = page.locator('[data-vehicle], [data-plate], [data-id]')
            if data_elements.count() > 0:
                print(f"Found {data_elements.count()} elements with vehicle data attributes")
            
            # Step 6: Try to extract vehicle information
            print("\nStep 6: Attempting to extract vehicle information...")
            
            # Common selectors for vehicle lists
            vehicle_selectors = [
                'tr[data-vehicle]',
                '[class*="vehicle"]',
                '[class*="veiculo"]',
                'tbody tr',
            ]
            
            vehicles_found = []
            for selector in vehicle_selectors:
                elements = page.locator(selector)
                count = elements.count()
                if count > 0:
                    print(f"  Selector '{selector}': {count} elements")
                    # Try to extract text from first few
                    for i in range(min(count, 5)):
                        text = elements.nth(i).inner_text()
                        if text.strip():
                            vehicles_found.append(text.strip()[:100])  # First 100 chars
                            print(f"    Element {i+1}: {text.strip()[:100]}")
            
            # Step 7: Check for API calls (network monitoring)
            print("\nStep 7: Monitoring network requests...")
            print("(This would show API endpoints that fetch vehicle data)")
            
            # Wait and observe
            print("\nWaiting 5 seconds for page to fully load...")
            time.sleep(5)
            
            # Final analysis
            print("\n" + "="*60)
            print("FINAL ANALYSIS")
            print("="*60)
            print(f"Page URL: {page.url}")
            print(f"Vehicles potentially found: {len(vehicles_found)}")
            
            if vehicles_found:
                print("\nSample vehicle data:")
                for i, vehicle in enumerate(vehicles_found[:5], 1):
                    print(f"  {i}. {vehicle}")
            
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
    headless = "--headless" in sys.argv
    explore_vehicle_list(headless=headless)



