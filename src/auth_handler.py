"""
Authentication handler for Senatran portal.
Handles certificate-based authentication through SSO.
"""

import time
import logging
import platform
from pathlib import Path
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from config import (
    SENATRAN_HOME_URL,
    SSO_LOGIN_URL,
    ENTRAR_COM_BUTTON_SELECTOR,
    CERTIFICATE_SELECTOR,
    DELAYS,
    LOGIN_SUCCESS_INDICATORS,
    CERTIFICATE_CONFIG,
    BROWSER_CONFIG,
    HUMAN_BEHAVIOR_CONFIG,
    CAPTCHA_CONFIG,
)
from captcha_handler import CaptchaHandler
from human_behavior import HumanBehavior

logger = logging.getLogger(__name__)

# Try to import certificate helper
try:
    from certificate_helper import CertificateHelper
    CERTIFICATE_HELPER_AVAILABLE = True
except ImportError:
    CERTIFICATE_HELPER_AVAILABLE = False
    # Logger not yet defined, will log later

# Try to import certificate checker
try:
    from certificate_checker import CertificateChecker
    CERTIFICATE_CHECKER_AVAILABLE = True
except ImportError:
    CERTIFICATE_CHECKER_AVAILABLE = False

class AuthHandler:
    """Handles authentication to Senatran portal using certificate."""
    
    def __init__(self, page: Page):
        """
        Initialize authentication handler.
        
        Args:
            page: Playwright page object to use for authentication.
        """
        self.page = page
        self.is_authenticated = False
        self.cert_helper = CertificateHelper() if CERTIFICATE_HELPER_AVAILABLE else None
        self._verify_certificate_config()
        # Note: Certificate installation check is now done before browser initialization in main.py
        
        # Initialize CAPTCHA handler
        screenshot_dir = CAPTCHA_CONFIG.get('screenshot_dir') if CAPTCHA_CONFIG.get('screenshot_on_detection', False) else None
        self.captcha_handler = CaptchaHandler(page, screenshot_dir) if CAPTCHA_CONFIG.get('detection_enabled', True) else None
    
    def _verify_certificate_config(self):
        """Verify certificate configuration and file existence."""
        cert_path = CERTIFICATE_CONFIG.get('certificate_path')
        if cert_path:
            cert_path_obj = Path(cert_path) if isinstance(cert_path, str) else cert_path
            if cert_path_obj.exists():
                logger.info(f"Certificate file verified: {cert_path_obj}")
            else:
                logger.warning(f"Certificate file not found: {cert_path_obj}")
                logger.warning("Please ensure the certificate file exists.")
    
    
    def login(self) -> bool:
        """
        Perform login to Senatran portal.
        
        Returns:
            True if login successful, False otherwise.
        """
        logger.info("Starting authentication process...")
        
        try:
            # Step 1: Navigate to Senatran home
            logger.info(f"Navigating to {SENATRAN_HOME_URL}")
            
            # Try with "load" first (more reliable than "networkidle")
            try:
                self.page.goto(
                    SENATRAN_HOME_URL,
                    wait_until="load",
                    timeout=DELAYS['navigation_timeout']
                )
            except PlaywrightTimeoutError:
                # Fallback: try with "domcontentloaded" if "load" times out
                logger.warning("'load' timeout, trying 'domcontentloaded'...")
                try:
                    self.page.goto(
                        SENATRAN_HOME_URL,
                        wait_until="domcontentloaded",
                        timeout=DELAYS['navigation_timeout']
                    )
                except PlaywrightTimeoutError:
                    # Last resort: just navigate without waiting
                    logger.warning("Navigation timeout, proceeding anyway...")
                    self.page.goto(SENATRAN_HOME_URL, timeout=10000)
            
            # Additional wait for page to stabilize (use human behavior if enabled)
            if HUMAN_BEHAVIOR_CONFIG.get('enabled', True) and HUMAN_BEHAVIOR_CONFIG.get('use_variable_delays', True):
                HumanBehavior.sleep_with_variance(DELAYS['page_load'], HUMAN_BEHAVIOR_CONFIG.get('delay_variance', 0.3))
            else:
                time.sleep(DELAYS['page_load'])
            
            # Verify we're on the right page
            current_url = self.page.url
            logger.info(f"Current URL: {current_url}")
            if "portalservicos.senatran" not in current_url and "sso.acesso.gov.br" not in current_url:
                logger.warning(f"Unexpected URL after navigation: {current_url}")
            
            # Don't check if already logged in here - we already checked in check_authentication_status()
            # Just proceed with authentication flow
            logger.info("Proceeding with authentication flow...")
            logger.info("Will attempt to click 'Entrar com' button and authenticate")
            
            # Step 2: Click "Entrar com" button
            logger.info("Looking for 'Entrar com' button...")
            try:
                entrar_button = self.page.locator(ENTRAR_COM_BUTTON_SELECTOR).locator('..')
                
                if entrar_button.count() == 0:
                    # Try alternative selectors
                    entrar_button = self.page.locator('button, a').filter(has_text="Entrar")
                    if entrar_button.count() == 0:
                        logger.error("Could not find 'Entrar com' button")
                        return False
                
                # Wait before clicking to avoid captcha (use human behavior if enabled)
                wait_time = DELAYS.get('before_login_click', 5)
                logger.info(f"Waiting before clicking login button (anti-captcha)...")
                if HUMAN_BEHAVIOR_CONFIG.get('enabled', True) and HUMAN_BEHAVIOR_CONFIG.get('use_variable_delays', True):
                    HumanBehavior.sleep_with_variance(wait_time, HUMAN_BEHAVIOR_CONFIG.get('delay_variance', 0.3))
                else:
                    time.sleep(wait_time)
                
                logger.info("Clicking 'Entrar com' button...")
                # Use human-like click if enabled
                if HUMAN_BEHAVIOR_CONFIG.get('enabled', True) and HUMAN_BEHAVIOR_CONFIG.get('simulate_mouse_movement', True):
                    HumanBehavior.click_with_human_behavior(self.page, entrar_button.first)
                else:
                    entrar_button.first.click()
                
                # Wait after click (use human behavior if enabled)
                if HUMAN_BEHAVIOR_CONFIG.get('enabled', True) and HUMAN_BEHAVIOR_CONFIG.get('use_variable_delays', True):
                    HumanBehavior.sleep_with_variance(DELAYS['after_click'], HUMAN_BEHAVIOR_CONFIG.get('delay_variance', 0.3))
                else:
                    time.sleep(DELAYS['after_click'])
                
            except Exception as e:
                logger.error(f"Error clicking login button: {e}")
                return False
            
            # Step 3: Wait for SSO redirect
            logger.info("Waiting for SSO redirect...")
            try:
                self.page.wait_for_url(
                    lambda url: "sso.acesso.gov.br" in url,
                    timeout=DELAYS['authentication_timeout'] * 1000
                )
                logger.info(f"Redirected to SSO: {self.page.url}")
            except PlaywrightTimeoutError:
                logger.warning("SSO redirect timeout, checking current URL...")
                if "sso.acesso.gov.br" not in self.page.url:
                    logger.error("Not redirected to SSO page")
                    return False
            
            # Step 4: Handle certificate selection
            logger.info("="*60)
            logger.info("CERTIFICATE SELECTION PHASE")
            logger.info("="*60)
            logger.info("Handling certificate selection...")
            
            cert_selection_result = self._handle_certificate_selection()
            if not cert_selection_result:
                logger.error("✗ Certificate selection failed or timed out")
                logger.error("Please check:")
                logger.error("  1. Certificate dialog appeared and was interacted with")
                logger.error("  2. Certificate password was entered if required")
                logger.error("  3. Certificate is installed in system certificate store")
                return False
            else:
                logger.info("✓ Certificate selection completed")
            
            # Step 5: Wait for redirect back to Senatran
            logger.info("Waiting for authentication to complete and redirect back to Senatran...")
            
            # Check current URL - might be on certificate info page
            current_url = self.page.url
            if "acesso.gov.br/info/x509" in current_url:
                logger.info("Currently on certificate info page - waiting for redirect to Senatran...")
            
            # Wait for URL to change from SSO/certificate info page back to Senatran
            max_wait_time = DELAYS['authentication_timeout']
            start_time = time.time()
            redirect_detected = False
            last_url = current_url
            
            elapsed = 0
            while time.time() - start_time < max_wait_time:
                current_url = self.page.url
                elapsed = int(time.time() - start_time)
                
                # Log progress every 5 seconds
                if elapsed % 5 == 0 and elapsed > 0:
                    logger.info(f"[{elapsed}s] Waiting for redirect... Current URL: {current_url}")
                
                # Check if URL changed
                if current_url != last_url:
                    logger.info(f"✓ URL changed: {last_url} -> {current_url}")
                    last_url = current_url
                
                # Check if we've been redirected back to Senatran
                if "portalservicos.senatran" in current_url and "sso.acesso.gov.br" not in current_url and "acesso.gov.br" not in current_url:
                    logger.info(f"✓✓✓ REDIRECT DETECTED! Now on: {current_url}")
                    redirect_detected = True
                    break
                
                # Check if still on certificate info page (intermediate)
                if "acesso.gov.br/info/x509" in current_url:
                    # This is normal - certificate is being processed
                    # Continue waiting
                    pass
                # Check if still on SSO page (might be waiting for certificate)
                elif "sso.acesso.gov.br" in current_url:
                    # Check for error messages or certificate selection prompts
                    try:
                        # Check for CAPTCHA using new handler
                        if self.captcha_handler:
                            detection = self.captcha_handler.detect_captcha()
                            if detection['detected']:
                                # Handle CAPTCHA
                                max_wait = CAPTCHA_CONFIG.get('max_wait_time', 300)
                                if not self.captcha_handler.handle_captcha(max_wait=max_wait):
                                    logger.error("CAPTCHA was not solved within timeout. Aborting.")
                                    return False
                                else:
                                    logger.info("✓ CAPTCHA appears to be solved. Continuing authentication...")
                                    # Continue waiting for redirect
                                    continue
                        else:
                            # Fallback to old detection method
                            captcha_error = self.page.locator('text=/captcha.*inválido|captcha.*invalid|captcha/i')
                            if captcha_error.count() > 0:
                                error_text = captcha_error.first.inner_text()
                                logger.warning("="*60)
                                logger.warning("⚠ CAPTCHA DETECTED - PAUSING FOR MANUAL SOLVING")
                                logger.warning("="*60)
                                logger.warning(f"Captcha message: {error_text[:200]}")
                                logger.warning("")
                                logger.warning("The automation is now PAUSED. Please:")
                                logger.warning("  1. Look at the browser window")
                                logger.warning("  2. Solve the captcha manually")
                                logger.warning("  3. Wait for the page to update")
                                logger.warning("")
                                logger.warning("The automation will automatically continue once the captcha is solved.")
                                logger.warning("="*60)
                                
                                # Wait for captcha to be solved
                                captcha_solved = self._wait_for_captcha_solution(max_wait=300)  # 5 minutes max
                                if not captcha_solved:
                                    logger.error("Captcha was not solved within 5 minutes. Aborting.")
                                    return False
                                else:
                                    logger.info("✓ Captcha appears to be solved. Continuing authentication...")
                                    # Continue waiting for redirect
                                    continue
                        
                        # Check for certificate not found error
                        cert_not_found = self.page.locator('text=/certificado.*não.*encontrado|certificado.*not.*found/i')
                        if cert_not_found.count() > 0:
                            error_text = cert_not_found.first.inner_text()
                            logger.error(f"✗ CERTIFICATE NOT FOUND ERROR: {error_text[:200]}")
                            logger.error("="*60)
                            logger.error("CERTIFICATE INSTALLATION REQUIRED")
                            logger.error("="*60)
                            logger.error("The certificate is not found in the system certificate store.")
                            logger.error("Please ensure:")
                            logger.error("  1. The certificate is installed in your system's certificate store")
                            logger.error("  2. The certificate is accessible to the browser")
                            logger.error("  3. The certificate name matches what's configured")
                            logger.error("")
                            logger.error("For Linux, you may need to:")
                            logger.error("  - Import certificate into browser's NSS database")
                            logger.error("  - Or use system-wide certificate stores")
                            logger.error("="*60)
                            return False
                        
                        # Check for other error messages (but don't spam logs)
                        if elapsed % 10 == 0:  # Only check every 10 seconds to avoid spam
                            error_elements = self.page.locator('text=/erro|error|senha|password/i')
                            if error_elements.count() > 0:
                                error_text = error_elements.first.inner_text()
                                if "captcha" not in error_text.lower():  # Skip if already handled above
                                    logger.warning(f"⚠ Possible error on SSO page: {error_text[:100]}")
                    except:
                        pass
                else:
                    # URL changed but not to Senatran - log it
                    logger.info(f"On intermediate page: {current_url}")
                
                time.sleep(1)
            
            if not redirect_detected:
                logger.warning(f"Timeout waiting for redirect after {max_wait_time} seconds")
                logger.warning(f"Still on URL: {self.page.url}")
                if "acesso.gov.br/info/x509" in self.page.url:
                    logger.warning("Stuck on certificate info page - certificate selection may not have completed")
                    logger.warning("Possible reasons:")
                    logger.warning("  1. Certificate requires password (not entered)")
                    logger.warning("  2. Certificate selection dialog not completed")
                    logger.warning("  3. Certificate validation failed")
                else:
                    logger.warning("Certificate selection may require password or manual intervention")
                return False
            
            # Additional wait for page to fully load (use human behavior if enabled)
            if HUMAN_BEHAVIOR_CONFIG.get('enabled', True) and HUMAN_BEHAVIOR_CONFIG.get('use_variable_delays', True):
                HumanBehavior.sleep_with_variance(DELAYS['page_load'], HUMAN_BEHAVIOR_CONFIG.get('delay_variance', 0.3))
            else:
                time.sleep(DELAYS['page_load'])
            
            # Step 6: Verify login success
            logger.info("Verifying login status...")
            if self._check_logged_in():
                logger.info("✓ Authentication successful")
                self.is_authenticated = True
                return True
            else:
                logger.error("✗ Authentication failed - not logged in after redirect")
                logger.error(f"Current URL: {self.page.url}")
                return False
                
        except Exception as e:
            logger.error(f"Error during authentication: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _handle_certificate_selection(self) -> bool:
        """
        Handle certificate selection dialog.
        
        This method attempts to trigger and handle the certificate selection.
        The certificate file is referenced in config, but for SSO authentication,
        the certificate must be in the system certificate store for the browser to use it.
        
        Returns:
            True if certificate selection was handled, False otherwise.
        """
        try:
            # Log certificate file location
            cert_path = CERTIFICATE_CONFIG.get('certificate_path')
            if cert_path:
                cert_path_str = str(cert_path) if isinstance(cert_path, Path) else cert_path
                logger.info(f"Certificate file configured: {cert_path_str}")
                # Check if file exists
                if isinstance(cert_path, Path) and cert_path.exists():
                    logger.info(f"Certificate file found at: {cert_path}")
                elif isinstance(cert_path, str) and Path(cert_path).exists():
                    logger.info(f"Certificate file found at: {cert_path}")
                else:
                    logger.warning(f"Certificate file not found at: {cert_path}")
                    logger.warning("Make sure the certificate is installed in the system certificate store")
            
            # Wait a moment for SSO page to fully load (longer to avoid captcha)
            logger.info("Waiting for SSO page to fully load...")
            if HUMAN_BEHAVIOR_CONFIG.get('enabled', True) and HUMAN_BEHAVIOR_CONFIG.get('use_variable_delays', True):
                HumanBehavior.sleep_with_variance(DELAYS.get('page_load', 5), HUMAN_BEHAVIOR_CONFIG.get('delay_variance', 0.3))
            else:
                time.sleep(DELAYS.get('page_load', 5))
            
            # Check current URL
            current_url = self.page.url
            logger.info(f"Current URL on SSO page: {current_url}")
            
            # Look for certificate selection button with id="login-certificate"
            logger.info(f"Looking for certificate button with selector: {CERTIFICATE_SELECTOR}")
            logger.info("Expected button text: 'Seu certificado digital'")
            
            cert_element = self.page.locator(CERTIFICATE_SELECTOR)
            cert_count = cert_element.count()
            logger.info(f"Found {cert_count} certificate button(s) with id='login-certificate'")
            
            if cert_count > 0:
                # Verify it has the expected text
                try:
                    button_text = cert_element.first.inner_text()
                    logger.info(f"Button text: '{button_text}'")
                    if "certificado" in button_text.lower() or "certificate" in button_text.lower():
                        logger.info("✓ Found certificate button with correct text")
                    else:
                        logger.warning(f"Button text doesn't match expected pattern, but proceeding anyway")
                except:
                    pass
                
                logger.info("Clicking certificate selection button...")
                # Wait a bit before clicking to avoid captcha (use human behavior if enabled)
                if HUMAN_BEHAVIOR_CONFIG.get('enabled', True) and HUMAN_BEHAVIOR_CONFIG.get('use_variable_delays', True):
                    HumanBehavior.sleep_with_variance(DELAYS.get('before_certificate_click', 2), HUMAN_BEHAVIOR_CONFIG.get('delay_variance', 0.3))
                else:
                    time.sleep(DELAYS.get('before_certificate_click', 2))
                try:
                    # Use human-like click if enabled
                    if HUMAN_BEHAVIOR_CONFIG.get('enabled', True) and HUMAN_BEHAVIOR_CONFIG.get('simulate_mouse_movement', True):
                        HumanBehavior.click_with_human_behavior(self.page, cert_element.first)
                    else:
                        cert_element.first.click()
                    logger.info("✓ Certificate button clicked - certificate dialog should appear")
                    # Wait after click (use human behavior if enabled)
                    if HUMAN_BEHAVIOR_CONFIG.get('enabled', True) and HUMAN_BEHAVIOR_CONFIG.get('use_variable_delays', True):
                        HumanBehavior.sleep_with_variance(DELAYS['after_click'], HUMAN_BEHAVIOR_CONFIG.get('delay_variance', 0.3))
                    else:
                        time.sleep(DELAYS['after_click'])
                except Exception as e:
                    logger.error(f"Error clicking certificate button: {e}")
                    logger.info("Trying alternative click method...")
                    try:
                        cert_element.first.click(force=True)
                        logger.info("Certificate button clicked (force)")
                        time.sleep(DELAYS['after_click'])
                    except Exception as e2:
                        logger.error(f"Error with force click: {e2}")
                        logger.error("Please manually click the certificate button in the browser")
            else:
                # Try alternative selectors as fallback
                logger.warning("Certificate button with id='login-certificate' not found, trying alternatives...")
                
                # Try by text content
                cert_by_text = self.page.locator('button, a, div').filter(has_text="Seu certificado digital")
                if cert_by_text.count() > 0:
                    logger.info("Found certificate button by text 'Seu certificado digital'")
                    cert_by_text.first.click()
                    time.sleep(DELAYS['after_click'])
                else:
                    # Try any element with "certificado" text
                    cert_links = self.page.locator('button, a, div').filter(
                        has_text=lambda text: "certificado" in text.lower() if text else False
                    )
                    alt_count = cert_links.count()
                    logger.info(f"Found {alt_count} alternative certificate elements")
                    if alt_count > 0:
                        logger.info("Clicking alternative certificate element...")
                        cert_links.first.click()
                        time.sleep(DELAYS['after_click'])
                    else:
                        logger.error("✗ Could not find certificate selection element")
                        logger.error("Please manually click the certificate selection button in the browser")
                        logger.error("Look for button with id='login-certificate' or text 'Seu certificado digital'")
            
            # Wait for certificate selection dialog
            # On Windows/Linux, this typically opens a system dialog
            # We can't directly interact with system dialogs via Playwright
            # The certificate must be in the system certificate store for automatic selection
            # or the user must select it manually from the dialog
            timeout = CERTIFICATE_CONFIG['manual_selection_timeout']
            logger.info(f"Waiting {timeout} seconds for certificate selection...")
            
            # Check if certificate might require password
            cert_password = CERTIFICATE_CONFIG.get('certificate_password')
            cert_name = CERTIFICATE_CONFIG.get('certificate_name', 'novamobilidade')  # Default from filename
            
            if cert_password:
                logger.info("Certificate password is configured - will be used if prompted")
            else:
                logger.warning("No certificate password configured - certificate may require password entry")
            
            # Try to automate certificate selection if helper is available
            if self.cert_helper:
                logger.info("Attempting to automate certificate selection...")
                logger.info(f"Certificate name pattern: {cert_name}")
                
                # Wait a moment for dialog to appear, then try to automate
                time.sleep(2)
                automation_success = self.cert_helper.wait_for_dialog_and_select(
                    timeout=5,
                    certificate_name=cert_name,
                    password=cert_password
                )
                
                if automation_success:
                    logger.info("Certificate selection automation attempted")
                else:
                    logger.warning("Certificate selection automation not available or failed")
                    logger.info("Please select your certificate manually in the system dialog if it appears.")
            else:
                logger.info("Certificate dialog automation not available (install pyautogui for automation)")
                logger.info("Please select your certificate manually in the system dialog if it appears.")
            
            if cert_path:
                logger.info("Note: Certificate file is configured, but it must be in the system certificate store for automatic use.")
            logger.info("If a password is required, enter it in the certificate dialog.")
            
            # Wait for either:
            # 1. URL change (redirected back to Senatran)
            # 2. Timeout (user may have selected certificate)
            start_time = time.time()
            last_url = self.page.url
            
            elapsed = 0
            while time.time() - start_time < timeout:
                current_url = self.page.url
                elapsed = int(time.time() - start_time)
                
                # Log progress every 5 seconds
                if elapsed % 5 == 0 and elapsed > 0:
                    logger.info(f"[{elapsed}s] Waiting for certificate selection... Current URL: {current_url}")
                
                # Check if URL changed (redirect happened)
                if current_url != last_url:
                    logger.info(f"✓ URL changed: {last_url} -> {current_url}")
                    last_url = current_url
                
                # Check if redirected back to Senatran
                if "portalservicos.senatran" in current_url and "sso.acesso.gov.br" not in current_url:
                    logger.info("✓✓✓ REDIRECT DETECTED! Back to Senatran portal")
                    logger.info(f"Final URL: {current_url}")
                    return True
                
                # Check if on intermediate certificate info page (acesso.gov.br/info/x509/)
                if "acesso.gov.br/info/x509" in current_url:
                    logger.debug("On certificate info page - waiting for redirect to Senatran...")
                    # This is an intermediate page, continue waiting
                
                # Check for error messages on SSO page
                try:
                    # Check for ERL error codes (common SSO errors: ERL0033800, ERL0002200, etc.)
                    erl_error = self.page.locator('text=/ERL\d+/i')
                    if erl_error.count() > 0:
                        error_text = erl_error.first.inner_text()
                        # Extract error code
                        import re
                        match = re.search(r'ERL\d+', error_text)
                        error_code = match.group() if match else "UNKNOWN"
                        
                        logger.warning("="*60)
                        logger.warning(f"⚠ SSO ERROR DETECTED ({error_code})")
                        logger.warning("="*60)
                        logger.warning(f"Error message: {error_text[:300]}")
                        logger.warning("")
                        
                        # Check if it's a captcha error
                        if "captcha" in error_text.lower() or "inválido" in error_text.lower() or error_code in ['ERL0033800', 'ERL0002200']:
                            logger.warning("This appears to be a CAPTCHA error.")
                            logger.warning("The automation is now PAUSED. Please:")
                            logger.warning("  1. Look at the browser window")
                            logger.warning("  2. Solve the captcha manually (if visible)")
                            logger.warning("  3. Refresh the page if needed")
                            logger.warning("  4. Wait for the page to update")
                            logger.warning("")
                            logger.warning("The automation will automatically continue once resolved.")
                            logger.warning("="*60)
                            
                            # Wait for error to be resolved
                            error_resolved = self._wait_for_error_resolution(max_wait=300)  # 5 minutes max
                            if not error_resolved:
                                logger.error("Error was not resolved within 5 minutes. Aborting.")
                                return False
                            else:
                                logger.info("✓ Error appears to be resolved. Continuing authentication...")
                                # Continue waiting for certificate selection
                                continue
                        else:
                            logger.warning("This may be a different SSO error.")
                            logger.warning("Please check the browser window for details.")
                            logger.warning("The automation will wait for the error to clear.")
                            logger.warning("="*60)
                            
                            # Wait for error to be resolved
                            error_resolved = self._wait_for_error_resolution(max_wait=300)
                            if not error_resolved:
                                logger.error("Error was not resolved within 5 minutes. Aborting.")
                                return False
                            else:
                                logger.info("✓ Error appears to be resolved. Continuing authentication...")
                                continue
                    
                    # Check for CAPTCHA using new handler
                    if self.captcha_handler:
                        detection = self.captcha_handler.detect_captcha()
                        if detection['detected']:
                            # Handle CAPTCHA
                            max_wait = CAPTCHA_CONFIG.get('max_wait_time', 300)
                            if not self.captcha_handler.handle_captcha(max_wait=max_wait):
                                logger.error("CAPTCHA was not solved within timeout. Aborting.")
                                return False
                            else:
                                logger.info("✓ CAPTCHA appears to be solved. Continuing authentication...")
                                # Continue waiting for certificate selection
                                continue
                    else:
                        # Fallback to old detection method
                        captcha_error = self.page.locator('text=/captcha.*inválido|captcha.*invalid|captcha/i')
                        if captcha_error.count() > 0:
                            error_text = captcha_error.first.inner_text()
                            logger.warning("="*60)
                            logger.warning("⚠ CAPTCHA DETECTED - PAUSING FOR MANUAL SOLVING")
                            logger.warning("="*60)
                            logger.warning(f"Captcha message: {error_text[:200]}")
                            logger.warning("")
                            logger.warning("The automation is now PAUSED. Please:")
                            logger.warning("  1. Look at the browser window")
                            logger.warning("  2. Solve the captcha manually")
                            logger.warning("  3. Wait for the page to update")
                            logger.warning("")
                            logger.warning("The automation will automatically continue once the captcha is solved.")
                            logger.warning("="*60)
                            
                            # Wait for captcha to be solved (check every 2 seconds)
                            captcha_solved = self._wait_for_captcha_solution(max_wait=300)  # 5 minutes max
                            if not captcha_solved:
                                logger.error("Captcha was not solved within 5 minutes. Aborting.")
                                return False
                            else:
                                logger.info("✓ Captcha appears to be solved. Continuing authentication...")
                                # Continue waiting for certificate selection
                                continue
                    
                    # Check for certificate not found error
                    cert_not_found = self.page.locator('text=/certificado.*não.*encontrado|certificado.*not.*found/i')
                    if cert_not_found.count() > 0:
                        error_text = cert_not_found.first.inner_text()
                        logger.error(f"✗ CERTIFICATE NOT FOUND ERROR: {error_text[:200]}")
                        logger.error("The certificate is not found in the system certificate store.")
                        logger.error("Please install the certificate in your system's certificate store.")
                        return False
                    
                    # Check for other errors (but don't spam logs)
                    if elapsed % 10 == 0:  # Only check every 10 seconds to avoid spam
                        error_elements = self.page.locator('text=/erro|error|falha|invalid|inválido/i')
                        if error_elements.count() > 0:
                            error_text = error_elements.first.inner_text()
                            if "captcha" not in error_text.lower():  # Skip if already handled above
                                logger.warning(f"⚠ Error detected on SSO page: {error_text[:150]}")
                                if "senha" in error_text.lower() or "password" in error_text.lower():
                                    logger.error("✗ Certificate password may be required or incorrect!")
                except:
                    pass
                
                # Check page title for clues
                try:
                    page_title = self.page.title()
                    if "senatran" in page_title.lower() and "sso" not in page_title.lower():
                        logger.info(f"Page title suggests redirect: {page_title}")
                except:
                    pass
                
                time.sleep(1)
            
            # Check if we're still on SSO page or redirected
            final_url = self.page.url
            if "sso.acesso.gov.br" not in final_url:
                # Check if we're on the certificate info page (intermediate)
                if "acesso.gov.br/info/x509" in final_url:
                    logger.info(f"On certificate info page: {final_url}")
                    logger.info("This is an intermediate page - certificate may be processing")
                    logger.info("Will continue waiting for redirect in next phase")
                    return True  # Return True to continue to redirect wait phase
                else:
                    logger.info(f"No longer on SSO page - now on: {final_url}")
                    # Check if already on Senatran
                    if "portalservicos.senatran" in final_url:
                        logger.info("✓ Already redirected to Senatran!")
                        return True
                    return True
            
            logger.warning(f"Still on SSO page after {timeout} seconds timeout")
            logger.warning("Certificate selection may not have completed successfully")
            logger.warning("Possible reasons:")
            logger.warning("  1. Certificate requires password (not entered or incorrect)")
            logger.warning("  2. Certificate not found in system certificate store")
            logger.warning("  3. Certificate selection dialog not interacted with")
            return False  # Return False to indicate certificate selection failed
            
        except Exception as e:
            logger.error(f"Error handling certificate selection: {e}")
            return False
    
    def _wait_for_error_resolution(self, max_wait: int = 300) -> bool:
        """
        Wait for SSO error (like ERL0033800) to be resolved.
        
        Args:
            max_wait: Maximum time to wait in seconds (default 5 minutes)
        
        Returns:
            True if error appears to be resolved, False if timeout
        """
        logger.info(f"Waiting up to {max_wait} seconds for error to be resolved...")
        start_time = time.time()
        last_url = self.page.url
        
        while time.time() - start_time < max_wait:
            elapsed = int(time.time() - start_time)
            
            # Check every 5 seconds
            if elapsed % 5 == 0 and elapsed > 0:
                logger.info(f"[{elapsed}s] Waiting for error resolution... (check browser window)")
            
            try:
                current_url = self.page.url
                
                # Check if URL changed (might indicate error resolved and redirect)
                if current_url != last_url:
                    logger.info(f"URL changed: {last_url} -> {current_url}")
                    last_url = current_url
                    
                    # If redirected away from SSO login, error might be resolved
                    if "sso.acesso.gov.br/login" not in current_url:
                        logger.info("Redirected away from SSO login page - error may be resolved")
                        return True
                
                # Check if ERL error is still present (any ERL code)
                erl_error = self.page.locator('text=/ERL\d+/i')
                if erl_error.count() == 0:
                    # Error disappeared - might be resolved
                    logger.info("Error message no longer present - checking if resolved...")
                    time.sleep(2)  # Wait a moment for page to update
                    
                    # Check again to confirm
                    erl_error = self.page.locator('text=/ERL\d+/i')
                    if erl_error.count() == 0:
                        logger.info("✓ Error cleared - appears to be resolved")
                        return True
                
                # Check if we're on certificate info page or redirected to Senatran
                if "acesso.gov.br/info/x509" in current_url or "portalservicos.senatran" in current_url:
                    logger.info("Redirected to certificate info or Senatran - error resolved")
                    return True
                
            except Exception as e:
                logger.debug(f"Error checking error status: {e}")
            
            time.sleep(2)  # Check every 2 seconds
        
        logger.warning(f"Timeout waiting for error resolution after {max_wait} seconds")
        return False
    
    def _wait_for_captcha_solution(self, max_wait: int = 300) -> bool:
        """
        Wait for user to manually solve captcha.
        
        Args:
            max_wait: Maximum time to wait in seconds (default 5 minutes)
        
        Returns:
            True if captcha appears to be solved, False if timeout
        """
        logger.info(f"Waiting up to {max_wait} seconds for captcha to be solved...")
        start_time = time.time()
        last_url = self.page.url
        
        while time.time() - start_time < max_wait:
            elapsed = int(time.time() - start_time)
            
            # Check every 5 seconds
            if elapsed % 5 == 0 and elapsed > 0:
                logger.info(f"[{elapsed}s] Waiting for captcha solution... (solve it in the browser)")
            
            try:
                current_url = self.page.url
                
                # Check if URL changed (might indicate captcha solved and redirect)
                if current_url != last_url:
                    logger.info(f"URL changed: {last_url} -> {current_url}")
                    last_url = current_url
                    
                    # If redirected away from SSO login, captcha might be solved
                    if "sso.acesso.gov.br/login" not in current_url:
                        logger.info("Redirected away from SSO login page - captcha may be solved")
                        return True
                
                # Check if captcha error is still present
                captcha_error = self.page.locator('text=/captcha.*inválido|captcha.*invalid|captcha/i')
                if captcha_error.count() == 0:
                    # Captcha error disappeared - might be solved
                    logger.info("Captcha error message no longer present - checking if solved...")
                    time.sleep(2)  # Wait a moment for page to update
                    
                    # Check again to confirm
                    captcha_error = self.page.locator('text=/captcha.*inválido|captcha.*invalid|captcha/i')
                    if captcha_error.count() == 0:
                        logger.info("✓ Captcha error cleared - appears to be solved")
                        return True
                
                # Check if we're on certificate info page or redirected to Senatran
                if "acesso.gov.br/info/x509" in current_url or "portalservicos.senatran" in current_url:
                    logger.info("Redirected to certificate info or Senatran - captcha solved")
                    return True
                
            except Exception as e:
                logger.debug(f"Error checking captcha status: {e}")
            
            time.sleep(2)  # Check every 2 seconds
        
        logger.warning(f"Timeout waiting for captcha solution after {max_wait} seconds")
        return False
    
    def _check_logged_in(self) -> bool:
        """
        Check if user is currently logged in.
        
        Returns:
            True if logged in, False otherwise.
        """
        try:
            current_url = self.page.url
            logger.info(f"Checking login status on URL: {current_url}")
            
            # First check: Must NOT be on SSO page
            if "sso.acesso.gov.br" in current_url:
                logger.info("✗ Still on SSO page - not logged in")
                return False
            
            # Second check: Must be on Senatran portal
            if "portalservicos.senatran" not in current_url:
                logger.info(f"✗ Not on Senatran portal - URL: {current_url}")
                return False
            
            logger.info("✓ On Senatran portal, checking for login indicators...")
            
            # Third check: Look for login success indicators
            for indicator in LOGIN_SUCCESS_INDICATORS:
                elements = self.page.locator(indicator)
                count = elements.count()
                if count > 0:
                    logger.info(f"✓ Found login indicator: {indicator} ({count} found)")
                    return True
                else:
                    logger.debug(f"  - {indicator}: not found")
            
            # Fourth check: Check if "Entrar com" button is visible (if visible, NOT logged in)
            logger.info(f"Checking for 'Entrar com' button with selector: {ENTRAR_COM_BUTTON_SELECTOR}")
            entrar_button = self.page.locator(ENTRAR_COM_BUTTON_SELECTOR)
            entrar_count = entrar_button.count()
            logger.info(f"'Entrar com' button count: {entrar_count}")
            
            if entrar_count > 0:
                # Button is visible - we're NOT logged in
                logger.info("✗ 'Entrar com' button is visible - NOT logged in")
                try:
                    button_text = entrar_button.first.inner_text()
                    logger.info(f"Button text: '{button_text}'")
                except:
                    pass
                return False
            else:
                # Button not found - might be logged in, but verify
                logger.info("✓ 'Entrar com' button not found")
                logger.info("Attempting to verify by checking page content...")
                
                # Try to see if we can access protected content
                # Check page title or other indicators
                try:
                    page_title = self.page.title()
                    logger.info(f"Page title: {page_title}")
                except:
                    pass
                
                # If we're here and button is not visible, likely logged in
                logger.info("✓ Appears to be logged in (login button not visible)")
                return True
            
        except Exception as e:
            logger.error(f"Error checking login status: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def logout(self):
        """Logout from Senatran portal (if needed)."""
        # Implementation if logout is needed
        pass



