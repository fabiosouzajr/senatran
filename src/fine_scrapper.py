"""
Fine scraper module for extracting traffic fines from SENATRAN portal.
Implements step-by-step iteration through vehicles and their fines.

NAVIGATION APPROACH - PROS AND CONS:

Current Implementation: Same Tab Navigation (using page.go_back())
-------------------------------------------------------------------
PROS:
- Simpler code - no tab management needed
- Lower memory usage - only one page in memory
- Faster - no tab switching overhead
- More human-like behavior
- Easier to debug - single browser window
- Better for sites that rely on browser history/state

CONS:
- Must wait for page to reload when going back
- Risk of losing state if navigation fails
- Slower overall if pages take long to load
- Can't compare vehicles side-by-side

Alternative: New Tab Navigation (open each vehicle in new tab)
-------------------------------------------------------------------
PROS:
- Faster iteration - no need to reload list page
- Can keep list page state intact
- Parallel processing possible (with limits)
- Easier to recover if one vehicle page fails

CONS:
- More complex code - tab management required
- Higher memory usage - multiple pages open
- Must close tabs to avoid memory leaks
- May trigger anti-bot detection (too many tabs)
- More complex error handling
- Some sites block multiple tabs

RECOMMENDATION:
- Start with same-tab navigation (current implementation)
- Switch to new-tab if performance becomes an issue
- Can be made configurable via config.py if needed
"""

import asyncio
import logging
import random
import re
import sys
from typing import List
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

