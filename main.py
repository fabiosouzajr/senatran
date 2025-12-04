"""
Main script for Playwright browser automation.
Opens a browser window, navigates to a configured URL, and waits for user input.
"""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright, BrowserContext, Page

import config


async def create_persistent_context(playwright) -> BrowserContext:
    """
    Create a persistent browser context for cookies, cache, and plugins.
    
    Returns:
        BrowserContext instance with persistent storage
    """
    # Ensure user data directory exists
    config.USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Launch browser based on configuration
    browser_type_map = {
        "chromium": playwright.chromium,
        "firefox": playwright.firefox,
        "webkit": playwright.webkit,
    }
    
    if config.BROWSER_TYPE not in browser_type_map:
        print(f"Warning: Unknown browser type '{config.BROWSER_TYPE}'. Using chromium.")
        browser_engine = playwright.chromium
    else:
        browser_engine = browser_type_map[config.BROWSER_TYPE]
    
    # Launch browser with persistent context
    # This ensures cookies, cache, and plugins persist across sessions
    # launch_persistent_context() is the correct way to create a persistent context
    # In headed mode, the browser window is resizable by default
    context = await browser_engine.launch_persistent_context(
        user_data_dir=str(config.USER_DATA_DIR),
        headless=config.BROWSER_HEADLESS,
        args=config.BROWSER_ARGS,
        viewport={"width": config.VIEWPORT_WIDTH, "height": config.VIEWPORT_HEIGHT},
        user_agent=config.USER_AGENT,
        # Enable plugins and normal browser features
        permissions=["geolocation", "notifications"],
        # Accept downloads automatically
        accept_downloads=True,
    )
    
    return context


async def open_browser_and_wait():
    """
    Main function that opens the browser, navigates to the URL, and waits for user input.
    """
    print(f"Initializing {config.BROWSER_TYPE} browser...")
    print(f"Target URL: {config.TARGET_URL}")
    print(f"User data directory: {config.USER_DATA_DIR}")
    print(f"Headless mode: {config.BROWSER_HEADLESS}")
    print()
    
    async with async_playwright() as playwright:
        try:
            # Create persistent context (this also launches the browser)
            context = await create_persistent_context(playwright)
            
            # Create a new page
            page: Page = await context.new_page()
            
            # Navigate to the target URL
            print(f"Navigating to {config.TARGET_URL}...")
            await page.goto(
                config.TARGET_URL,
                wait_until="domcontentloaded",
                timeout=config.NAVIGATION_TIMEOUT,
            )
            
            print(f"\n{config.WAIT_MESSAGE}")
            print("Browser is ready. You can interact with it now.")
            print("Press Enter to continue with further automation...")
            
            # Wait for user input (Enter key)
            # This is a blocking call that waits for Enter in the terminal
            input()
            
            print("\nContinuing with automation...")
            print("Browser will remain open. Add your automation code here.")
            
            # Keep the browser open for further automation
            # You can add your automation code here
            # For now, we'll keep it running until manually closed
            
            # Wait indefinitely (or until browser is closed)
            # In a real scenario, you'd add your automation logic here
            print("Browser is running. Close the browser window or press Ctrl+C to exit.")
            
            # Keep the script running
            try:
                await asyncio.sleep(3600)  # Wait for 1 hour (or until interrupted)
            except KeyboardInterrupt:
                print("\nShutting down...")
            
        except Exception as e:
            print(f"Error occurred: {e}", file=sys.stderr)
            raise
        finally:
            # Clean up
            try:
                await context.close()
                print("Browser closed.")
            except:
                pass


def main():
    """Entry point for the script."""
    try:
        asyncio.run(open_browser_and_wait())
    except KeyboardInterrupt:
        print("\nScript interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

