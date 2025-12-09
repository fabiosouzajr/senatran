"""
Diagnostic script to analyze vehicle list DOM structure and selector issues.
This script helps identify why the current selector finds 22 elements instead of 9.

Run this script to inspect the actual DOM structure and find better selectors.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

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


async def analyze_dom_structure(page):
    """
    Analyze the DOM structure to understand what elements are being matched.
    
    Args:
        page: Playwright Page object
    """
    logger.info("=" * 80)
    logger.info("DOM STRUCTURE ANALYSIS")
    logger.info("=" * 80)
    
    # Wait for the vehicle list component
    logger.info("Waiting for vehicle list component...")
    await page.wait_for_selector(
        "app-infracao-veiculo-lista",
        timeout=config.DEFAULT_TIMEOUT,
        state="visible"
    )
    
    # Wait for Angular to stabilize
    await asyncio.sleep(2.0)
    logger.info("Component loaded, waiting for Angular to stabilize...")
    
    # Test current XPath selector
    xpath_selector = "xpath=//app-infracao-veiculo-lista/form/div[3]/div[2]/div/div[1]"
    logger.info(f"\nTesting current XPath selector: {xpath_selector}")
    
    items_locator = page.locator(xpath_selector)
    count = await items_locator.count()
    logger.info(f"Current selector found {count} elements")
    
    # Analyze each matched element
    logger.info("\n" + "=" * 80)
    logger.info("ANALYZING MATCHED ELEMENTS")
    logger.info("=" * 80)
    
    element_analysis = []
    
    for i in range(count):
        try:
            element = items_locator.nth(i)
            
            # Get element information
            tag_name = await element.evaluate("el => el.tagName")
            class_name = await element.get_attribute("class") or ""
            element_id = await element.get_attribute("id") or ""
            inner_text = await element.inner_text()
            inner_html = await element.inner_html()
            
            # Get parent information
            parent_info = await element.evaluate("""
                el => {
                    const parent = el.parentElement;
                    if (!parent) return null;
                    return {
                        tag: parent.tagName,
                        class: parent.className || '',
                        id: parent.id || '',
                        childrenCount: parent.children.length
                    };
                }
            """)
            
            # Get sibling information
            sibling_info = await element.evaluate("""
                el => {
                    const parent = el.parentElement;
                    if (!parent) return null;
                    return {
                        index: Array.from(parent.children).indexOf(el),
                        siblingsCount: parent.children.length
                    };
                }
            """)
            
            # Check for vehicle-specific content
            has_license_plate = any(keyword in inner_text.lower() for keyword in 
                                  ['placa', 'abc', 'def', 'ghi', 'jkl', 'mno', 'pqr', 'stu', 'vwx', 'yz'])
            has_vehicle_info = any(keyword in inner_text.lower() for keyword in 
                                  ['veículo', 'veiculo', 'modelo', 'marca', 'ano', 'chassi', 'renavam'])
            has_click_handler = await element.evaluate("""
                el => {
                    return el.onclick !== null || 
                           el.getAttribute('onclick') !== null ||
                           el.style.cursor === 'pointer' ||
                           window.getComputedStyle(el).cursor === 'pointer';
                }
            """)
            
            # Get computed styles that might indicate interactivity
            computed_styles = await element.evaluate("""
                el => {
                    const styles = window.getComputedStyle(el);
                    return {
                        cursor: styles.cursor,
                        display: styles.display,
                        position: styles.position,
                        zIndex: styles.zIndex
                    };
                }
            """)
            
            analysis = {
                "index": i,
                "tag": tag_name,
                "class": class_name,
                "id": element_id,
                "text_preview": inner_text[:100] if inner_text else "",
                "text_length": len(inner_text) if inner_text else 0,
                "html_preview": inner_html[:200] if inner_html else "",
                "parent": parent_info,
                "sibling": sibling_info,
                "has_license_plate": has_license_plate,
                "has_vehicle_info": has_vehicle_info,
                "has_click_handler": has_click_handler,
                "computed_styles": computed_styles
            }
            
            element_analysis.append(analysis)
            
            # Log summary for each element
            logger.info(f"\n--- Element {i + 1}/{count} ---")
            logger.info(f"Tag: {tag_name}, Class: {class_name}, ID: {element_id}")
            logger.info(f"Text length: {len(inner_text) if inner_text else 0} chars")
            logger.info(f"Text preview: {inner_text[:80] if inner_text else '(empty)'}")
            logger.info(f"Has license plate keywords: {has_license_plate}")
            logger.info(f"Has vehicle info keywords: {has_vehicle_info}")
            logger.info(f"Has click handler: {has_click_handler}")
            if parent_info:
                logger.info(f"Parent: {parent_info['tag']} (class: {parent_info['class']}, children: {parent_info['childrenCount']})")
            if sibling_info:
                logger.info(f"Sibling index: {sibling_info['index']}/{sibling_info['siblingsCount']}")
                
        except Exception as e:
            logger.error(f"Error analyzing element {i}: {e}")
            element_analysis.append({
                "index": i,
                "error": str(e)
            })
    
    # Analyze patterns
    logger.info("\n" + "=" * 80)
    logger.info("PATTERN ANALYSIS")
    logger.info("=" * 80)
    
    # Group elements by characteristics
    elements_with_vehicle_info = [e for e in element_analysis if e.get("has_vehicle_info")]
    elements_with_click_handler = [e for e in element_analysis if e.get("has_click_handler")]
    elements_with_text = [e for e in element_analysis if e.get("text_length", 0) > 10]
    
    logger.info(f"Elements with vehicle info keywords: {len(elements_with_vehicle_info)}")
    logger.info(f"Elements with click handlers: {len(elements_with_click_handler)}")
    logger.info(f"Elements with substantial text (>10 chars): {len(elements_with_text)}")
    
    # Find common patterns
    class_patterns = {}
    for e in element_analysis:
        if "class" in e and e["class"]:
            classes = e["class"].split()
            for cls in classes:
                class_patterns[cls] = class_patterns.get(cls, 0) + 1
    
    logger.info("\nMost common classes:")
    for cls, count in sorted(class_patterns.items(), key=lambda x: x[1], reverse=True)[:10]:
        logger.info(f"  .{cls}: {count} elements")
    
    # Check parent structure
    parent_structures = {}
    for e in element_analysis:
        if "parent" in e and e["parent"]:
            parent_key = f"{e['parent']['tag']}.{e['parent']['class']}"
            parent_structures[parent_key] = parent_structures.get(parent_key, 0) + 1
    
    logger.info("\nParent element patterns:")
    for parent, count in sorted(parent_structures.items(), key=lambda x: x[1], reverse=True)[:10]:
        logger.info(f"  {parent}: {count} elements")
    
    # Save detailed analysis to file
    output_file = Path(__file__).parent.parent / "vehicle_selector_analysis.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "total_elements": count,
            "expected_vehicles": 9,
            "elements": element_analysis,
            "patterns": {
                "class_frequency": class_patterns,
                "parent_structures": parent_structures,
                "elements_with_vehicle_info": len(elements_with_vehicle_info),
                "elements_with_click_handler": len(elements_with_click_handler),
                "elements_with_text": len(elements_with_text)
            }
        }, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\nDetailed analysis saved to: {output_file}")
    
    # Try alternative selectors
    logger.info("\n" + "=" * 80)
    logger.info("TESTING ALTERNATIVE SELECTORS")
    logger.info("=" * 80)
    
    alternative_selectors = [
        ("CSS: form > div:nth-child(3) > div:nth-child(2) > div > div:first-child",
         "app-infracao-veiculo-lista form > div:nth-child(3) > div:nth-child(2) > div > div:first-child"),
        ("CSS: form div:nth-child(3) div:nth-child(2) > div > div:first-child",
         "app-infracao-veiculo-lista form div:nth-child(3) div:nth-child(2) > div > div:first-child"),
        ("XPath: All clickable divs in form",
         "xpath=//app-infracao-veiculo-lista/form//div[@onclick or @role='button' or contains(@class, 'click')]"),
        ("XPath: Divs with vehicle-related text",
         "xpath=//app-infracao-veiculo-lista/form//div[contains(text(), 'Placa') or contains(text(), 'Veículo')]"),
    ]
    
    for name, selector in alternative_selectors:
        try:
            locator = page.locator(selector)
            alt_count = await locator.count()
            logger.info(f"{name}: {alt_count} elements")
        except Exception as e:
            logger.warning(f"{name}: Error - {e}")
    
    # Recommendations
    logger.info("\n" + "=" * 80)
    logger.info("RECOMMENDATIONS")
    logger.info("=" * 80)
    
    if count > 9:
        logger.warning(f"Current selector finds {count} elements but only 9 vehicles expected.")
        logger.info("Possible causes:")
        logger.info("  1. Selector matches nested divs within vehicle items")
        logger.info("  2. Selector matches non-vehicle structural elements")
        logger.info("  3. Selector is too broad")
        logger.info("\nSuggested fixes:")
        logger.info("  1. Look for elements with vehicle-specific content (license plates, vehicle info)")
        logger.info("  2. Look for clickable elements (onclick handlers, cursor: pointer)")
        logger.info("  3. Use more specific class names or data attributes")
        logger.info("  4. Filter results by text content or other characteristics")
    
    return element_analysis


async def main():
    """Main function to run the diagnostic."""
    logger.info("Starting vehicle selector diagnostic...")
    logger.info(f"Target URL: {config.FINES_URL}")
    logger.info(f"Browser: {config.BROWSER_TYPE} (headless: {config.BROWSER_HEADLESS})")
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
            
            # Run analysis
            analysis = await analyze_dom_structure(page)
            
            logger.info("\n" + "=" * 80)
            logger.info("Analysis complete!")
            logger.info("Review the output above and the JSON file for detailed information.")
            logger.info("=" * 80)
            
            # Keep browser open for manual inspection if not headless
            if not config.BROWSER_HEADLESS:
                logger.info("\nBrowser will remain open for 60 seconds for manual inspection...")
                logger.info("Press Ctrl+C to close early.")
                try:
                    await asyncio.sleep(60)
                except KeyboardInterrupt:
                    logger.info("Closing browser...")
            
        except Exception as e:
            logger.error(f"Error during analysis: {e}", exc_info=True)
            raise
        finally:
            await context.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nScript interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

