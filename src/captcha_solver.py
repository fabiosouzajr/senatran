"""
CAPTCHA solving service integration using 2Captcha API.
Handles automatic CAPTCHA detection and solving.
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any
from playwright.async_api import Page

import config

logger = logging.getLogger(__name__)

# 2Captcha API endpoints
CAPTCHA_API_URL = "https://2captcha.com/in.php"
CAPTCHA_RESULT_URL = "https://2captcha.com/res.php"


class CaptchaSolver:
    """Handles CAPTCHA solving using 2Captcha service."""
    
    def __init__(self, api_key: str):
        """
        Initialize CAPTCHA solver.
        
        Args:
            api_key: 2Captcha API key
        """
        self.api_key = api_key
        self.session = None  # Will be set up when needed
    
    async def solve_recaptcha_v2(self, page: Page, site_key: str, page_url: str) -> Optional[str]:
        """
        Solve reCAPTCHA v2 on a page.
        
        Args:
            page: Playwright Page object
            site_key: reCAPTCHA site key
            page_url: URL of the page with CAPTCHA
            
        Returns:
            Solution token if successful, None otherwise
        """
        try:
            logger.info("Starting reCAPTCHA v2 solving process...")
            
            # Step 1: Submit CAPTCHA to 2Captcha
            task_id = await self._submit_captcha("userrecaptcha", site_key, page_url)
            if not task_id:
                logger.error("Failed to submit CAPTCHA to 2Captcha")
                return None
            
            logger.info(f"CAPTCHA submitted, task ID: {task_id}")
            
            # Step 2: Wait for solution
            solution = await self._wait_for_solution(task_id, timeout=120)
            if not solution:
                logger.error("Failed to get CAPTCHA solution")
                return None
            
            logger.info("CAPTCHA solved successfully")
            return solution
            
        except Exception as e:
            logger.error(f"Error solving CAPTCHA: {e}", exc_info=True)
            return None
    
    async def solve_recaptcha_v3(self, page: Page, site_key: str, page_url: str, action: str = "verify") -> Optional[str]:
        """
        Solve reCAPTCHA v3 on a page.
        
        Args:
            page: Playwright Page object
            site_key: reCAPTCHA site key
            page_url: URL of the page with CAPTCHA
            action: reCAPTCHA action (default: "verify")
            
        Returns:
            Solution token if successful, None otherwise
        """
        try:
            logger.info("Starting reCAPTCHA v3 solving process...")
            
            # Step 1: Submit CAPTCHA to 2Captcha
            task_id = await self._submit_captcha("userrecaptcha", site_key, page_url, action=action)
            if not task_id:
                logger.error("Failed to submit CAPTCHA to 2Captcha")
                return None
            
            logger.info(f"CAPTCHA submitted, task ID: {task_id}")
            
            # Step 2: Wait for solution
            solution = await self._wait_for_solution(task_id, timeout=120)
            if not solution:
                logger.error("Failed to get CAPTCHA solution")
                return None
            
            logger.info("CAPTCHA solved successfully")
            return solution
            
        except Exception as e:
            logger.error(f"Error solving CAPTCHA: {e}", exc_info=True)
            return None
    
    async def solve_hcaptcha(self, page: Page, site_key: str, page_url: str) -> Optional[str]:
        """
        Solve hCaptcha on a page.
        
        Args:
            page: Playwright Page object
            site_key: hCaptcha site key
            page_url: URL of the page with CAPTCHA
            
        Returns:
            Solution token if successful, None otherwise
        """
        try:
            logger.info("Starting hCaptcha solving process...")
            
            # Step 1: Submit CAPTCHA to 2Captcha
            task_id = await self._submit_captcha("hcaptcha", site_key, page_url)
            if not task_id:
                logger.error("Failed to submit CAPTCHA to 2Captcha")
                return None
            
            logger.info(f"CAPTCHA submitted, task ID: {task_id}")
            
            # Step 2: Wait for solution
            solution = await self._wait_for_solution(task_id, timeout=120)
            if not solution:
                logger.error("Failed to get CAPTCHA solution")
                return None
            
            logger.info("CAPTCHA solved successfully")
            return solution
            
        except Exception as e:
            logger.error(f"Error solving CAPTCHA: {e}", exc_info=True)
            return None
    
    async def _submit_captcha(self, method: str, site_key: str, page_url: str, **kwargs) -> Optional[str]:
        """
        Submit CAPTCHA to 2Captcha service.
        
        Args:
            method: CAPTCHA type (userrecaptcha, hcaptcha, etc.)
            site_key: CAPTCHA site key
            page_url: Page URL
            **kwargs: Additional parameters
            
        Returns:
            Task ID if successful, None otherwise
        """
        try:
            import aiohttp
            
            params = {
                "key": self.api_key,
                "method": method,
                "googlekey": site_key if method == "userrecaptcha" else None,
                "sitekey": site_key if method == "hcaptcha" else None,
                "pageurl": page_url,
                "json": 1,  # Return JSON response
            }
            
            # Add additional parameters
            if "action" in kwargs:
                params["action"] = kwargs["action"]
            
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(CAPTCHA_API_URL, data=params) as response:
                    result = await response.json()
                    
                    if result.get("status") == 1:
                        return result.get("request")
                    else:
                        error = result.get("request", "Unknown error")
                        logger.error(f"Failed to submit CAPTCHA: {error}")
                        return None
                        
        except ImportError:
            logger.error("aiohttp not installed. Install it with: pip install aiohttp")
            return None
        except Exception as e:
            logger.error(f"Error submitting CAPTCHA: {e}", exc_info=True)
            return None
    
    async def _wait_for_solution(self, task_id: str, timeout: int = 120, poll_interval: int = 5) -> Optional[str]:
        """
        Wait for CAPTCHA solution from 2Captcha.
        
        Args:
            task_id: Task ID from submission
            timeout: Maximum time to wait in seconds
            poll_interval: Time between polls in seconds
            
        Returns:
            Solution token if successful, None otherwise
        """
        try:
            import aiohttp
            
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                await asyncio.sleep(poll_interval)
                
                params = {
                    "key": self.api_key,
                    "action": "get",
                    "id": task_id,
                    "json": 1,
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(CAPTCHA_RESULT_URL, params=params) as response:
                        result = await response.json()
                        
                        if result.get("status") == 1:
                            # Solution ready
                            return result.get("request")
                        elif result.get("request") == "CAPCHA_NOT_READY":
                            # Still processing
                            logger.debug(f"CAPTCHA not ready yet, waiting... ({int(time.time() - start_time)}s)")
                            continue
                        else:
                            # Error
                            error = result.get("request", "Unknown error")
                            logger.error(f"Error getting solution: {error}")
                            return None
            
            logger.error(f"Timeout waiting for CAPTCHA solution ({timeout}s)")
            return None
            
        except ImportError:
            logger.error("aiohttp not installed. Install it with: pip install aiohttp")
            return None
        except Exception as e:
            logger.error(f"Error waiting for solution: {e}", exc_info=True)
            return None
    
    async def inject_solution(self, page: Page, solution: str, captcha_type: str = "recaptcha") -> bool:
        """
        Inject CAPTCHA solution into the page.
        
        Args:
            page: Playwright Page object
            solution: Solution token from solver
            captcha_type: Type of CAPTCHA (recaptcha, hcaptcha)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if captcha_type == "recaptcha":
                # Inject reCAPTCHA solution
                await page.evaluate(f"""
                    (function() {{
                        window.__recaptchaCallback = function(token) {{
                            // Set the token in the form
                            var textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                            if (textarea) {{
                                textarea.value = token;
                                textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            }}
                            
                            // Also try to set it in grecaptcha object
                            if (window.grecaptcha) {{
                                window.grecaptcha.getResponse = function() {{
                                    return token;
                                }};
                            }}
                            
                            // Trigger callback if exists
                            if (window.__recaptchaCallback) {{
                                window.__recaptchaCallback(token);
                            }}
                        }};
                        window.__recaptchaCallback('{solution}');
                    }})();
                """)
                
                # Also try to set it directly
                await page.evaluate(f"""
                    document.querySelector('textarea[name="g-recaptcha-response"]').value = '{solution}';
                """)
                
            elif captcha_type == "hcaptcha":
                # Inject hCaptcha solution
                await page.evaluate(f"""
                    (function() {{
                        window.hcaptcha = window.hcaptcha || {{}};
                        window.hcaptcha.getResponse = function() {{
                            return '{solution}';
                        }};
                        
                        // Set in form
                        var input = document.querySelector('input[name="h-captcha-response"]');
                        if (input) {{
                            input.value = '{solution}';
                            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }}
                    }})();
                """)
            
            logger.info("CAPTCHA solution injected into page")
            return True
            
        except Exception as e:
            logger.error(f"Error injecting solution: {e}", exc_info=True)
            return False


