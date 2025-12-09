"""
Test script to verify vehicle count detection fix.
Tests the updated get_vehicle_items() function to ensure it correctly identifies 9 vehicles.
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
from fine_scrapper import get_vehicle_items

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


async def test_vehicle_detection():
    """Test the vehicle detection functionality."""
    logger.info("=" * 80)
    logger.info("TESTING VEHICLE DETECTION")
    logger.info("=" * 80)
    logger.info(f"Target URL: {config.FINES_URL}")
    logger.info(f"Expected vehicles: 9")
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
            
            # Wait a bit for page to fully load
            await asyncio.sleep(2.0)
            
            logger.info("\n" + "=" * 80)
            logger.info("CALLING get_vehicle_items()")
            logger.info("=" * 80)
            
            # Test the vehicle detection function
            vehicle_items = await get_vehicle_items(page)
            
            logger.info("\n" + "=" * 80)
            logger.info("TEST RESULTS")
            logger.info("=" * 80)
            logger.info(f"Total vehicles found: {len(vehicle_items)}")
            logger.info(f"Expected: 9")
            
            if len(vehicle_items) == 9:
                logger.info("✅ SUCCESS: Found exactly 9 vehicles!")
            elif len(vehicle_items) > 9:
                logger.warning(f"⚠️  WARNING: Found {len(vehicle_items)} vehicles, expected 9. Some false positives may be included.")
            else:
                logger.warning(f"⚠️  WARNING: Found only {len(vehicle_items)} vehicles, expected 9. Some vehicles may be missing.")
            
            # Display details about each vehicle
            logger.info("\n" + "=" * 80)
            logger.info("VEHICLE DETAILS")
            logger.info("=" * 80)
            
            for i, vehicle_item in enumerate(vehicle_items, 1):
                try:
                    # Get vehicle information
                    class_name = await vehicle_item.get_attribute("class") or ""
                    text_content = await vehicle_item.inner_text()
                    text_preview = text_content[:80].replace("\n", " | ") if text_content else "(empty)"
                    
                    # Check if clickable
                    is_clickable = await vehicle_item.evaluate("""
                        el => {
                            const styles = window.getComputedStyle(el);
                            return styles.cursor === 'pointer';
                        }
                    """)
                    
                    logger.info(f"\nVehicle {i}/{len(vehicle_items)}:")
                    logger.info(f"  Class: {class_name}")
                    logger.info(f"  Clickable: {is_clickable}")
                    logger.info(f"  Text preview: {text_preview}")
                    
                except Exception as e:
                    logger.error(f"Error getting details for vehicle {i}: {e}")
            
            # Summary
            logger.info("\n" + "=" * 80)
            logger.info("SUMMARY")
            logger.info("=" * 80)
            
            if len(vehicle_items) == 9:
                logger.info("✅ Test PASSED: Vehicle detection is working correctly!")
                logger.info("   All 9 vehicles were identified successfully.")
            else:
                logger.warning("⚠️  Test needs attention:")
                logger.warning(f"   Found {len(vehicle_items)} vehicles instead of 9.")
                logger.warning("   Review the selector and validation logic.")
            
            # Keep browser open for manual inspection if not headless
            if not config.BROWSER_HEADLESS:
                logger.info("\n" + "=" * 80)
                logger.info("Browser will remain open for 30 seconds for manual inspection...")
                logger.info("Press Ctrl+C to close early.")
                try:
                    await asyncio.sleep(30)
                except KeyboardInterrupt:
                    logger.info("Closing browser...")
            
            return len(vehicle_items) == 9
            
        except Exception as e:
            logger.error(f"Error during test: {e}", exc_info=True)
            raise
        finally:
            await context.close()


async def main():
    """Main function to run the test."""
    try:
        success = await test_vehicle_detection()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

