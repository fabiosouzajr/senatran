#!/usr/bin/env python3
"""
Exploratory script to understand the fine details structure.
This script will help map all the required fine information fields.
"""

import time
import sys
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# URLs - This would typically be accessed after selecting a vehicle
# The actual URL pattern will be discovered during exploration

def explore_fine_details(headless=False, vehicle_url=None):
    """
    Explore the fine details page to understand:
    1. How fines are displayed (table, cards, modal)
    2. Field labels and their corresponding values
    3. Field extraction selectors
    4. Multiple fines handling (if a vehicle has multiple fines)
    """
    print("Starting fine details exploration...")
    print(f"Headless mode: {headless}\n")
    print("NOTE: This script assumes you are already logged in and on a vehicle's fine page.")
    print("You may need to navigate to a vehicle's fines manually first.\n")
    
    # Required fields to map
    required_fields = [
        "Órgão Autuador",
        "Órgão Competente/Responsável",
        "Local da Infração",
        "Data/Hora do Cometimento da Infração",
        "Número do Auto de Infração",
        "Código da Infração",
        "Número RENAINF",
        "Valor Original",
        "Data da Notificação de Autuação",
        "Data Limite para Interposição de Defesa Prévia",
        "Data Limite para Identificação do Condutor Infrator",
        "Data da Notificação de Penalidade",
        "Data Limite para Interposição de Recurso",
        "Data do Vencimento do Desconto",
    ]
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=1000)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()
        
        try:
            if vehicle_url:
                print(f"Step 1: Navigating to provided URL: {vehicle_url}")
                page.goto(vehicle_url, wait_until="networkidle", timeout=30000)
            else:
                print("Step 1: Waiting for manual navigation to vehicle fines page...")
                print("Please navigate to a vehicle's fines page in the browser.")
                input("Press Enter after you've navigated to the fines page...")
            
            time.sleep(3)
            print(f"Current URL: {page.url}")
            print(f"Page title: {page.title()}\n")
            
            # Take screenshot
            page.screenshot(path="fine_details_page.png")
            print("Screenshot saved as 'fine_details_page.png'\n")
            
            # Step 2: Analyze page structure
            print("Step 2: Analyzing page structure...")
            
            # Look for tables containing fine data
            tables = page.locator('table')
            print(f"Found {tables.count()} table(s)")
            
            # Look for cards or list items
            cards = page.locator('[class*="card"], [class*="fine"], [class*="multa"]')
            print(f"Found {cards.count()} potential card/list items")
            
            # Step 3: Map required fields
            print("\nStep 3: Mapping required fields...")
            
            field_mappings = {}
            page_text = page.inner_text('body')
            
            for field in required_fields:
                print(f"\nLooking for field: '{field}'")
                
                # Method 1: Look for label text
                label_selectors = [
                    f'label:has-text("{field}")',
                    f'*:has-text("{field}")',
                    f'[aria-label*="{field}"]',
                ]
                
                found = False
                for selector in label_selectors:
                    elements = page.locator(selector)
                    if elements.count() > 0:
                        print(f"  ✓ Found with selector: {selector}")
                        # Try to find associated value
                        for i in range(min(elements.count(), 3)):
                            element = elements.nth(i)
                            # Get parent or next sibling
                            parent = element.locator('..')
                            text = parent.inner_text()
                            # Try to extract value after label
                            if field in text:
                                parts = text.split(field, 1)
                                if len(parts) > 1:
                                    value = parts[1].strip().split('\n')[0].strip()
                                    print(f"    Potential value: {value[:50]}")
                                    field_mappings[field] = {
                                        'selector': selector,
                                        'sample_value': value[:100]
                                    }
                                    found = True
                                    break
                        if found:
                            break
                
                if not found:
                    # Method 2: Look for field in text and try to find nearby value
                    if field in page_text:
                        print(f"  ⚠ Field text found in page, but selector not found")
                        # Try to find it with regex or nearby elements
                    else:
                        print(f"  ✗ Field not found")
            
            # Step 4: Look for fine records (multiple fines)
            print("\nStep 4: Looking for fine records structure...")
            
            # Common patterns for multiple records
            record_selectors = [
                'tbody tr',
                '[class*="row"]',
                '[class*="record"]',
                '[class*="item"]',
            ]
            
            for selector in record_selectors:
                elements = page.locator(selector)
                count = elements.count()
                if count > 1:  # More than header
                    print(f"  Selector '{selector}': {count} elements (potential fine records)")
                    # Analyze first record structure
                    if count > 1:
                        first_record = elements.nth(1)  # Skip header if table
                        cells = first_record.locator('td, [class*="cell"], [class*="field"]')
                        print(f"    First record has {cells.count()} cells/fields")
                        if cells.count() > 0:
                            print(f"    Sample cells: {[c.inner_text()[:30] for c in cells.all()[:5]]}")
            
            # Step 5: Extract sample data
            print("\nStep 5: Attempting to extract sample fine data...")
            
            # Try to build a data structure
            sample_fines = []
            
            # If it's a table
            if tables.count() > 0:
                table = tables.first
                rows = table.locator('tbody tr')
                row_count = rows.count()
                print(f"  Found {row_count} data rows in table")
                
                if row_count > 0:
                    # Get headers
                    headers = table.locator('thead th, thead td')
                    header_texts = [h.inner_text().strip() for h in headers.all()]
                    print(f"  Headers: {header_texts}")
                    
                    # Extract first few rows
                    for i in range(min(row_count, 3)):
                        row = rows.nth(i)
                        cells = row.locator('td')
                        cell_texts = [c.inner_text().strip() for c in cells.all()]
                        fine_data = dict(zip(header_texts, cell_texts))
                        sample_fines.append(fine_data)
                        print(f"\n  Fine {i+1}:")
                        for key, value in fine_data.items():
                            print(f"    {key}: {value[:50]}")
            
            # Step 6: Look for expandable details
            print("\nStep 6: Checking for expandable detail views...")
            expandable = page.locator('[class*="expand"], [class*="detail"], [aria-expanded]')
            if expandable.count() > 0:
                print(f"  Found {expandable.count()} potentially expandable elements")
                print("  (Some fine details might be hidden in expandable sections)")
            
            # Step 7: Check for modals or detail pages
            print("\nStep 7: Checking for detail modals/pages...")
            modals = page.locator('[class*="modal"], [class*="dialog"], [role="dialog"]')
            if modals.count() > 0:
                print(f"  Found {modals.count()} potential modal/dialog elements")
            
            # Final summary
            print("\n" + "="*60)
            print("FIELD MAPPING SUMMARY")
            print("="*60)
            print(f"Fields mapped: {len(field_mappings)}/{len(required_fields)}")
            print("\nMapped fields:")
            for field, mapping in field_mappings.items():
                print(f"  ✓ {field}")
                print(f"    Selector: {mapping['selector']}")
                print(f"    Sample: {mapping['sample_value']}")
            
            print(f"\nUnmapped fields:")
            for field in required_fields:
                if field not in field_mappings:
                    print(f"  ✗ {field}")
            
            if sample_fines:
                print(f"\nSample fines extracted: {len(sample_fines)}")
            
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
    vehicle_url = None
    if len(sys.argv) > 2 and not sys.argv[-1].startswith('--'):
        vehicle_url = sys.argv[-1]
    
    explore_fine_details(headless=headless, vehicle_url=vehicle_url)