import config
import human_behavior
from captcha_solver import detect_and_solve_captcha
from rate_limit_handler import check_for_rate_limit_error

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def wait_for_page_ready(page: Page, timeout: int = None) -> None:
    """
    Wait for page to be ready using lenient strategies suitable for SPAs.
    Doesn't fail on timeout - just gives the page time to render.
    
    Args:
        page: Playwright Page object
        timeout: Timeout in milliseconds (uses config default if None)
    """
    if timeout is None:
        timeout = config.DEFAULT_TIMEOUT
    
    try:
        # Try to wait for load state, but use shorter timeout
        await page.wait_for_load_state("load", timeout=min(10000, timeout // 3))
    except Exception:
        # If load state times out, just give SPA time to render
        logger.debug("Load state timeout, giving page time to render...")
        await asyncio.sleep(1.5)  # Give SPA time to initialize


async def check_and_handle_captcha_error(page: Page, operation_name: str = "operation") -> bool:
    """
    Check for CAPTCHA error messages and handle them appropriately.
    
    Args:
        page: Playwright Page object
        operation_name: Name of the operation that triggered the check (for logging)
    
    Returns:
        True if no error or error was handled, False if error persists
    """
    try:
        # Wait a moment for error messages to appear
        await asyncio.sleep(1.0)
        
        # Check for CAPTCHA error messages
        error_text = await check_for_rate_limit_error(page)
        
        if error_text and "captcha" in error_text.lower():
            logger.warning(f"CAPTCHA error detected after {operation_name}: {error_text}")
            
            # Check if there's actually a visible CAPTCHA widget
            captcha_widgets = await page.locator("iframe[src*='hcaptcha'], iframe[src*='recaptcha'], div[id*='hcaptcha'], div[class*='hcaptcha']").count()
            
            if captcha_widgets > 0:
                logger.info("Visible CAPTCHA widget detected, attempting to solve...")
                if config.ENABLE_CAPTCHA_SOLVING:
                    captcha_solved = await detect_and_solve_captcha(page)
                    if captcha_solved:
                        logger.info("CAPTCHA solved successfully")
                        await asyncio.sleep(2.0)
                        return True
                    else:
                        logger.warning("Failed to solve CAPTCHA")
                        return False
            else:
                # No visible CAPTCHA widget - this is an API-level error
                logger.warning("CAPTCHA error message but no visible widget - likely API-level rate limiting")
                logger.info("Waiting longer before retrying...")
                # Wait longer (2-5 seconds as per audit recommendations)
                wait_time = random.uniform(2.0, 5.0)
                logger.info(f"Waiting {wait_time:.1f} seconds before retrying...")
                await asyncio.sleep(wait_time)
                
                # Try to refresh or navigate back
                try:
                    await page.reload(wait_until="domcontentloaded", timeout=10000)
                    await asyncio.sleep(2.0)
                    logger.info("Page refreshed, checking for error again...")
                    
                    # Check again after refresh
                    error_text_after = await check_for_rate_limit_error(page)
                    if error_text_after and "captcha" in error_text_after.lower():
                        logger.error("CAPTCHA error persists after refresh")
                        return False
                    else:
                        logger.info("Error cleared after refresh")
                        return True
                except Exception as e:
                    logger.warning(f"Error refreshing page: {e}")
                    return False
        
        return True
        
    except Exception as e:
        logger.warning(f"Error checking for CAPTCHA error: {e}")
        return True  # Assume no error if check fails


async def getfines(page: Page) -> None:
    """
    Scrape traffic fines from the SENATRAN portal.
    
    Flow:
    1. Navigate to FINES_URL
    2. Wait for vehicle list to load
    3. Iterate through all pages of vehicles
    4. For each vehicle, open it and find fine elements
    5. Print information to console
    
    Args:
        page: Playwright Page object to use for navigation and scraping
    """
    try:
        logger.info("Starting fine scraping process...")
        
        # Step 1: Navigate to FINES_URL with human-like behavior
        logger.info(f"Navigating to {config.FINES_URL}...")
        try:
            await human_behavior.human_like_navigation(page, config.FINES_URL, timeout=config.NAVIGATION_TIMEOUT)
            logger.info("Page loaded successfully")
            
            # Check for and solve CAPTCHA if present
            if config.ENABLE_CAPTCHA_SOLVING:
                logger.info("Checking for CAPTCHA...")
                captcha_solved = await detect_and_solve_captcha(page)
                if captcha_solved:
                    logger.info("CAPTCHA solved successfully")
                    # Wait a bit after solving
                    await asyncio.sleep(2.0)
                else:
                    logger.debug("No CAPTCHA found or solving not needed")
                    
        except Exception as e:
            logger.warning(f"Navigation timeout or error: {e}")
            logger.info("Continuing anyway - page may still be usable")
            # Give page additional time to render
            await asyncio.sleep(2.0)
        
        # Step 2: Wait for the vehicle list component to appear
        logger.info("Waiting for vehicle list component to load...")
        try:
            await page.wait_for_selector(
                "app-infracao-veiculo-lista",
                timeout=config.DEFAULT_TIMEOUT,
                state="visible"
            )
            logger.info("Vehicle list component found")
        except PlaywrightTimeoutError:
            logger.error("Vehicle list component (app-infracao-veiculo-lista) not found within timeout")
            raise
        
        # Step 3: Process all pages of vehicles
        await process_all_vehicle_pages(page)
        
        logger.info("Fine scraping process completed successfully")
        
    except Exception as e:
        logger.error(f"Error in getfines: {e}", exc_info=True)
        raise


async def process_all_vehicle_pages(page: Page) -> None:
    """
    Process all pages of the vehicle list, iterating through pagination.
    
    Args:
        page: Playwright Page object
    """
    page_number = 1
    
    while True:
        logger.info(f"Processing page {page_number} of vehicle list...")
        
        # Wait for vehicle list to be visible and loaded
        try:
            vehicle_list = await page.wait_for_selector(
                "app-infracao-veiculo-lista",
                timeout=config.DEFAULT_TIMEOUT,
                state="visible"
            )
        except PlaywrightTimeoutError:
            logger.error(f"Vehicle list not found on page {page_number}")
            break
        
        # Get all vehicle items within the list
        vehicle_items = await get_vehicle_items(page)
        
        if not vehicle_items:
            logger.info(f"No vehicles found on page {page_number}. End of list.")
            break
        
        logger.info(f"Found {len(vehicle_items)} vehicles on page {page_number}")
        
        # Process each vehicle on the current page
        for idx, vehicle_item in enumerate(vehicle_items, 1):
            logger.info(f"Processing vehicle {idx}/{len(vehicle_items)} on page {page_number}...")
            await process_vehicle(page, vehicle_item, page_number, idx)
        
        # Check if there's a next page
        has_next_page = await check_for_next_page(page)
        
        if not has_next_page:
            logger.info("No more pages to process")
            break
        
        # Navigate to next page
        logger.info("Navigating to next page...")
        
        # Longer delay before navigating to next page to avoid CAPTCHA triggers
        # (as per audit Section 7.3 - rapid navigation can trigger CAPTCHA)
        await human_behavior.random_delay(2000, 4000)  # 2-4 seconds
        
        await navigate_to_next_page(page)
        page_number += 1
        
        # Wait for the new page to load (lenient approach for SPAs)
        await wait_for_page_ready(page)
        
        # Check for CAPTCHA errors after navigation
        error_handled = await check_and_handle_captcha_error(page, "pagination navigation")
        if not error_handled:
            logger.error("CAPTCHA error detected and could not be resolved. Stopping pagination.")
            break
        
        # Simulate reading the new page
        await human_behavior.simulate_reading(page, 1.0, 2.0)


async def get_vehicle_items(page: Page) -> List:
    """
    Get all vehicle items from the current page's vehicle list.
    
    Based on DOM analysis, vehicle items have class 'card-list-item' and are clickable.
    
    Args:
        page: Playwright Page object
        
    Returns:
        List of Locator objects for vehicle items
    """
    try:
        # Wait for vehicle list container
        await page.wait_for_selector(
            "app-infracao-veiculo-lista",
            timeout=config.DEFAULT_TIMEOUT,
            state="visible"
        )
        
        # Wait for Angular to stabilize (as per audit Section 8.1)
        # Wait for network idle or at least for API calls to complete
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            # If networkidle times out, give Angular time to render
            logger.debug("Network idle timeout, giving Angular time to stabilize...")
            await asyncio.sleep(1.5)
        
        # Additional wait for Angular change detection to complete
        await asyncio.sleep(1.5)
        
        # Wait for dynamic content to load with human-like delay
        await human_behavior.simulate_reading(page, 1.0, 2.0)
        
        # Random scroll to simulate exploring the page
        if random.random() < 0.6:  # 60% chance to scroll
            await human_behavior.random_scroll(page, 1, 2)
        
        # Primary selector: Use class-based selector (more reliable than XPath with indices)
        # Based on DOM analysis, vehicle items have class 'card-list-item'
        vehicle_list_locator = page.locator("app-infracao-veiculo-lista")
        
        # Try class-based selector first (most reliable)
        primary_selector = "div.card-list-item"
        items_locator = vehicle_list_locator.locator(primary_selector)
        count = await items_locator.count()
        logger.info(f"Class-based selector '{primary_selector}' found {count} elements")
        
        # Validate and filter vehicle items
        vehicle_items = []
        for i in range(count):
            try:
                element = items_locator.nth(i)
                
                # Validate that this is actually a vehicle item
                # Check for clickability (vehicle items are clickable)
                is_clickable = await element.evaluate("""
                    el => {
                        const styles = window.getComputedStyle(el);
                        return styles.cursor === 'pointer' || 
                               el.onclick !== null || 
                               el.getAttribute('onclick') !== null;
                    }
                """)
                
                # Check for vehicle content (should have some text)
                text_content = await element.inner_text()
                has_content = len(text_content.strip()) > 10
                
                # Filter out pagination and other non-vehicle elements
                # Pagination typically has text like "Exibir:", "Página", etc.
                is_pagination = any(keyword in text_content.lower() for keyword in 
                                  ['exibir', 'página', 'página', 'itens', 'próximo', 'anterior'])
                
                if is_clickable and has_content and not is_pagination:
                    vehicle_items.append(element)
                    logger.debug(f"Validated vehicle item {len(vehicle_items)}: clickable={is_clickable}, has_content={has_content}")
                else:
                    logger.debug(f"Filtered out element {i}: clickable={is_clickable}, has_content={has_content}, is_pagination={is_pagination}")
                    
            except Exception as e:
                logger.warning(f"Error validating element {i}: {e}")
                continue
        
        if len(vehicle_items) > 0:
            logger.info(f"Found {len(vehicle_items)} validated vehicle items using class-based selector")
            return vehicle_items
        
        # Fallback: Try XPath selector if class-based selector didn't work
        logger.warning("Class-based selector didn't find valid vehicles, trying XPath fallback...")
        xpath_selector = "xpath=//app-infracao-veiculo-lista/form/div[3]/div[2]/div/div[1]"
        
        try:
            items_locator = page.locator(xpath_selector)
            count = await items_locator.count()
            logger.info(f"XPath selector found {count} elements")
            
            # Validate XPath results
            for i in range(count):
                try:
                    element = items_locator.nth(i)
                    class_name = await element.get_attribute("class") or ""
                    
                    # Only include elements with card-list-item class
                    if "card-list-item" in class_name:
                        vehicle_items.append(element)
                except Exception as e:
                    logger.warning(f"Error processing XPath element {i}: {e}")
                    continue
            
            if len(vehicle_items) > 0:
                logger.info(f"Found {len(vehicle_items)} vehicle items using XPath fallback")
                return vehicle_items
                
        except Exception as e:
            logger.warning(f"XPath selector failed: {e}")
        
        # Final fallback: Try CSS selector with structure pattern
        logger.warning("Trying CSS structure-based fallback...")
        items_locator = vehicle_list_locator.locator("form > div:nth-child(3) > div:nth-child(2) > div > div:first-child")
        count = await items_locator.count()
        logger.debug(f"CSS selector found {count} items")
        
        # Validate CSS results
        for i in range(count):
            try:
                element = items_locator.nth(i)
                class_name = await element.get_attribute("class") or ""
                is_clickable = await element.evaluate("""
                    el => {
                        const styles = window.getComputedStyle(el);
                        return styles.cursor === 'pointer';
                    }
                """)
                
                if "card-list-item" in class_name and is_clickable:
                    vehicle_items.append(element)
            except Exception:
                continue
        
        if not vehicle_items:
            logger.warning("No vehicle items found. The page structure may be different than expected.")
            logger.info("Please inspect the page and update the selectors in get_vehicle_items()")
        elif len(vehicle_items) < 9:
            logger.warning(f"Found only {len(vehicle_items)} vehicle items, expected 9. Some items may be missing.")
            logger.info("The selector may need adjustment. Check the page structure.")
        
        logger.info(f"Found {len(vehicle_items)} vehicle items")
        return vehicle_items
        
    except Exception as e:
        logger.error(f"Error getting vehicle items: {e}", exc_info=True)
        raise


async def process_vehicle(page: Page, vehicle_item, page_number: int, vehicle_index: int) -> None:
    """
    Process a single vehicle: open it and find fine elements.
    
    Args:
        page: Playwright Page object
        vehicle_item: Locator for the vehicle item
        page_number: Current page number (for logging)
        vehicle_index: Index of vehicle on current page (for logging)
    """
    try:
        logger.info(f"Opening vehicle {vehicle_index} from page {page_number}...")
        
        # Small random delay before clicking (simulating decision time)
        await human_behavior.random_delay(300, 800)
        
        # Click on the vehicle item with human-like behavior
        await human_behavior.human_like_click(page, vehicle_item, delay_before=False)
        
        # Wait for navigation to complete (lenient approach for SPAs)
        await wait_for_page_ready(page)
        
        # Check for CAPTCHA errors after navigation (before checking for visible CAPTCHA)
        error_handled = await check_and_handle_captcha_error(page, "vehicle navigation")
        if not error_handled:
            logger.warning("CAPTCHA error detected after vehicle click. Attempting to recover...")
            # Try to go back and skip this vehicle
            await go_back_to_vehicle_list(page)
            await asyncio.sleep(2.0)
            return
        
        # Check for and solve CAPTCHA if present (visible widget)
        if config.ENABLE_CAPTCHA_SOLVING:
            logger.info("Checking for visible CAPTCHA widget on vehicle page...")
            captcha_solved = await detect_and_solve_captcha(page)
            if captcha_solved:
                logger.info("CAPTCHA solved successfully")
                await asyncio.sleep(2.0)
        
        # Simulate reading the page after navigation
        await human_behavior.simulate_reading(page, 0.8, 1.5)
        
        # Wait for the vehicle details page to load
        # Wait for fine elements to appear (or check if we're on a page with fines)
        logger.info("Waiting for fine elements to load...")
        try:
            # Wait for fine elements with a reasonable timeout
            await page.wait_for_selector(
                "div.col-md-12.autuacao.border",
                timeout=config.DEFAULT_TIMEOUT,
                state="visible"
            )
            logger.info("Fine elements found")
        except PlaywrightTimeoutError:
            logger.warning(f"No fine elements found for vehicle {vehicle_index} on page {page_number}")
            logger.info("This vehicle may have no fines, or the page structure is different")
            # Go back to vehicle list
            await go_back_to_vehicle_list(page)
            return
        
        # Get all fine elements using locator API
        fine_locator = page.locator("div.col-md-12.autuacao.border")
        fine_count = await fine_locator.count()
        
        logger.info(f"Found {fine_count} fine(s) for vehicle {vehicle_index} on page {page_number}")
        
        # Print information about each fine (iteration logic only, no data extraction yet)
        for fine_idx in range(fine_count):
            logger.info(f"  Fine {fine_idx + 1}/{fine_count} found")
            # Get the specific fine element for future data extraction
            fine_element = fine_locator.nth(fine_idx)
            # TODO: Extract fine data in future implementation
            # Example: fine_data = await extract_fine_data(fine_element)
        
        # Small delay before going back
        await human_behavior.random_delay(400, 1000)
        
        # Go back to vehicle list with human-like behavior
        await go_back_to_vehicle_list(page)
        
        # Wait for vehicle list to be visible again
        await page.wait_for_selector(
            "app-infracao-veiculo-lista",
            timeout=config.DEFAULT_TIMEOUT,
            state="visible"
        )
        
        # Simulate reading the list again
        await human_behavior.simulate_reading(page, 0.5, 1.2)
        
        logger.info(f"Completed processing vehicle {vehicle_index} from page {page_number}")
        
    except Exception as e:
        logger.error(f"Error processing vehicle {vehicle_index} on page {page_number}: {e}", exc_info=True)
        # Try to recover by going back to vehicle list
        try:
            await go_back_to_vehicle_list(page)
        except Exception as recovery_error:
            logger.error(f"Failed to recover: {recovery_error}")
        raise


async def go_back_to_vehicle_list(page: Page) -> None:
    """
    Navigate back to the vehicle list page with human-like behavior.
    
    Args:
        page: Playwright Page object
    """
    try:
        # Use human-like back navigation
        await human_behavior.human_like_back_navigation(page)
        logger.debug("Navigated back using browser back button")
        
    except Exception as e:
        logger.warning(f"Error going back to vehicle list: {e}")
        # Alternative: navigate directly to FINES_URL with human-like behavior
        logger.info("Attempting direct navigation to vehicle list...")
        await human_behavior.human_like_navigation(page, config.FINES_URL)


async def check_for_next_page(page: Page) -> bool:
    """
    Check if there's a next page in the pagination.
    
    Uses multiple strategies:
    1. Check for Brazil Design System pagination component (br-pagination-table)
    2. Check pagination text (e.g., "1-9 de 11 itens" indicates more pages)
    3. Check for next button in various formats
    
    Args:
        page: Playwright Page object
    
    Returns:
        True if next page exists, False otherwise
    """
    try:
        # Strategy 1: Check pagination text to see if there are more items
        # Look for text like "1-9 de 11 itens" which indicates more pages exist
        try:
            pagination_text = await page.locator("br-pagination-table").inner_text()
            if pagination_text:
                # Extract numbers from text like "1-9 de 11 itens"
                match = re.search(r'(\d+)-(\d+)\s+de\s+(\d+)', pagination_text)
                if match:
                    start = int(match.group(1))
                    end = int(match.group(2))
                    total = int(match.group(3))
                    if end < total:
                        logger.info(f"Pagination text indicates more pages: {end} of {total} items shown")
                        return True
        except Exception:
            pass
        
        # Strategy 2: Check for Brazil Design System pagination next button
        # The br-pagination-table component may have specific selectors
        try:
            # Look for next button in br-pagination-table
            pagination_locator = page.locator("br-pagination-table")
            next_button = pagination_locator.locator("button:has-text('Próximo'), button[aria-label*='próximo' i]")
            if await next_button.count() > 0:
                is_disabled = await next_button.get_attribute("disabled")
                class_name = await next_button.get_attribute("class") or ""
                if is_disabled is None and "disabled" not in class_name.lower():
                    logger.info("Next page button found in br-pagination-table")
                    return True
        except Exception:
            pass
        
        # Strategy 3: Common pagination selectors (fallback)
        next_selectors = [
            "button:has-text('Próximo')",
            "button:has-text('Next')",
            "a:has-text('Próximo')",
            "a:has-text('Next')",
            "[aria-label*='próximo' i]",
            "[aria-label*='next' i]",
            ".pagination .next:not(.disabled)",
            ".pagination button.next:not([disabled])",
            "br-pagination-table button:has-text('Próximo')",
            "br-pagination-table [aria-label*='próximo' i]",
        ]
        
        for selector in next_selectors:
            try:
                next_button = await page.query_selector(selector)
                if next_button:
                    # Check if button is disabled
                    is_disabled = await next_button.get_attribute("disabled")
                    if is_disabled is None:
                        # Check for disabled class
                        class_name = await next_button.get_attribute("class") or ""
                        if "disabled" not in class_name.lower():
                            logger.info(f"Next page button found with selector: {selector}")
                            return True
            except Exception:
                continue
        
        logger.info("No next page found")
        return False
        
    except Exception as e:
        logger.warning(f"Error checking for next page: {e}")
        return False


async def navigate_to_next_page(page: Page) -> None:
    """
    Navigate to the next page of the vehicle list.
    
    Tries multiple strategies to find and click the next page button,
    prioritizing Brazil Design System pagination component.
    
    Args:
        page: Playwright Page object
    """
    try:
        # Strategy 1: Try Brazil Design System pagination component first
        # The next button has ID 'btn-next-page' and class 'br-button circle'
        try:
            # Try by ID first (most reliable)
            next_button_id = page.locator("#btn-next-page")
            if await next_button_id.count() > 0:
                is_disabled = await next_button_id.get_attribute("disabled")
                if is_disabled is None:
                    # Use human-like click
                    await human_behavior.human_like_click(page, next_button_id.first)
                    logger.info("Clicked next page button (btn-next-page)")
                    return
            
            # Try within br-pagination-table by ID
            pagination_locator = page.locator("br-pagination-table")
            if await pagination_locator.count() > 0:
                next_button_locator = pagination_locator.locator("#btn-next-page")
                if await next_button_locator.count() > 0:
                    is_disabled = await next_button_locator.get_attribute("disabled")
                    if is_disabled is None:
                        await human_behavior.human_like_click(page, next_button_locator.first)
                        logger.info("Clicked next page button in br-pagination-table (btn-next-page)")
                        return
                
                # Fallback: Look for button with chevron-right icon (next button indicator)
                next_button_with_icon = pagination_locator.locator("button.br-button.circle:has(i.fa-chevron-right)")
                if await next_button_with_icon.count() > 0:
                    is_disabled = await next_button_with_icon.get_attribute("disabled")
                    if is_disabled is None:
                        await human_behavior.human_like_click(page, next_button_with_icon.first)
                        logger.info("Clicked next page button (by icon)")
                        return
        except Exception as e:
            logger.debug(f"Strategy 1 failed: {e}")
            pass
        
        # Strategy 2: Common pagination selectors (fallback)
        next_selectors = [
            "#btn-next-page",  # Direct ID selector
            "button#btn-next-page",  # Button with ID
            "br-pagination-table #btn-next-page",  # Within pagination component
            "button.br-button.circle:has(i.fa-chevron-right)",  # Button with next icon
            "button:has-text('Próximo')",
            "button:has-text('Next')",
            "a:has-text('Próximo')",
            "a:has-text('Next')",
            "[aria-label*='próximo' i]",
            "[aria-label*='next' i]",
            ".pagination .next:not(.disabled)",
            ".pagination button.next:not([disabled])",
        ]
        
        for selector in next_selectors:
            try:
                next_button_locator = page.locator(selector)
                count = await next_button_locator.count()
                if count > 0:
                    # Check if button is disabled
                    is_disabled = await next_button_locator.get_attribute("disabled")
                    class_name = await next_button_locator.get_attribute("class") or ""
                    if is_disabled is None and "disabled" not in class_name.lower():
                        # Use human-like click
                        await human_behavior.human_like_click(page, next_button_locator.first)
                        logger.info(f"Clicked next page button with selector: {selector}")
                        return
            except Exception:
                continue
        
        raise Exception("Could not find or click next page button")
        
    except Exception as e:
        logger.error(f"Error navigating to next page: {e}", exc_info=True)
        raise

