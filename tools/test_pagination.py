"""
Test script to verify pagination detection and navigation.
Tests that the system can detect and navigate through multiple pages of vehicles.
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
from fine_scrapper import get_vehicle_items, check_for_next_page, navigate_to_next_page

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


async def test_pagination():
    """Test pagination detection and navigation."""
    logger.info("=" * 80)
    logger.info("TESTING PAGINATION")
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
                
                logger.info("Next page available. Navigating...")
                
                # Navigate to next page
                await human_behavior.random_delay(500, 1500)
                await navigate_to_next_page(page)
                
                # Wait for new page to load
                await asyncio.sleep(2.0)
                
                page_number += 1
            
            # Summary
            logger.info("\n" + "=" * 80)
            logger.info("PAGINATION TEST SUMMARY")
            logger.info("=" * 80)
            logger.info(f"Total pages processed: {page_number}")
            logger.info(f"Total vehicles found: {total_vehicles_found}")
            
            if page_number > 1:
                logger.info("✅ SUCCESS: Pagination is working correctly!")
                logger.info(f"   Successfully navigated through {page_number} page(s)")
            else:
                logger.warning("⚠️  Only one page found. Either:")
                logger.warning("   1. There is only one page of vehicles")
                logger.warning("   2. Pagination detection is not working")
            
            # Keep browser open for manual inspection if not headless
            if not config.BROWSER_HEADLESS:
                logger.info("\nBrowser will remain open for 30 seconds for manual inspection...")
                logger.info("Press Ctrl+C to close early.")
                try:
                    await asyncio.sleep(30)
                except KeyboardInterrupt:
                    logger.info("Closing browser...")
            
            return page_number > 1
            
        except Exception as e:
            logger.error(f"Error during pagination test: {e}", exc_info=True)
            raise
        finally:
            await context.close()


async def main():
    """Main function to run the test."""
    try:
        success = await test_pagination()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

