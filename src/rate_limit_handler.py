"""
Rate Limiting and CAPTCHA Detection Handler
Handles 429 errors, rate limiting, and CAPTCHA requirements.
"""

import asyncio
import logging
import random
from typing import Optional, Callable
from playwright.async_api import Page, Response

logger = logging.getLogger(__name__)

# Rate limiting configuration
DEFAULT_BACKOFF_BASE = 2  # Exponential backoff base
MAX_BACKOFF_SECONDS = 300  # Maximum 5 minutes
INITIAL_BACKOFF_SECONDS = 5  # Start with 5 seconds
RATE_LIMIT_REST_PERIOD = 60  # Rest period after rate limit (1 minute)


async def handle_rate_limit(
    page: Page,
    retry_func: Callable,
    max_retries: int = 3,
    backoff_base: float = DEFAULT_BACKOFF_BASE
) -> bool:
    """
    Handle rate limiting with exponential backoff.
    
    Args:
        page: Playwright Page object
        retry_func: Async function to retry
        max_retries: Maximum number of retries
        backoff_base: Base for exponential backoff
    
    Returns:
        True if operation succeeded, False if max retries exceeded
    """
    for attempt in range(max_retries):
        try:
            # Check for rate limit errors on the page
            error_text = await check_for_rate_limit_error(page)
            if error_text:
                logger.warning(f"Rate limit detected (attempt {attempt + 1}/{max_retries}): {error_text}")
                
                if attempt < max_retries - 1:
                    # Calculate backoff time (exponential with jitter)
                    backoff_time = min(
                        INITIAL_BACKOFF_SECONDS * (backoff_base ** attempt),
                        MAX_BACKOFF_SECONDS
                    )
                    # Add random jitter (10-30% of backoff time)
                    jitter = backoff_time * random.uniform(0.1, 0.3)
                    total_wait = backoff_time + jitter
                    
                    logger.info(f"Waiting {total_wait:.1f} seconds before retry...")
                    await asyncio.sleep(total_wait)
                    
                    # Try to refresh the page or navigate back
                    try:
                        await page.reload(wait_until="domcontentloaded", timeout=10000)
                        await asyncio.sleep(2)  # Give page time to load
                    except Exception:
                        pass
                    
                    continue
                else:
                    logger.error("Max retries exceeded for rate limit")
                    return False
            
            # Try the operation
            result = await retry_func()
            return True
            
        except Exception as e:
            if "429" in str(e) or "rate limit" in str(e).lower() or "too many requests" in str(e).lower():
                logger.warning(f"Rate limit error caught: {e}")
                if attempt < max_retries - 1:
                    backoff_time = min(
                        INITIAL_BACKOFF_SECONDS * (backoff_base ** attempt),
                        MAX_BACKOFF_SECONDS
                    )
                    jitter = backoff_time * random.uniform(0.1, 0.3)
                    total_wait = backoff_time + jitter
                    
                    logger.info(f"Waiting {total_wait:.1f} seconds before retry...")
                    await asyncio.sleep(total_wait)
                    continue
                else:
                    logger.error("Max retries exceeded")
                    return False
            else:
                # Re-raise if it's not a rate limit error
                raise
    
    return False


async def check_for_rate_limit_error(page: Page) -> Optional[str]:
    """
    Check if the page shows a rate limit or CAPTCHA error.
    
    Args:
        page: Playwright Page object
    
    Returns:
        Error message if found, None otherwise
    """
    try:
        # Check for common error messages
        error_selectors = [
            "text=Não foi possível validar o CAPTCHA",
            "text=Erro!",
            "text=CAPTCHA",
            "text=rate limit",
            "text=too many requests",
            "text=429",
            "[class*='error']",
            "[class*='captcha']",
        ]
        
        for selector in error_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text and any(keyword in text.lower() for keyword in 
                                   ["captcha", "erro", "rate limit", "429", "many requests"]):
                        return text.strip()
            except Exception:
                continue
        
        # Check for specific error message patterns in alerts/dialogs
        try:
            # Check for br-alert or error dialogs
            alert_selectors = [
                "br-alert",
                "[class*='alert']",
                "[class*='error']",
                "[class*='mensagem']",
                "[role='alert']",
            ]
            
            for selector in alert_selectors:
                try:
                    alert_elements = await page.locator(selector).all()
                    for alert in alert_elements:
                        text = await alert.inner_text()
                        if text and ("captcha" in text.lower() or "não foi possível validar" in text.lower()):
                            return text.strip()
                except Exception:
                    continue
        except Exception:
            pass
        
        # Check page content for error messages
        page_text = await page.inner_text("body")
        if page_text:
            # More specific error patterns
            error_patterns = [
                "não foi possível validar o captcha",
                "não foi possível validar o captcha para realizar a operação",
                "erro!",
                "captcha",
                "rate limit",
                "too many requests",
                "429"
            ]
            
            for pattern in error_patterns:
                if pattern in page_text.lower():
                    # Extract error message context
                    lines = page_text.split("\n")
                    for i, line in enumerate(lines):
                        if pattern in line.lower():
                            # Return the error line and maybe next line
                            error_msg = line.strip()
                            if i + 1 < len(lines):
                                error_msg += " " + lines[i + 1].strip()
                            return error_msg
        
        return None
        
    except Exception as e:
        logger.debug(f"Error checking for rate limit: {e}")
        return None


