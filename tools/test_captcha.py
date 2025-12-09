"""
Test script for CAPTCHA solving functionality.
This script tests the CAPTCHA detection and solving capabilities.

Usage:
    # Activate virtual environment first:
    # Windows: .\venv\Scripts\Activate.ps1
    # Linux/Mac: source venv/bin/activate
    
    python test_captcha.py
"""

import asyncio
import sys

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("ERROR: playwright not installed.")
    print("Please activate your virtual environment and install dependencies:")
    print("  .\\venv\\Scripts\\Activate.ps1  # Windows")
    print("  source venv/bin/activate       # Linux/Mac")
    print("  pip install -r requirements.txt")
    sys.exit(1)

try:
    import src.config as config
    from src.captcha_solver import detect_and_solve_captcha, CaptchaSolver
    from src.main import create_persistent_context
except ImportError as e:
    print(f"ERROR: Failed to import modules: {e}")
    print("Make sure you're in the project directory and virtual environment is activated")
    sys.exit(1)


async def test_captcha_detection():
    """Test CAPTCHA detection on a test page."""
    print("Testing CAPTCHA detection and solving...")
    print(f"API Key configured: {'Yes' if config.CAPTCHA_API_KEY else 'No'}")
    print(f"CAPTCHA solving enabled: {config.ENABLE_CAPTCHA_SOLVING}")
    print()
    
    if not config.CAPTCHA_API_KEY:
        print("ERROR: CAPTCHA_API_KEY not set in config or .env file")
        print("Please set your 2Captcha API key:")
        print("  - Add CAPTCHA_API_KEY=your_key_here to .env file")
        print("  - Or set it in config.py")
        print()
        print("Get your API key from: https://2captcha.com/?from=1234567")
        return False
    
    async with async_playwright() as playwright:
        try:
            # Create browser context
            context = await create_persistent_context(playwright)
            page = await context.new_page()
            
            print("Navigating to FINES_URL to test CAPTCHA detection...")
            await page.goto(config.FINES_URL, wait_until="domcontentloaded", timeout=30000)
            
            # Wait a bit for page to load
            await asyncio.sleep(2)
            
            # Check for CAPTCHA
            print("\nChecking for CAPTCHA on page...")
            recaptcha_v2 = await page.locator("iframe[src*='recaptcha']").count()
            recaptcha_v3 = await page.locator("[data-sitekey]").count()
            hcaptcha = await page.locator("iframe[src*='hcaptcha']").count()
            
            print(f"  reCAPTCHA v2 iframes found: {recaptcha_v2}")
            print(f"  reCAPTCHA v3 elements found: {recaptcha_v3}")
            print(f"  hCaptcha iframes found: {hcaptcha}")
            
            if recaptcha_v2 == 0 and recaptcha_v3 == 0 and hcaptcha == 0:
                print("\n✓ No CAPTCHA detected on this page")
                print("  (This is normal if CAPTCHA only appears under certain conditions)")
            else:
                print("\n⚠ CAPTCHA detected!")
                print("  Attempting to solve...")
                
                if config.ENABLE_CAPTCHA_SOLVING:
                    result = await detect_and_solve_captcha(page)
                    if result:
                        print("✓ CAPTCHA solved successfully!")
                        await asyncio.sleep(2)
                    else:
                        print("✗ Failed to solve CAPTCHA")
                        return False
                else:
                    print("  CAPTCHA solving is disabled in config")
            
            # Test API connection
            print("\nTesting 2Captcha API connection...")
            solver = CaptchaSolver(config.CAPTCHA_API_KEY)
            
            # Check balance (simple API test)
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    params = {
                        "key": config.CAPTCHA_API_KEY,
                        "action": "getbalance",
                        "json": 1,
                    }
                    async with session.get("https://2captcha.com/res.php", params=params) as response:
                        result = await response.json()
                        if result.get("status") == 1:
                            balance = result.get("request", "Unknown")
                            print(f"✓ API connection successful!")
                            print(f"  Account balance: ${balance}")
                        else:
                            error = result.get("request", "Unknown error")
                            print(f"✗ API error: {error}")
                            return False
            except ImportError:
                print("✗ aiohttp not installed. Run: pip install aiohttp")
                return False
            except Exception as e:
                print(f"✗ Error testing API: {e}")
                return False
            
            print("\n✓ All tests passed!")
            print("\nThe browser will stay open for 10 seconds so you can inspect the page...")
            await asyncio.sleep(10)
            
            await context.close()
            return True
            
        except Exception as e:
            print(f"\n✗ Error during testing: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return False


async def test_captcha_solver_class():
    """Test the CaptchaSolver class directly."""
    print("\n" + "="*50)
    print("Testing CaptchaSolver class...")
    
    if not config.CAPTCHA_API_KEY:
        print("Skipping - API key not configured")
        return
    
    solver = CaptchaSolver(config.CAPTCHA_API_KEY)
    print(f"Solver initialized with API key: {config.CAPTCHA_API_KEY[:10]}...")
    print("✓ CaptchaSolver class test passed")


def main():
    """Main test function."""
    print("="*50)
    print("CAPTCHA Solving Test Suite")
    print("="*50)
    print()
    
    try:
        # Test 1: Solver class
        asyncio.run(test_captcha_solver_class())
        
        # Test 2: Detection and solving
        result = asyncio.run(test_captcha_detection())
        
        if result:
            print("\n" + "="*50)
            print("✓ All tests completed successfully!")
            print("="*50)
            sys.exit(0)
        else:
            print("\n" + "="*50)
            print("✗ Some tests failed")
            print("="*50)
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

