"""
Certificate selection helper for automating certificate dialog interaction.
Uses pyautogui to interact with system certificate selection dialogs.
"""

import time
import logging
import platform
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Check if pyautogui can be used (delayed import to avoid display connection errors)
PYAUTOGUI_AVAILABLE = False
_pyautogui = None

def _check_pyautogui():
    """Check if pyautogui is available and can connect to display."""
    global PYAUTOGUI_AVAILABLE, _pyautogui
    
    if PYAUTOGUI_AVAILABLE is not False:  # Already checked
        return PYAUTOGUI_AVAILABLE
    
    try:
        import pyautogui
        _pyautogui = pyautogui
        
        # Test if we can actually use pyautogui (check for display)
        try:
            # Set a fake DISPLAY if not set to avoid connection errors during import
            if 'DISPLAY' not in os.environ:
                os.environ['DISPLAY'] = ':0'
            
            # Try to get screen size as a test
            pyautogui.size()
            PYAUTOGUI_AVAILABLE = True
            return True
        except Exception as e:
            PYAUTOGUI_AVAILABLE = False
            logger.debug(f"pyautogui installed but cannot connect to display: {e}")
            return False
    except ImportError:
        PYAUTOGUI_AVAILABLE = False
        logger.debug("pyautogui not available - certificate dialog automation disabled")
        return False
    except Exception as e:
        PYAUTOGUI_AVAILABLE = False
        logger.debug(f"Error checking pyautogui: {e}")
        return False


