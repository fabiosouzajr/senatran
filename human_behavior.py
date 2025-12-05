"""
Human behavior simulation module to make browser automation more human-like
and reduce CAPTCHA triggers.
"""

import asyncio
import random
import logging
from playwright.async_api import Page

logger = logging.getLogger(__name__)


# Timing configuration for human-like delays
MIN_DELAY = 500  # Minimum delay in milliseconds
MAX_DELAY = 2000  # Maximum delay in milliseconds
MIN_READING_DELAY = 1000  # Minimum time to "read" content
MAX_READING_DELAY = 3000  # Maximum time to "read" content
MIN_CLICK_DELAY = 200  # Minimum delay before clicking
MAX_CLICK_DELAY = 800  # Maximum delay before clicking
MIN_SCROLL_DELAY = 500  # Minimum delay between scrolls
MAX_SCROLL_DELAY = 1500  # Maximum delay between scrolls


async def random_delay(min_ms: int = MIN_DELAY, max_ms: int = MAX_DELAY) -> None:
    """
    Wait for a random amount of time to simulate human thinking/reading.
    
    Args:
        min_ms: Minimum delay in milliseconds
        max_ms: Maximum delay in milliseconds
    """
    delay = random.uniform(min_ms, max_ms) / 1000.0  # Convert to seconds
    await asyncio.sleep(delay)


async def human_like_click(page: Page, locator, delay_before: bool = True) -> None:
    """
    Perform a human-like click with mouse movement and random delays.
    
    Args:
        page: Playwright Page object
        locator: Locator to click
        delay_before: Whether to add delay before clicking
    """
    try:
        # Scroll element into view if needed
        await locator.scroll_into_view_if_needed()
        
        # Random delay before clicking (simulating decision time)
        if delay_before:
            await random_delay(MIN_CLICK_DELAY, MAX_CLICK_DELAY)
        
        # Get element bounding box for mouse movement
        try:
            box = await locator.bounding_box()
            if box:
                # Move mouse to a random point near the element (not exactly center)
                x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
                y = box['y'] + box['height'] * random.uniform(0.3, 0.7)
                
                # Move mouse with human-like speed (not instant)
                await page.mouse.move(x, y, steps=random.randint(5, 15))
                
                # Small random delay before actual click
                await asyncio.sleep(random.uniform(0.05, 0.15))
        except Exception:
            # If bounding box fails, just proceed with click
            pass
        
        # Perform the click
        await locator.click()
        
        # Small delay after click
        await asyncio.sleep(random.uniform(0.1, 0.3))
        
    except Exception as e:
        logger.warning(f"Error in human_like_click: {e}")
        # Fallback to regular click
        await locator.click()


async def random_scroll(page: Page, min_scrolls: int = 1, max_scrolls: int = 3) -> None:
    """
    Perform random scrolling to simulate human browsing behavior.
    
    Args:
        page: Playwright Page object
        min_scrolls: Minimum number of scroll actions
        max_scrolls: Maximum number of scroll actions
    """
    num_scrolls = random.randint(min_scrolls, max_scrolls)
    
    for _ in range(num_scrolls):
        # Random scroll amount (not always full page)
        scroll_amount = random.randint(200, 600)
        
        # Random scroll direction (mostly down, sometimes up)
        if random.random() < 0.9:  # 90% chance to scroll down
            await page.mouse.wheel(0, scroll_amount)
        else:
            await page.mouse.wheel(0, -scroll_amount)
        
        # Random delay between scrolls
        await random_delay(MIN_SCROLL_DELAY, MAX_SCROLL_DELAY)


async def simulate_reading(page: Page, min_seconds: float = None, max_seconds: float = None) -> None:
    """
    Simulate reading time on a page.
    
    Args:
        page: Playwright Page object
        min_seconds: Minimum reading time (uses default if None)
        max_seconds: Maximum reading time (uses default if None)
    """
    if min_seconds is None:
        min_seconds = MIN_READING_DELAY / 1000.0
    if max_seconds is None:
        max_seconds = MAX_READING_DELAY / 1000.0
    
    reading_time = random.uniform(min_seconds, max_seconds)
    
    # Occasionally scroll while "reading"
    if random.random() < 0.4:  # 40% chance to scroll while reading
        await random_scroll(page, 1, 2)
        # Continue reading after scroll
        remaining_time = reading_time * 0.6
        if remaining_time > 0:
            await asyncio.sleep(remaining_time)
    else:
        await asyncio.sleep(reading_time)


async def human_like_navigation(page: Page, url: str, timeout: int = 30000) -> None:
    """
    Navigate to a URL with human-like behavior (delays, scrolling).
    Uses lenient wait strategies to avoid timeout errors with SPAs.
    
    Args:
        page: Playwright Page object
        url: URL to navigate to
        timeout: Timeout in milliseconds (default: 30000)
    """
    # Random delay before navigation (simulating decision to navigate)
    await random_delay(300, 800)
    
    # Navigate with domcontentloaded (more lenient than networkidle)
    await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
    
    # Wait for page to be interactive with fallback
    # SPAs may never reach networkidle, so we use a more lenient approach
    try:
        # Try to wait for load state, but don't fail if it times out
        await page.wait_for_load_state("load", timeout=min(10000, timeout // 3))
    except Exception:
        # If load state times out, just continue - page might still be usable
        logger.debug("Load state timeout, continuing anyway")
        pass
    
    # Additional wait for any critical elements (optional)
    # This gives the page more time to render without strict networkidle requirement
    await asyncio.sleep(1.0)  # Give SPA time to initialize
    
    # Simulate reading the page
    await simulate_reading(page, 1.0, 2.5)
    
    # Random scroll to simulate exploring
    if random.random() < 0.7:  # 70% chance to scroll
        await random_scroll(page, 1, 2)


async def human_like_back_navigation(page: Page, timeout: int = 30000) -> None:
    """
    Navigate back with human-like behavior.
    Uses lenient wait strategies to avoid timeout errors.
    
    Args:
        page: Playwright Page object
        timeout: Timeout in milliseconds (default: 30000)
    """
    # Random delay before going back
    await random_delay(400, 1000)
    
    # Go back
    await page.go_back(wait_until="domcontentloaded", timeout=timeout)
    
    # Wait for page to load with fallback
    try:
        await page.wait_for_load_state("load", timeout=min(10000, timeout // 3))
    except Exception:
        # If load state times out, just continue
        logger.debug("Load state timeout on back navigation, continuing anyway")
        pass
    
    # Give SPA time to re-render
    await asyncio.sleep(1.0)
    
    # Small delay after navigation
    await random_delay(300, 700)


async def random_mouse_movement(page: Page) -> None:
    """
    Perform random mouse movements to simulate human activity.
    
    Args:
        page: Playwright Page object
    """
    try:
        viewport = page.viewport_size
        if viewport:
            # Move to random position on screen
            x = random.randint(100, viewport['width'] - 100)
            y = random.randint(100, viewport['height'] - 100)
            
            # Move with human-like speed
            await page.mouse.move(x, y, steps=random.randint(10, 20))
            
            # Small delay
            await asyncio.sleep(random.uniform(0.1, 0.3))
    except Exception:
        pass  # Ignore errors in mouse movement


async def add_human_variability(action_func, *args, **kwargs):
    """
    Wrapper to add random delays before and after actions.
    
    Args:
        action_func: Async function to wrap
        *args: Arguments for the function
        **kwargs: Keyword arguments for the function
    """
    # Random delay before action
    await random_delay(200, 600)
    
    # Execute action
    result = await action_func(*args, **kwargs)
    
    # Random delay after action
    await random_delay(100, 400)
    
    return result

