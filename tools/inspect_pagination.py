"""
Diagnostic script to inspect pagination component structure.
Helps identify the correct selector for the next page button.
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
import src.config as config
import src.human_behavior as human_behavior

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


async def inspect_pagination(page):
    """Inspect the pagination component structure."""
    logger.info("=" * 80)
    logger.info("INSPECTING PAGINATION COMPONENT")
    logger.info("=" * 80)
    
    # Wait for pagination component
    await asyncio.sleep(5.0)
    await page.wait_for_selector("br-pagination-table", timeout=10000, state="visible")
    await asyncio.sleep(2.0)
    
    # Get pagination HTML
    pagination_html = await page.locator("br-pagination-table").inner_html()
    logger.info("\nPagination HTML:")
    logger.info(pagination_html[:500])
    
    # Get pagination text
    pagination_text = await page.locator("br-pagination-table").inner_text()
    logger.info(f"\nPagination text: {pagination_text}")
    
    # Try to find all buttons in pagination
    logger.info("\n" + "=" * 80)
    logger.info("SEARCHING FOR BUTTONS")
    logger.info("=" * 80)
    
    button_selectors = [
        "br-pagination-table button",
        "br-pagination-table button:has-text('Próximo')",
        "br-pagination-table button:has-text('Next')",
        "br-pagination-table [aria-label*='próximo' i]",
        "br-pagination-table [aria-label*='next' i]",
        "br-pagination-table a",
        "br-pagination-table [role='button']",
    ]
    
    for selector in button_selectors:
        try:
            buttons = page.locator(selector)
            count = await buttons.count()
            logger.info(f"\nSelector: {selector}")
            logger.info(f"  Found {count} elements")
            
            for i in range(min(count, 5)):  # Show first 5
                try:
                    button = buttons.nth(i)
                    text = await button.inner_text()
                    aria_label = await button.get_attribute("aria-label") or ""
                    class_name = await button.get_attribute("class") or ""
                    is_disabled = await button.get_attribute("disabled")
                    tag = await button.evaluate("el => el.tagName")
                    
                    logger.info(f"  Button {i+1}:")
                    logger.info(f"    Tag: {tag}")
                    logger.info(f"    Text: {text}")
                    logger.info(f"    Aria-label: {aria_label}")
                    logger.info(f"    Class: {class_name}")
                    logger.info(f"    Disabled: {is_disabled}")
                except Exception as e:
                    logger.warning(f"    Error inspecting button {i+1}: {e}")
        except Exception as e:
            logger.warning(f"Selector '{selector}' failed: {e}")
    
    # Try to find clickable elements
    logger.info("\n" + "=" * 80)
    logger.info("SEARCHING FOR CLICKABLE ELEMENTS")
    logger.info("=" * 80)
    
    clickable_elements = await page.evaluate("""
        () => {
            const pagination = document.querySelector('br-pagination-table');
            if (!pagination) return [];
            
            const allElements = pagination.querySelectorAll('*');
            const clickable = [];
            
            allElements.forEach(el => {
                const styles = window.getComputedStyle(el);
                const isClickable = 
                    styles.cursor === 'pointer' ||
                    el.onclick !== null ||
                    el.getAttribute('onclick') !== null ||
                    el.tagName === 'BUTTON' ||
                    el.tagName === 'A' ||
                    el.getAttribute('role') === 'button';
                
                if (isClickable) {
                    clickable.push({
                        tag: el.tagName,
                        text: el.innerText?.substring(0, 50) || '',
                        class: el.className || '',
                        id: el.id || '',
                        ariaLabel: el.getAttribute('aria-label') || '',
                        disabled: el.disabled || el.getAttribute('disabled') || false
                    });
                }
            });
            
            return clickable;
        }
    """)
    
    logger.info(f"Found {len(clickable_elements)} clickable elements:")
    for i, elem in enumerate(clickable_elements[:10], 1):  # Show first 10
        logger.info(f"\n  Element {i}:")
        logger.info(f"    Tag: {elem['tag']}")
        logger.info(f"    Text: {elem['text']}")
        logger.info(f"    Class: {elem['class']}")
        logger.info(f"    ID: {elem['id']}")
        logger.info(f"    Aria-label: {elem['ariaLabel']}")
        logger.info(f"    Disabled: {elem['disabled']}")
    
    # Try to find elements with "próximo" or "next" text
    logger.info("\n" + "=" * 80)
    logger.info("SEARCHING FOR 'PRÓXIMO' OR 'NEXT' TEXT")
    logger.info("=" * 80)
    
    next_elements = await page.evaluate("""
        () => {
            const pagination = document.querySelector('br-pagination-table');
            if (!pagination) return [];
            
            const allElements = pagination.querySelectorAll('*');
            const matches = [];
            
            allElements.forEach(el => {
                const text = el.innerText?.toLowerCase() || '';
                if (text.includes('próximo') || text.includes('next') || 
                    el.getAttribute('aria-label')?.toLowerCase().includes('próximo') ||
                    el.getAttribute('aria-label')?.toLowerCase().includes('next')) {
                    matches.push({
                        tag: el.tagName,
                        text: el.innerText?.substring(0, 50) || '',
                        class: el.className || '',
                        ariaLabel: el.getAttribute('aria-label') || '',
                        disabled: el.disabled || el.getAttribute('disabled') || false,
                        html: el.outerHTML.substring(0, 200)
                    });
                }
            });
            
            return matches;
        }
    """)
    
    logger.info(f"Found {len(next_elements)} elements with 'próximo' or 'next':")
    for i, elem in enumerate(next_elements, 1):
        logger.info(f"\n  Element {i}:")
        logger.info(f"    Tag: {elem['tag']}")
        logger.info(f"    Text: {elem['text']}")
        logger.info(f"    Class: {elem['class']}")
        logger.info(f"    Aria-label: {elem['ariaLabel']}")
        logger.info(f"    Disabled: {elem['disabled']}")
        logger.info(f"    HTML: {elem['html']}")


async def main():
    """Main function."""
    logger.info("Starting pagination inspection...")
    logger.info(f"Target URL: {config.FINES_URL}")
    logger.info("")
    
    async with async_playwright() as playwright:
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
            
            logger.info(f"Navigating to {config.FINES_URL}...")
            await human_behavior.human_like_navigation(page, config.FINES_URL, timeout=config.NAVIGATION_TIMEOUT)
            
            await asyncio.sleep(2.0)
            
            await inspect_pagination(page)
            
            logger.info("\n" + "=" * 80)
            logger.info("Inspection complete!")
            logger.info("=" * 80)
            
            if not config.BROWSER_HEADLESS:
                logger.info("\nBrowser will remain open for 60 seconds for manual inspection...")
                logger.info("Press Ctrl+C to close early.")
                try:
                    await asyncio.sleep(60)
                except KeyboardInterrupt:
                    logger.info("Closing browser...")
            
        except Exception as e:
            logger.error(f"Error during inspection: {e}", exc_info=True)
            raise
        finally:
            await context.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nInspection interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