class CertificateHelper:
    """Helper class for automating certificate selection dialogs."""
    
    def __init__(self):
        """Initialize certificate helper."""
        self.platform = platform.system()
        self.pyautogui_available = _check_pyautogui()
        
        if not self.pyautogui_available:
            logger.debug("pyautogui not available - certificate dialog automation will not work")
            logger.debug("This is normal in headless environments or when DISPLAY is not set")
    
    def select_certificate_from_dialog(self, certificate_name: Optional[str] = None, password: Optional[str] = None) -> bool:
        """
        Attempt to select certificate from system dialog.
        
        Args:
            certificate_name: Name of certificate to select (partial match supported)
            password: Certificate password if required
        
        Returns:
            True if selection attempted, False if not available
        """
        if not self.pyautogui_available or _pyautogui is None:
            logger.warning("Cannot automate certificate selection - pyautogui not available")
            return False
        
        logger.info("Attempting to automate certificate selection dialog...")
        logger.info(f"Platform: {self.platform}")
        
        try:
            # Wait a moment for dialog to appear
            time.sleep(2)
            
            if self.platform == "Windows":
                return self._handle_windows_dialog(certificate_name, password)
            elif self.platform == "Linux":
                return self._handle_linux_dialog(certificate_name, password)
            elif self.platform == "Darwin":  # macOS
                return self._handle_macos_dialog(certificate_name, password)
            else:
                logger.warning(f"Unsupported platform: {self.platform}")
                return False
                
        except Exception as e:
            logger.error(f"Error automating certificate selection: {e}")
            return False
    
    def _handle_windows_dialog(self, certificate_name: Optional[str], password: Optional[str]) -> bool:
        """Handle Windows certificate selection dialog."""
        logger.info("Handling Windows certificate dialog...")
        
        try:
            # Look for certificate selection dialog
            # Common dialog titles: "Select Certificate", "Choose a certificate"
            dialog_titles = ["Select Certificate", "Choose a certificate", "Certificate", "Certificado"]
            
            # Try to find and activate the dialog
            for title in dialog_titles:
                try:
                    window = _pyautogui.getWindowsWithTitle(title)
                    if window:
                        window[0].activate()
                        logger.info(f"Found certificate dialog: {title}")
                        time.sleep(1)
                        break
                except:
                    continue
            
            # If certificate name is provided, try to select it
            if certificate_name:
                logger.info(f"Looking for certificate: {certificate_name}")
                # Type certificate name to filter
                _pyautogui.write(certificate_name, interval=0.1)
                time.sleep(1)
            
            # Press Enter or click OK to select
            # Try Tab to navigate, then Enter
            _pyautogui.press('tab')
            time.sleep(0.5)
            _pyautogui.press('enter')
            
            # If password dialog appears
            if password:
                time.sleep(2)  # Wait for password dialog
                logger.info("Entering certificate password...")
                _pyautogui.write(password, interval=0.1)
                time.sleep(0.5)
                _pyautogui.press('enter')
            
            logger.info("Certificate selection attempted")
            return True
            
        except Exception as e:
            logger.error(f"Error handling Windows dialog: {e}")
            return False
    
    def _handle_linux_dialog(self, certificate_name: Optional[str], password: Optional[str]) -> bool:
        """Handle Linux certificate selection dialog."""
        logger.info("Handling Linux certificate dialog...")
        
        try:
            # On Linux, certificate dialogs vary by desktop environment
            # Common: Firefox/Chrome certificate selection, or system dialog
            
            # Look for common dialog patterns
            # Try to find certificate selection window
            time.sleep(1)
            
            # For Firefox/Chrome on Linux, certificate selection is usually in-browser
            # For system dialogs, we might need to use xdotool or similar
            
            # Try pressing Enter to accept default selection
            _pyautogui.press('enter')
            time.sleep(1)
            
            # If password dialog appears
            if password:
                time.sleep(2)
                logger.info("Entering certificate password...")
                _pyautogui.write(password, interval=0.1)
                time.sleep(0.5)
                _pyautogui.press('enter')
            
            logger.info("Certificate selection attempted")
            return True
            
        except Exception as e:
            logger.error(f"Error handling Linux dialog: {e}")
            return False
    
    def _handle_macos_dialog(self, certificate_name: Optional[str], password: Optional[str]) -> bool:
        """Handle macOS certificate selection dialog."""
        logger.info("Handling macOS certificate dialog...")
        
        try:
            # macOS uses Keychain Access for certificates
            # Certificate selection is usually in-browser or system dialog
            
            # Try pressing Enter to accept
            _pyautogui.press('enter')
            time.sleep(1)
            
            # If password dialog appears (Touch ID or password)
            if password:
                time.sleep(2)
                logger.info("Entering certificate password...")
                _pyautogui.write(password, interval=0.1)
                time.sleep(0.5)
                _pyautogui.press('enter')
            
            logger.info("Certificate selection attempted")
            return True
            
        except Exception as e:
            logger.error(f"Error handling macOS dialog: {e}")
            return False
    
    def wait_for_dialog_and_select(self, timeout: int = 10, certificate_name: Optional[str] = None, password: Optional[str] = None) -> bool:
        """
        Wait for certificate dialog to appear and attempt to select certificate.
        
        Args:
            timeout: Maximum time to wait for dialog (seconds)
            certificate_name: Name of certificate to select
            password: Certificate password if required
        
        Returns:
            True if selection attempted, False otherwise
        """
        if not self.pyautogui_available:
            return False
        
        logger.info(f"Waiting up to {timeout} seconds for certificate dialog...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check if dialog is visible (platform-specific)
            # For now, just wait a bit then try to interact
            time.sleep(1)
            
            # Try to detect dialog (simplified - could be improved)
            try:
                # On Windows, try to find dialog window
                if self.platform == "Windows" and _pyautogui:
                    windows = _pyautogui.getWindowsWithTitle("Certificate")
                    if windows or time.time() - start_time > 3:
                        # Assume dialog appeared, try to interact
                        return self.select_certificate_from_dialog(certificate_name, password)
            except:
                pass
        
        # If timeout, try anyway
        logger.warning("Timeout waiting for dialog, attempting selection anyway...")
        return self.select_certificate_from_dialog(certificate_name, password)