async def detect_and_solve_captcha(page: Page, solver: Optional[CaptchaSolver] = None) -> bool:
    """
    Detect and solve CAPTCHA on the current page.
    
    Args:
        page: Playwright Page object
        solver: Optional CaptchaSolver instance (creates one if not provided)
        
    Returns:
        True if CAPTCHA was detected and solved, False otherwise
    """
    try:
        # Check if CAPTCHA is present
        recaptcha_v2 = await page.locator("iframe[src*='recaptcha']").count()
        recaptcha_v3 = await page.locator("[data-sitekey]").count()
        hcaptcha = await page.locator("iframe[src*='hcaptcha']").count()
        
        if recaptcha_v2 == 0 and recaptcha_v3 == 0 and hcaptcha == 0:
            logger.debug("No CAPTCHA detected on page")
            return False
        
        logger.info("CAPTCHA detected on page")
        
        # Get API key from config
        api_key = getattr(config, "CAPTCHA_API_KEY", None)
        if not api_key:
            logger.warning("CAPTCHA API key not configured. Set CAPTCHA_API_KEY in config or .env")
            return False
        
        # Create solver if not provided
        if solver is None:
            solver = CaptchaSolver(api_key)
        
        page_url = page.url
        
        # Try to solve reCAPTCHA v2
        if recaptcha_v2 > 0:
            logger.info("Detected reCAPTCHA v2")
            # Extract site key from iframe
            site_key = await page.evaluate("""
                () => {
                    const iframe = document.querySelector('iframe[src*="recaptcha"]');
                    if (iframe) {
                        const src = iframe.src;
                        const match = src.match(/[&?]k=([^&]+)/);
                        return match ? match[1] : null;
                    }
                    return null;
                }
            """)
            
            if site_key:
                solution = await solver.solve_recaptcha_v2(page, site_key, page_url)
                if solution:
                    return await solver.inject_solution(page, solution, "recaptcha")
        
        # Try to solve reCAPTCHA v3
        if recaptcha_v3 > 0:
            logger.info("Detected reCAPTCHA v3")
            # Extract site key
            site_key = await page.evaluate("""
                () => {
                    const element = document.querySelector('[data-sitekey]');
                    return element ? element.getAttribute('data-sitekey') : null;
                }
            """)
            
            if site_key:
                solution = await solver.solve_recaptcha_v3(page, site_key, page_url)
                if solution:
                    return await solver.inject_solution(page, solution, "recaptcha")
        
        # Try to solve hCaptcha
        if hcaptcha > 0:
            logger.info("Detected hCaptcha")
            # Extract site key
            site_key = await page.evaluate("""
                () => {
                    const iframe = document.querySelector('iframe[src*="hcaptcha"]');
                    if (iframe) {
                        const src = iframe.src;
                        const match = src.match(/[&?]sitekey=([^&]+)/);
                        return match ? match[1] : null;
                    }
                    return null;
                }
            """)
            
            if site_key:
                solution = await solver.solve_hcaptcha(page, site_key, page_url)
                if solution:
                    return await solver.inject_solution(page, solution, "hcaptcha")
        
        logger.warning("CAPTCHA detected but could not be solved")
        return False
        
    except Exception as e:
        logger.error(f"Error detecting/solving CAPTCHA: {e}", exc_info=True)
        return False