async def setup_rate_limit_monitoring(page: Page) -> None:
    """
    Set up network request monitoring to detect 429 errors and intercept API calls.
    
    Args:
        page: Playwright Page object
    """
    # Use a lock to prevent concurrent access to shared state
    request_lock = asyncio.Lock()
    request_count = 0
    last_request_time = 0
    last_extra_delay_count = 0  # Track when we last added extra delay
    
    async def handle_request(request):
        """Handle network requests to add delays and prevent rate limiting."""
        nonlocal request_count, last_request_time, last_extra_delay_count
        
        # Only monitor API requests to the portal service
        if "portalservicos-ws" in request.url or "recaptchaToken" in request.url:
            async with request_lock:
                request_count += 1
                current_count = request_count
                current_time = asyncio.get_event_loop().time()
                
                # Calculate time since last request
                if last_request_time > 0:
                    time_since_last = current_time - last_request_time
                    if time_since_last < 3.0:  # If less than 3 seconds since last request
                        wait_time = 3.0 - time_since_last
                        logger.debug(f"Adding delay before API request: {wait_time:.2f}s")
                        await asyncio.sleep(wait_time)
                        # Update time after delay
                        current_time = asyncio.get_event_loop().time()
                
                last_request_time = current_time
                
                # Add extra delay every 5 requests (only once per 5 requests)
                # Check if we haven't already added delay for this batch
                if current_count % 5 == 0 and current_count != last_extra_delay_count:
                    last_extra_delay_count = current_count
                    extra_delay = random.uniform(5.0, 10.0)
                    logger.info(f"Added extra delay after {current_count} requests: {extra_delay:.2f}s")
                    await asyncio.sleep(extra_delay)
                    # Update time after extra delay
                    last_request_time = asyncio.get_event_loop().time()
    
    async def handle_response(response: Response):
        """Handle network responses to detect rate limiting."""
        if response.status == 429:
            url_short = response.url.split("?")[0] if "?" in response.url else response.url
            logger.warning(f"429 Too Many Requests detected for: {url_short}")
            logger.warning("Rate limiting detected - adding extended delay")
            
            # Wait longer when 429 is detected
            wait_time = random.uniform(10.0, 20.0)
            logger.info(f"Waiting {wait_time:.2f} seconds after 429 error...")
            await asyncio.sleep(wait_time)
        
        # Check for 400 errors on API calls (might be rate limit related)
        if response.status == 400 and ("portalservicos-ws" in response.url or "recaptchaToken" in response.url):
            # Check if it's a rate limit related 400
            try:
                body = await response.text()
                if "captcha" in body.lower() or "rate" in body.lower() or "limit" in body.lower():
                    logger.warning(f"400 error with rate limit indicators: {response.url[:100]}")
                    wait_time = random.uniform(5.0, 10.0)
                    logger.info(f"Waiting {wait_time:.2f} seconds after potential rate limit 400...")
                    await asyncio.sleep(wait_time)
            except Exception:
                pass
        
        # Check for CAPTCHA-related responses
        if "captcha" in response.url.lower() or "recaptcha" in response.url.lower():
            if response.status >= 400:
                logger.warning(f"CAPTCHA-related request failed: {response.url[:100]} (Status: {response.status})")
    
    page.on("request", handle_request)
    page.on("response", handle_response)


async def wait_after_rate_limit(page: Page, wait_seconds: int = RATE_LIMIT_REST_PERIOD) -> None:
    """
    Wait for a rest period after detecting rate limiting.
    Optionally refreshes the page.
    
    Args:
        page: Playwright Page object
        wait_seconds: Seconds to wait
    """
    logger.info(f"Rate limit detected. Resting for {wait_seconds} seconds...")
    
    # Wait with progress updates
    for remaining in range(wait_seconds, 0, -10):
        logger.info(f"  Waiting... {remaining} seconds remaining")
        await asyncio.sleep(min(10, remaining))
    
    logger.info("Rest period complete. Continuing...")


