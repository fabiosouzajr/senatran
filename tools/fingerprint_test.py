"""
Fingerprint Testing Script
Tests browser fingerprint against anti-bot detection tools in headless mode.
Uses the same browser configuration as the main application.
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, BrowserContext, Page

import config
from stealth_helper import apply_comprehensive_stealth
from adblock_helper import setup_ublock_origin, get_adblock_extension_path
from headers_helper import get_enhanced_headers, apply_headers_to_context

# Test URLs for fingerprinting tools
FINGERPRINT_TOOLS = {
    "creepjs": "https://abrahamjuliot.github.io/creepjs/",
    "bot_sannysoft": "https://bot.sannysoft.com/",
    "pixelscan": "https://pixelscan.net/",
    "deviceinfo": "https://www.deviceinfo.me/",
}

# Output directory for test results
RESULTS_DIR = Path(__file__).parent / "fingerprint_test_results"
RESULTS_DIR.mkdir(exist_ok=True)


async def create_test_context(playwright) -> BrowserContext:
    """
    Create a browser context using the same settings as the main app.
    Forces headless mode for testing.
    """
    # Ensure user data directory exists
    test_user_data = config.USER_DATA_DIR.parent / ".playwright_test_data"
    test_user_data.mkdir(parents=True, exist_ok=True)
    
    # Browser type mapping
    browser_type_map = {
        "chromium": playwright.chromium,
        "firefox": playwright.firefox,
        "webkit": playwright.webkit,
    }
    
    if config.BROWSER_TYPE not in browser_type_map:
        browser_engine = playwright.chromium
    else:
        browser_engine = browser_type_map[config.BROWSER_TYPE]
    
    # Set up adblock extension if enabled and browser is Chromium
    browser_args = config.BROWSER_ARGS.copy()
    if config.ENABLE_ADBLOCK and config.BROWSER_TYPE == "chromium":
        try:
            extension_path = setup_ublock_origin()
            manifest_file = extension_path / "manifest.json"
            if extension_path.exists() and manifest_file.exists():
                browser_args.append(f"--load-extension={extension_path}")
        except Exception:
            pass  # Continue without adblock for testing
    
    # Create context with same settings as main app, but forced headless
    context = await browser_engine.launch_persistent_context(
        user_data_dir=str(test_user_data),
        headless=True,  # Force headless for testing
        args=browser_args,
        viewport={"width": config.VIEWPORT_WIDTH, "height": config.VIEWPORT_HEIGHT},
        user_agent=config.USER_AGENT,
        permissions=["geolocation", "notifications"],
        accept_downloads=True,
        locale="pt-BR",
        timezone_id="America/Sao_Paulo",
    )
    
    # Apply enhanced HTTP headers if enabled
    if config.ENABLE_ENHANCED_HEADERS:
        try:
            headers = get_enhanced_headers(
                locale="pt-BR",
                browser_type=config.BROWSER_TYPE,
                user_agent=config.USER_AGENT
            )
            apply_headers_to_context(context, headers)
        except Exception:
            pass  # Continue without enhanced headers for testing
    
    return context


async def extract_fingerprint_data(page: Page, tool_name: str) -> dict:
    """
    Extract fingerprint data from the page based on the tool.
    Returns a dictionary with extracted information.
    """
    results = {
        "tool": tool_name,
        "url": page.url,
        "timestamp": datetime.now().isoformat(),
    }
    
    try:
        # Wait for page to load
        await page.wait_for_load_state("networkidle", timeout=30000)
        await asyncio.sleep(3)  # Give tools time to analyze
        
        if tool_name == "creepjs":
            # CreepJS specific extraction
            results.update(await extract_creepjs_data(page))
        elif tool_name == "bot_sannysoft":
            # Bot.sannysoft.com specific extraction
            results.update(await extract_sannysoft_data(page))
        elif tool_name == "pixelscan":
            # Pixelscan.net specific extraction
            results.update(await extract_pixelscan_data(page))
        elif tool_name == "deviceinfo":
            # DeviceInfo.me specific extraction
            results.update(await extract_deviceinfo_data(page))
        
        # Take screenshot
        screenshot_path = RESULTS_DIR / f"{tool_name}_screenshot.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        results["screenshot"] = str(screenshot_path)
        
    except Exception as e:
        results["error"] = str(e)
        # Still take screenshot even on error
        try:
            screenshot_path = RESULTS_DIR / f"{tool_name}_screenshot.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            results["screenshot"] = str(screenshot_path)
        except:
            pass
    
    return results


async def extract_creepjs_data(page: Page) -> dict:
    """Extract data from CreepJS."""
    data = {}
    
    try:
        # CreepJS shows results in various elements
        # Look for key indicators
        page_content = await page.content()
        
        # Check for automation detection
        automation_detected = "webdriver" in page_content.lower() or "automation" in page_content.lower()
        data["automation_detected"] = automation_detected
        
        # Try to extract score or risk level
        score_elements = await page.query_selector_all(".score, .risk, .fingerprint")
        if score_elements:
            scores = []
            for elem in score_elements[:5]:  # Limit to first 5
                text = await elem.inner_text()
                if text:
                    scores.append(text.strip())
            data["scores"] = scores
        
        # Extract any visible warnings or flags
        warning_selectors = [
            ".warning", ".alert", ".danger", ".detected", 
            "[class*='bot']", "[class*='automation']"
        ]
        warnings = []
        for selector in warning_selectors:
            elements = await page.query_selector_all(selector)
            for elem in elements[:3]:  # Limit results
                text = await elem.inner_text()
                if text and len(text) < 200:  # Avoid huge text blocks
                    warnings.append(text.strip())
        data["warnings"] = warnings[:10]  # Limit to 10 warnings
        
    except Exception as e:
        data["extraction_error"] = str(e)
    
    return data


async def extract_sannysoft_data(page: Page) -> dict:
    """Extract data from bot.sannysoft.com."""
    data = {}
    
    try:
        # Wait for results table
        await page.wait_for_selector("table", timeout=10000)
        
        # Extract table data
        table_rows = await page.query_selector_all("table tr")
        test_results = {}
        
        for row in table_rows:
            try:
                cells = await row.query_selector_all("td, th")
                if len(cells) >= 2:
                    test_name = await cells[0].inner_text()
                    result = await cells[1].inner_text()
                    status = await cells[-1].inner_text() if len(cells) > 2 else ""
                    
                    test_results[test_name.strip()] = {
                        "result": result.strip(),
                        "status": status.strip()
                    }
            except:
                continue
        
        data["test_results"] = test_results
        
        # Check for failed tests (indicating detection)
        failed_tests = [
            name for name, result in test_results.items()
            if "fail" in result.get("status", "").lower() or 
               "detected" in result.get("status", "").lower() or
               "❌" in result.get("status", "") or
               "✗" in result.get("status", "")
        ]
        data["failed_tests"] = failed_tests
        data["detection_count"] = len(failed_tests)
        
    except Exception as e:
        data["extraction_error"] = str(e)
    
    return data


async def extract_pixelscan_data(page: Page) -> dict:
    """Extract data from pixelscan.net."""
    data = {}
    
    try:
        # Wait for results
        await asyncio.sleep(5)  # Pixelscan takes time to analyze
        
        # Look for risk score or detection indicators
        page_text = await page.inner_text("body")
        
        # Check for common detection terms
        detection_terms = ["bot", "automation", "headless", "webdriver", "suspicious", "risk"]
        found_terms = [term for term in detection_terms if term.lower() in page_text.lower()]
        data["detection_terms_found"] = found_terms
        
        # Try to find score or percentage
        score_elements = await page.query_selector_all(
            "[class*='score'], [class*='risk'], [class*='percentage'], "
            "[id*='score'], [id*='risk']"
        )
        scores = []
        for elem in score_elements[:5]:
            text = await elem.inner_text()
            if text:
                scores.append(text.strip())
        data["scores"] = scores
        
        # Extract any highlighted issues
        issue_selectors = [
            ".issue", ".problem", ".warning", ".alert",
            "[class*='detect']", "[class*='flag']"
        ]
        issues = []
        for selector in issue_selectors:
            elements = await page.query_selector_all(selector)
            for elem in elements[:3]:
                text = await elem.inner_text()
                if text and len(text) < 150:
                    issues.append(text.strip())
        data["issues"] = issues[:10]
        
    except Exception as e:
        data["extraction_error"] = str(e)
    
    return data


async def extract_deviceinfo_data(page: Page) -> dict:
    """Extract data from deviceinfo.me."""
    data = {}
    
    try:
        # Wait for page to load
        await page.wait_for_load_state("networkidle", timeout=15000)
        await asyncio.sleep(2)
        
        # DeviceInfo.me shows information in a structured format
        # Extract key information sections
        info_sections = {}
        
        # Look for common information sections
        section_selectors = [
            "h2", "h3", ".section", "[class*='info']", 
            "[class*='detail']", "strong"
        ]
        
        for selector in section_selectors:
            elements = await page.query_selector_all(selector)
            for elem in elements[:10]:  # Limit results
                try:
                    text = await elem.inner_text()
                    if text and 5 < len(text) < 100:
                        # Get following text/content
                        parent = await elem.evaluate_handle("el => el.parentElement")
                        if parent:
                            parent_text = await parent.as_element().inner_text() if hasattr(parent, 'as_element') else None
                            if parent_text and len(parent_text) < 300:
                                info_sections[text.strip()] = parent_text.strip()[:200]
                except:
                    continue
        
        data["info_sections"] = info_sections
        
        # Check for automation indicators
        page_text = await page.inner_text("body")
        automation_indicators = [
            "webdriver", "automation", "headless", "selenium", 
            "playwright", "puppeteer", "phantom"
        ]
        found_indicators = [
            ind for ind in automation_indicators 
            if ind.lower() in page_text.lower()
        ]
        data["automation_indicators"] = found_indicators
        
    except Exception as e:
        data["extraction_error"] = str(e)
    
    return data


async def test_fingerprint_tool(context: BrowserContext, tool_name: str, url: str) -> dict:
    """
    Test a single fingerprinting tool.
    """
    print(f"\n{'='*60}")
    print(f"Testing: {tool_name}")
    print(f"URL: {url}")
    print(f"{'='*60}")
    
    page = await context.new_page()
    
    try:
        # Apply comprehensive stealth (same as main app)
        stealth_applied = await apply_comprehensive_stealth(page, config.ENABLE_STEALTH)
        if stealth_applied:
            print("✓ Comprehensive stealth mode applied")
        else:
            print("⚠ Stealth mode not available")
        
        # Navigate to tool
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        # Extract data
        print("Extracting fingerprint data...")
        results = await extract_fingerprint_data(page, tool_name)
        
        print(f"✓ Completed testing {tool_name}")
        return results
        
    except Exception as e:
        print(f"✗ Error testing {tool_name}: {e}")
        return {
            "tool": tool_name,
            "url": url,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
    finally:
        await page.close()


async def run_fingerprint_tests():
    """
    Run fingerprint tests against all tools.
    """
    print("="*60)
    print("Fingerprint Testing Script")
    print("="*60)
    print(f"Browser: {config.BROWSER_TYPE}")
    print(f"Headless: True (forced for testing)")
    print(f"Viewport: {config.VIEWPORT_WIDTH}x{config.VIEWPORT_HEIGHT}")
    print(f"User Agent: {config.USER_AGENT or 'Default'}")
    print(f"Stealth: {config.ENABLE_STEALTH}")
    print(f"Results directory: {RESULTS_DIR}")
    print("="*60)
    
    all_results = {}
    
    async with async_playwright() as playwright:
        try:
            # Create context with same settings as main app
            context = await create_test_context(playwright)
            
            # Test each fingerprinting tool
            for tool_name, url in FINGERPRINT_TOOLS.items():
                try:
                    results = await test_fingerprint_tool(context, tool_name, url)
                    all_results[tool_name] = results
                    
                    # Small delay between tests
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    print(f"✗ Failed to test {tool_name}: {e}")
                    all_results[tool_name] = {
                        "tool": tool_name,
                        "url": url,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
            
            # Save results to JSON
            results_file = RESULTS_DIR / f"fingerprint_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(results_file, "w", encoding="utf-8") as f:
                json.dump(all_results, f, indent=2, ensure_ascii=False)
            
            print(f"\n{'='*60}")
            print("Testing completed!")
            print(f"Results saved to: {results_file}")
            print(f"{'='*60}\n")
            
            # Print summary
            print_summary(all_results)
            
        except Exception as e:
            print(f"Fatal error: {e}")
            raise
        finally:
            try:
                await context.close()
            except:
                pass


def print_summary(results: dict):
    """Print a summary of test results."""
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for tool_name, result in results.items():
        print(f"\n{tool_name.upper()}:")
        if "error" in result:
            print(f"  ✗ Error: {result['error']}")
        elif "detection_count" in result:
            print(f"  Detections: {result['detection_count']}")
            if result.get("failed_tests"):
                print(f"  Failed tests: {', '.join(result['failed_tests'][:5])}")
        elif "automation_detected" in result:
            print(f"  Automation detected: {result['automation_detected']}")
        elif "automation_indicators" in result:
            indicators = result.get("automation_indicators", [])
            print(f"  Automation indicators: {len(indicators)}")
            if indicators:
                print(f"    - {', '.join(indicators)}")
        else:
            print(f"  Status: Check screenshot and detailed results")


def main():
    """Entry point."""
    try:
        asyncio.run(run_fingerprint_tests())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
