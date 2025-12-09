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
import sys
from typing import List
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

import config
import human_behavior
from captcha_solver import detect_and_solve_captcha

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
        
        # Random delay before navigating to next page
        await human_behavior.random_delay(500, 1500)
        
        await navigate_to_next_page(page)
        page_number += 1
        
        # Wait for the new page to load (lenient approach for SPAs)
        await wait_for_page_ready(page)
        
        # Simulate reading the new page
        await human_behavior.simulate_reading(page, 1.0, 2.0)


async def get_vehicle_items(page: Page) -> List:
    """
    Get all vehicle items from the current page's vehicle list.
    
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
        
        # Wait for dynamic content to load with human-like delay
        await human_behavior.simulate_reading(page, 1.0, 2.0)
        
        # Random scroll to simulate exploring the page
        if random.random() < 0.6:  # 60% chance to scroll
            await human_behavior.random_scroll(page, 1, 2)
        
        # Use XPath based on the provided structure
        # XPath for first vehicle: /html/body/.../app-infracao-veiculo-lista/form/div[3]/div[2]/div[1]/div[1]
        # Pattern: form/div[3]/div[2]/div[*]/div[1] - vehicles are in nested divs
        # Each vehicle is at: form/div[3]/div[2]/div[N]/div[1] where N is the vehicle index
        
        # Use XPath to find all vehicle items
        # XPath: //app-infracao-veiculo-lista/form/div[3]/div[2]/div/div[1]
        # This finds all div[1] elements that are children of div elements under form/div[3]/div[2]
        xpath_selector = "xpath=//app-infracao-veiculo-lista/form/div[3]/div[2]/div/div[1]"
        
        try:
            # Use XPath locator to find all vehicles
            items_locator = page.locator(xpath_selector)
            count = await items_locator.count()
            logger.info(f"XPath selector found {count} vehicle items")
            
            if count >= 9:
                # Create list of locators using nth()
                vehicle_items = [items_locator.nth(i) for i in range(count)]
                logger.info(f"Successfully found {len(vehicle_items)} vehicle items using XPath")
                return vehicle_items
            else:
                logger.warning(f"XPath found only {count} items, expected 9. Trying alternative approach...")
        except Exception as e:
            logger.warning(f"XPath selector failed: {e}. Trying alternative approach...")
        
        # Fallback: Use CSS selector with the structure pattern
        vehicle_list_locator = page.locator("app-infracao-veiculo-lista")
        items_locator = vehicle_list_locator.locator("form > div:nth-child(3) > div:nth-child(2) > div > div:first-child")
        
        count = await items_locator.count()
        logger.debug(f"CSS selector found {count} items")
        
        if count < 9:
            # Try alternative CSS selectors based on the structure
            alternative_selectors = [
                "form div:nth-child(3) div:nth-child(2) > div > div:first-child",
                "form > div:nth-of-type(3) > div:nth-of-type(2) > div > div:first-child",
            ]
            
            for selector in alternative_selectors:
                test_locator = vehicle_list_locator.locator(selector)
                test_count = await test_locator.count()
                logger.debug(f"Alternative selector '{selector}' found {test_count} items")
                if test_count >= 9:
                    items_locator = test_locator
                    count = test_count
                    break
        
        # Create list of locators using nth()
        vehicle_items = [items_locator.nth(i) for i in range(count)]
        
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
        
        # Check for and solve CAPTCHA if present
        if config.ENABLE_CAPTCHA_SOLVING:
            logger.info("Checking for CAPTCHA on vehicle page...")
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
    
    Args:
        page: Playwright Page object
        
    Returns:
        True if next page exists, False otherwise
    """
    try:
        # Common pagination selectors
        next_selectors = [
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
                next_button = await page.query_selector(selector)
                if next_button:
                    # Check if button is disabled
                    is_disabled = await next_button.get_attribute("disabled")
                    if is_disabled is None:
                        # Check for disabled class
                        class_name = await next_button.get_attribute("class") or ""
                        if "disabled" not in class_name.lower():
                            logger.info("Next page button found and enabled")
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
    
    Args:
        page: Playwright Page object
    """
    try:
        # Try to find and click next button
        next_selectors = [
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
                        logger.info("Clicked next page button")
                        return
            except Exception:
                continue
        
        raise Exception("Could not find or click next page button")
        
    except Exception as e:
        logger.error(f"Error navigating to next page: {e}", exc_info=True)
        raise