async def add_extra_delay_for_rate_limiting(min_seconds: float = 3.0, max_seconds: float = 8.0) -> None:
    """
    Add extra delay between requests to avoid rate limiting.
    Use this before making API calls or loading pages.
    
    Args:
        min_seconds: Minimum delay in seconds
        max_seconds: Maximum delay in seconds
    """
    delay = random.uniform(min_seconds, max_seconds)
    logger.debug(f"Adding extra delay: {delay:.2f} seconds to avoid rate limiting")
    await asyncio.sleep(delay)


async def intercept_and_delay_api_calls(page: Page) -> None:
    """
    Intercept API calls and add delays to prevent rate limiting.
    This modifies the page's fetch/XMLHttpRequest to add delays.
    
    Args:
        page: Playwright Page object
    """
    # Get config values for delays
    import config
    delay_min_ms = int(config.API_CALL_DELAY_MIN * 1000)
    delay_max_ms = int(config.API_CALL_DELAY_MAX * 1000)
    
    await page.add_init_script(f"""
        // Track last API call time to enforce minimum spacing
        let lastApiCallTime = 0;
        const MIN_TIME_BETWEEN_CALLS = 3000; // 3 seconds minimum
        
        // Intercept fetch requests
        const originalFetch = window.fetch;
        window.fetch = async function(...args) {{
            const url = args[0];
            
            // Add delay for API calls
            if (typeof url === 'string' && (url.includes('portalservicos-ws') || url.includes('recaptchaToken'))) {{
                const now = Date.now();
                const timeSinceLastCall = now - lastApiCallTime;
                
                // Ensure minimum time between calls
                if (timeSinceLastCall < MIN_TIME_BETWEEN_CALLS) {{
                    const waitTime = MIN_TIME_BETWEEN_CALLS - timeSinceLastCall;
                    await new Promise(resolve => setTimeout(resolve, waitTime));
                }}
                
                // Add random delay between configured min and max
                const delay = Math.random() * ({delay_max_ms} - {delay_min_ms}) + {delay_min_ms};
                await new Promise(resolve => setTimeout(resolve, delay));
                
                lastApiCallTime = Date.now();
            }}
            
            return originalFetch.apply(this, args);
        }};
        
        // Intercept XMLHttpRequest
        const originalXHROpen = XMLHttpRequest.prototype.open;
        const originalXHRSend = XMLHttpRequest.prototype.send;
        
        XMLHttpRequest.prototype.open = function(method, url, ...rest) {{
            this._url = url;
            return originalXHROpen.apply(this, [method, url, ...rest]);
        }};
        
        XMLHttpRequest.prototype.send = async function(...args) {{
            if (this._url && (this._url.includes('portalservicos-ws') || this._url.includes('recaptchaToken'))) {{
                const now = Date.now();
                const timeSinceLastCall = now - lastApiCallTime;
                
                // Ensure minimum time between calls
                if (timeSinceLastCall < MIN_TIME_BETWEEN_CALLS) {{
                    const waitTime = MIN_TIME_BETWEEN_CALLS - timeSinceLastCall;
                    await new Promise(resolve => setTimeout(resolve, waitTime));
                }}
                
                // Add random delay between configured min and max
                const delay = Math.random() * ({delay_max_ms} - {delay_min_ms}) + {delay_min_ms};
                await new Promise(resolve => setTimeout(resolve, delay));
                
                lastApiCallTime = Date.now();
            }}
            
            return originalXHRSend.apply(this, args);
        }};
    """)
    logger.debug(f"API call interception enabled with delays: {config.API_CALL_DELAY_MIN}-{config.API_CALL_DELAY_MAX}s")


async def check_and_handle_captcha(page: Page) -> bool:
    """
    Check if CAPTCHA is required and handle it if possible.
    
    Args:
        page: Playwright Page object
    
    Returns:
        True if CAPTCHA was handled or not present, False if CAPTCHA blocking
    """
    error_text = await check_for_rate_limit_error(page)
    
    if error_text and "captcha" in error_text.lower():
        logger.warning("CAPTCHA requirement detected")
        logger.warning("Note: CAPTCHA solving is not implemented yet.")
        logger.warning("Consider:")
        logger.warning("  1. Increasing delays between requests")
        logger.warning("  2. Using a CAPTCHA solving service")
        logger.warning("  3. Waiting longer before retrying")
        
        # Wait a longer period before retrying
        await wait_after_rate_limit(page, wait_seconds=120)  # 2 minutes
        
        return False
    
    return True
