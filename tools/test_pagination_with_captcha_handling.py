"""
Test script to verify pagination works correctly with CAPTCHA error handling.
Tests that the system can detect and handle CAPTCHA errors during pagination.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory and src directory to path to import modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from playwright.async_api import async_playwright
import config
import human_behavior
from fine_scrapper import (
    get_vehicle_items, 
    check_for_next_page, 
    navigate_to_next_page,
    check_and_handle_captcha_error
)
from rate_limit_handler import check_for_rate_limit_error

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


async def test_pagination_with_captcha_handling():
    """Test pagination with CAPTCHA error detection and handling."""
    logger.info("=" * 80)
    logger.info("TESTING PAGINATION WITH CAPTCHA ERROR HANDLING")
    logger.info("=" * 80)
    logger.info(f"Target URL: {config.FINES_URL}")
    logger.info("")
    
    async with async_playwright() as playwright:
        # Create browser context
        browser_type_map = {
            "chromium": playwright.chromium,
            "firefox": playwright.firefox,
            "webkit": playwright.webkit,
        }
        
        browser_engine = browser_type_map.get(config.BROWSER_TYPE, playwright.chromium)
        
        context = await browser_engine.launch_persistent_context(
            user_data_dir=str(config.USER_DATA_DIR),
            headless=config.BROWSER_HEADLESS,
            args=config.BROWSER_ARGS,
            viewport={"width": config.VIEWPORT_WIDTH, "height": config.VIEWPORT_HEIGHT},
            user_agent=config.USER_AGENT,
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
        )
        
        try:
            page = await context.new_page()
            
            # Navigate to vehicle list
            logger.info(f"Navigating to {config.FINES_URL}...")
            await human_behavior.human_like_navigation(page, config.FINES_URL, timeout=config.NAVIGATION_TIMEOUT)
            
            # Wait for page to load
            await asyncio.sleep(2.0)
            
            total_vehicles_found = 0
            page_number = 1
            max_pages = 10  # Safety limit
            captcha_errors_detected = 0
            captcha_errors_handled = 0
            
            while page_number <= max_pages:
                logger.info("\n" + "=" * 80)
                logger.info(f"PAGE {page_number}")
                logger.info("=" * 80)
                
                # Get vehicles on current page
                vehicle_items = await get_vehicle_items(page)
                
                if not vehicle_items:
                    logger.info(f"No vehicles found on page {page_number}. End of list.")
                    break
                
                logger.info(f"Found {len(vehicle_items)} vehicles on page {page_number}")
                total_vehicles_found += len(vehicle_items)
                
                # Display first vehicle as sample
                if vehicle_items:
                    try:
                        first_vehicle_text = await vehicle_items[0].inner_text()
                        logger.info(f"Sample vehicle: {first_vehicle_text[:60].replace(chr(10), ' | ')}")
                    except Exception as e:
                        logger.debug(f"Could not get sample vehicle text: {e}")
                
                # Check for next page
                logger.info("\nChecking for next page...")
                has_next = await check_for_next_page(page)
                
                if not has_next:
                    logger.info("No more pages available.")
                    break
                
                logger.info("Next page available. Preparing to navigate...")
                
                # Check for any existing errors before navigation
                logger.info("Checking for CAPTCHA errors before navigation...")
                error_before = await check_for_rate_limit_error(page)
                
                if error_before and "captcha" in error_before.lower():
                    captcha_errors_detected += 1
                    logger.warning(f"⚠️  CAPTCHA error detected before navigation: {error_before}")
                    
                    # Test the error handling function
                    logger.info("Attempting to handle CAPTCHA error before navigation...")
                    error_handled = await check_and_handle_captcha_error(page, f"before pagination to page {page_number + 1}")
                    
                    if error_handled:
                        captcha_errors_handled += 1
                        logger.info("✅ CAPTCHA error was handled successfully before navigation")
                        
                        # Verify error is gone
                        error_after_handling = await check_for_rate_limit_error(page)
                        if error_after_handling and "captcha" in error_after_handling.lower():
                            logger.warning(f"⚠️  Error still present after handling: {error_after_handling}")
                        else:
                            logger.info("✅ Error cleared after handling")
                        
                        # Wait a bit more after handling error
                        await asyncio.sleep(2.0)
                    else:
                        logger.error("❌ Failed to handle CAPTCHA error before navigation")
                        logger.error("Stopping pagination due to unresolved CAPTCHA error")
                        break
                else:
                    logger.info("✅ No CAPTCHA errors detected before navigation")
                
                # Navigate to next page with longer delay (as per implementation)
                logger.info("Waiting before navigation (2-4 seconds to reduce CAPTCHA triggers)...")
                await human_behavior.random_delay(2000, 4000)
                
                logger.info("Clicking next page button...")
                await navigate_to_next_page(page)
                
                # Wait for navigation to complete
                await asyncio.sleep(2.0)
                
                # Check for CAPTCHA errors after navigation
                logger.info("\nChecking for CAPTCHA errors after navigation...")
                error_after = await check_for_rate_limit_error(page)
                
                if error_after and "captcha" in error_after.lower():
                    captcha_errors_detected += 1
                    logger.warning(f"⚠️  CAPTCHA error detected after navigation: {error_after}")
                    
                    # Test the error handling function
                    logger.info("Attempting to handle CAPTCHA error after navigation...")
                    error_handled = await check_and_handle_captcha_error(page, f"pagination to page {page_number + 1}")
                    
                    if error_handled:
                        captcha_errors_handled += 1
                        logger.info("✅ CAPTCHA error was handled successfully after navigation")
                        
                        # Verify error is gone
                        error_after_handling = await check_for_rate_limit_error(page)
                        if error_after_handling and "captcha" in error_after_handling.lower():
                            logger.warning(f"⚠️  Error still present after handling: {error_after_handling}")
                        else:
                            logger.info("✅ Error cleared after handling")
                    else:
                        logger.error("❌ Failed to handle CAPTCHA error after navigation")
                        logger.error("Stopping pagination due to unresolved CAPTCHA error")
                        break
                else:
                    logger.info("✅ No CAPTCHA errors detected after navigation")
                
                # Wait for new page to fully load
                await asyncio.sleep(2.0)
                
                page_number += 1
            
            # Summary
            logger.info("\n" + "=" * 80)
            logger.info("PAGINATION WITH CAPTCHA HANDLING TEST SUMMARY")
            logger.info("=" * 80)
            logger.info(f"Total pages processed: {page_number}")
            logger.info(f"Total vehicles found: {total_vehicles_found}")
            logger.info(f"CAPTCHA errors detected: {captcha_errors_detected}")
            logger.info(f"CAPTCHA errors handled: {captcha_errors_handled}")
            
            if captcha_errors_detected > 0:
                if captcha_errors_handled == captcha_errors_detected:
                    logger.info("✅ SUCCESS: All CAPTCHA errors were handled successfully!")
                else:
                    logger.warning(f"⚠️  WARNING: {captcha_errors_detected - captcha_errors_handled} CAPTCHA error(s) could not be handled")
            else:
                logger.info("✅ No CAPTCHA errors encountered during pagination")
            
            if page_number > 1:
                logger.info("✅ SUCCESS: Pagination navigation is working correctly!")
                logger.info(f"   Successfully navigated through {page_number} page(s)")
            else:
                logger.warning("⚠️  Only one page found. Either:")
                logger.warning("   1. There is only one page of vehicles")
                logger.warning("   2. Pagination detection is not working")
            
            # Test results
            test_passed = (
                page_number > 1 and  # Successfully navigated through pages
                (captcha_errors_detected == 0 or captcha_errors_handled == captcha_errors_detected)  # All errors handled
            )
            
            if test_passed:
                logger.info("\n" + "=" * 80)
                logger.info("✅ OVERALL TEST RESULT: PASSED")
                logger.info("=" * 80)
            else:
                logger.warning("\n" + "=" * 80)
                logger.warning("⚠️  OVERALL TEST RESULT: NEEDS ATTENTION")
                logger.warning("=" * 80)
            
            # Keep browser open for manual inspection if not headless
            if not config.BROWSER_HEADLESS:
                logger.info("\nBrowser will remain open for 30 seconds for manual inspection...")
                logger.info("Press Ctrl+C to close early.")
                try:
                    await asyncio.sleep(30)
                except KeyboardInterrupt:
                    logger.info("Closing browser...")
            
            return test_passed
            
        except Exception as e:
            logger.error(f"Error during pagination test: {e}", exc_info=True)
            raise
        finally:
            await context.close()


async def main():
    """Main function to run the test."""
    try:
        success = await test_pagination_with_captcha_handling()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

