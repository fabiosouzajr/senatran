"""
CAPTCHA detection and handling module.
Centralized CAPTCHA detection with support for multiple CAPTCHA types.
"""

import time
import logging
from pathlib import Path
from typing import Optional, Dict, List
from playwright.sync_api import Page

logger = logging.getLogger(__name__)


class CaptchaHandler:
    """Handles CAPTCHA detection and resolution."""
    
    # CAPTCHA detection patterns
    CAPTCHA_PATTERNS = {
        'reCAPTCHA': [
            'text=/recaptcha/i',
            '[class*="recaptcha"]',
            '[id*="recaptcha"]',
            'iframe[src*="recaptcha"]',
        ],
        'hCaptcha': [
            'text=/hcaptcha/i',
            '[class*="hcaptcha"]',
            '[id*="hcaptcha"]',
            'iframe[src*="hcaptcha"]',
        ],
        'image_captcha': [
            'text=/captcha.*imagem|captcha.*image/i',
            '[class*="captcha-image"]',
            'img[alt*="captcha"]',
        ],
        'text_captcha': [
            'text=/captcha.*texto|captcha.*text/i',
            '[class*="captcha-text"]',
        ],
        'generic_captcha': [
            'text=/captcha.*inválido|captcha.*invalid|captcha/i',
            '[class*="captcha"]',
            '[id*="captcha"]',
        ],
        'error_message': [
            'text=/ERL0033800/i',
            'text=/erro.*captcha|error.*captcha/i',
            'text=/captcha.*inválido|captcha.*invalid/i',
        ],
    }
    
    def __init__(self, page: Page, screenshot_dir: Optional[Path] = None):
        """
        Initialize CAPTCHA handler.
        
        Args:
            page: Playwright page object.
            screenshot_dir: Directory to save CAPTCHA screenshots (optional).
        """
        self.page = page
        self.screenshot_dir = screenshot_dir
        if screenshot_dir:
            screenshot_dir.mkdir(parents=True, exist_ok=True)
    
    def detect_captcha(self) -> Dict[str, any]:
        """
        Detect if a CAPTCHA is present on the page.
        
        Returns:
            Dictionary with detection results:
            {
                'detected': bool,
                'type': str or None,
                'element_count': int,
                'error_message': str or None,
            }
        """
        result = {
            'detected': False,
            'type': None,
            'element_count': 0,
            'error_message': None,
        }
        
        try:
            # Check for each CAPTCHA type
            for captcha_type, patterns in self.CAPTCHA_PATTERNS.items():
                for pattern in patterns:
                    try:
                        elements = self.page.locator(pattern)
                        count = elements.count()
                        
                        if count > 0:
                            result['detected'] = True
                            result['type'] = captcha_type
                            result['element_count'] = count
                            
                            # Try to get error message
                            if captcha_type in ['generic_captcha', 'error_message']:
                                try:
                                    error_text = elements.first.inner_text()
                                    if error_text:
                                        result['error_message'] = error_text[:200]
                                except:
                                    pass
                            
                            logger.info(f"CAPTCHA detected: type={captcha_type}, count={count}")
                            return result
                    except Exception as e:
                        logger.debug(f"Error checking pattern {pattern}: {e}")
                        continue
            
            # Also check page content for CAPTCHA keywords
            try:
                page_text = self.page.inner_text('body').lower()
                captcha_keywords = ['captcha', 'recaptcha', 'hcaptcha', 'verificação']
                if any(keyword in page_text for keyword in captcha_keywords):
                    # Check if it's an error message
                    if 'inválido' in page_text or 'invalid' in page_text:
                        result['detected'] = True
                        result['type'] = 'generic_captcha'
                        logger.info("CAPTCHA detected via page content analysis")
            except:
                pass
        
        except Exception as e:
            logger.error(f"Error detecting CAPTCHA: {e}")
        
        return result
    
    def take_screenshot(self, filename: str = None) -> Optional[Path]:
        """
        Take a screenshot of the current page (useful for debugging CAPTCHAs).
        
        Args:
            filename: Optional filename for screenshot.
        
        Returns:
            Path to screenshot file or None.
        """
        if not self.screenshot_dir:
            return None
        
        try:
            if filename is None:
                timestamp = int(time.time())
                filename = f"captcha_{timestamp}.png"
            
            screenshot_path = self.screenshot_dir / filename
            self.page.screenshot(path=str(screenshot_path))
            logger.info(f"CAPTCHA screenshot saved: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return None
    
    def wait_for_captcha_solution(self, max_wait: int = 300, check_interval: int = 2) -> bool:
        """
        Wait for user to manually solve CAPTCHA.
        
        Args:
            max_wait: Maximum time to wait in seconds (default 5 minutes).
            check_interval: How often to check for solution in seconds.
        
        Returns:
            True if CAPTCHA appears to be solved, False if timeout.
        """
        logger.info(f"Waiting up to {max_wait} seconds for CAPTCHA to be solved...")
        start_time = time.time()
        last_url = self.page.url
        
        # Take screenshot if directory is configured
        if self.screenshot_dir:
            self.take_screenshot()
        
        while time.time() - start_time < max_wait:
            elapsed = int(time.time() - start_time)
            
            # Log progress periodically
            if elapsed % 10 == 0 and elapsed > 0:
                logger.info(f"[{elapsed}s] Waiting for CAPTCHA solution... (solve it in the browser)")
            
            try:
                current_url = self.page.url
                
                # Check if URL changed (might indicate CAPTCHA solved)
                if current_url != last_url:
                    logger.info(f"URL changed: {last_url} -> {current_url}")
                    last_url = current_url
                    
                    # If redirected away from login/SSO, CAPTCHA might be solved
                    if "sso.acesso.gov.br/login" not in current_url:
                        logger.info("Redirected away from SSO login - CAPTCHA may be solved")
                        # Verify CAPTCHA is gone
                        time.sleep(2)
                        detection = self.detect_captcha()
                        if not detection['detected']:
                            logger.info("✓ CAPTCHA appears to be solved")
                            return True
                
                # Check for ERL0033800 error (invalid CAPTCHA)
                erl_error = self.page.locator('text=/ERL0033800/i')
                if erl_error.count() > 0:
                    error_text = erl_error.first.inner_text()
                    if "inválido" in error_text.lower() or "invalid" in error_text.lower():
                        logger.warning("⚠ CAPTCHA was marked as INVALID (ERL0033800)")
                        logger.warning("The CAPTCHA you solved was rejected. Please solve it again.")
                        logger.warning("Waiting for you to solve the new CAPTCHA...")
                        # Take new screenshot
                        if self.screenshot_dir:
                            self.take_screenshot("captcha_invalid_retry.png")
                        # Continue waiting - a new CAPTCHA should appear
                        time.sleep(check_interval)
                        continue
                
                # Check if CAPTCHA is still present
                detection = self.detect_captcha()
                if not detection['detected']:
                    # Wait a moment and check again to confirm
                    time.sleep(2)
                    detection = self.detect_captcha()
                    if not detection['detected']:
                        logger.info("✓ CAPTCHA error cleared - appears to be solved")
                        return True
                
                # Check if redirected to success page
                if "portalservicos.senatran" in current_url and "sso.acesso.gov.br" not in current_url:
                    logger.info("Redirected to Senatran portal - CAPTCHA solved")
                    return True
                
            except Exception as e:
                logger.debug(f"Error checking CAPTCHA status: {e}")
            
            time.sleep(check_interval)
        
        logger.warning(f"Timeout waiting for CAPTCHA solution after {max_wait} seconds")
        return False
    
    def handle_captcha(self, max_wait: int = 300) -> bool:
        """
        Detect and handle CAPTCHA (currently supports manual solving only).
        
        Args:
            max_wait: Maximum time to wait for manual solution.
        
        Returns:
            True if CAPTCHA was handled successfully, False otherwise.
        """
        detection = self.detect_captcha()
        
        if not detection['detected']:
            return True  # No CAPTCHA present
        
        # Check if it's an error message (like ERL0033800)
        if detection['type'] == 'error_message':
            logger.warning("="*60)
            logger.warning("⚠ CAPTCHA ERROR DETECTED")
            logger.warning("="*60)
            if detection['error_message']:
                logger.warning(f"Error: {detection['error_message']}")
            logger.warning("")
            logger.warning("This usually means:")
            logger.warning("  1. A previous CAPTCHA was invalid")
            logger.warning("  2. A new CAPTCHA will appear")
            logger.warning("  3. Please solve the new CAPTCHA when it appears")
            logger.warning("="*60)
        else:
            logger.warning("="*60)
            logger.warning("⚠ CAPTCHA DETECTED - PAUSING FOR MANUAL SOLVING")
            logger.warning("="*60)
            logger.warning(f"CAPTCHA type: {detection['type']}")
            if detection['error_message']:
                logger.warning(f"Error message: {detection['error_message']}")
            logger.warning("")
            logger.warning("The automation is now PAUSED. Please:")
            logger.warning("  1. Look at the browser window")
            logger.warning("  2. Solve the CAPTCHA manually")
            logger.warning("  3. Wait for the page to update")
            logger.warning("")
            logger.warning("The automation will automatically continue once the CAPTCHA is solved.")
            logger.warning("="*60)
        
        # Take screenshot for reference
        if self.screenshot_dir:
            self.take_screenshot()
        
        # Wait for solution
        solved = self.wait_for_captcha_solution(max_wait=max_wait)
        
        if solved:
            logger.info("✓ CAPTCHA appears to be solved. Continuing automation...")
            return True
        else:
            logger.error("✗ CAPTCHA was not solved within the timeout period.")
            return False

