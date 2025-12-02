#!/usr/bin/env python3
"""
Main controller for Senatran fine automation.
Terminal-based CLI interface to orchestrate the automation process.
"""

import sys
import time
import logging
import argparse
import random
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    BROWSER_CONFIG,
    DELAYS,
    RATE_LIMITING,
    LOGGING_CONFIG,
    STEALTH_CONFIG,
    FINGERPRINT_CONFIG,
    HUMAN_BEHAVIOR_CONFIG,
    CAPTCHA_CONFIG,
    CERTIFICATE_CONFIG,
    BASE_DIR,
)
from auth_handler import AuthHandler
from vehicle_scraper import VehicleScraper
from fine_extractor import FineExtractor
from database import DatabaseManager
from fingerprint_manager import FingerprintManager
from human_behavior import HumanBehavior
from certificate_policy import CertificatePolicyManager

# Try to import certificate checker
try:
    from certificate_checker import CertificateChecker
    CERTIFICATE_CHECKER_AVAILABLE = True
except ImportError:
    CERTIFICATE_CHECKER_AVAILABLE = False

# Set up logging
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG['level']),
    format=LOGGING_CONFIG['format'],
    handlers=[
        logging.FileHandler(LOGGING_CONFIG['file']),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class SenatranAutomation:
    """Main automation controller."""
    
    def __init__(self, headless: bool = False):
        """
        Initialize automation controller.
        
        Args:
            headless: Run browser in headless mode.
        """
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.db = None
        self.fingerprint_manager = FingerprintManager() if FINGERPRINT_CONFIG.get('enabled', True) else None
        self.current_fingerprint = None
        self.cert_policy_manager = None
    
    def check_certificate(self) -> bool:
        """
        Check certificate installation before opening browser.
        
        Returns:
            True if certificate check passed (or not required), False if check failed
        """
        logger.info("Checking certificate installation...")
        
        if not CERTIFICATE_CHECKER_AVAILABLE:
            logger.warning("Certificate checker not available - skipping certificate verification")
            return True  # Continue anyway
        
        try:
            from config import CERTIFICATE_CONFIG
            cert_checker = CertificateChecker()
            cert_name = CERTIFICATE_CONFIG.get('certificate_name', 'novamobilidade')
            
            is_installed, message = cert_checker.check_certificate_installed(cert_name)
            
            if is_installed:
                logger.info(f"✓ {message}")
                logger.info("Certificate appears to be installed in system certificate store.")
                return True
            else:
                logger.warning("="*60)
                logger.warning("CERTIFICATE NOT FOUND IN SYSTEM CERTIFICATE STORE")
                logger.warning("="*60)
                logger.warning(f"✗ {message}")
                logger.warning("")
                logger.warning("For SSO authentication to work automatically, the certificate")
                logger.warning("must be installed in your system's certificate store.")
                logger.warning("")
                logger.warning("Installation instructions:")
                instructions = cert_checker.get_installation_instructions()
                for line in instructions.strip().split('\n'):
                    if line.strip():
                        logger.warning(line)
                logger.warning("")
                logger.warning("After installing the certificate, you may need to:")
                logger.warning("1. Restart your browser")
                logger.warning("2. Run the automation again")
                logger.warning("")
                logger.warning("You can continue anyway, but you may need to manually")
                logger.warning("select the certificate when the dialog appears.")
                logger.warning("="*60)
                
                # Ask user if they want to continue
                response = input("\nDo you want to continue anyway? (yes/no): ").strip().lower()
                if response in ['yes', 'y']:
                    logger.info("Continuing with certificate check warning...")
                    return True
                else:
                    logger.info("Exiting. Please install the certificate and try again.")
                    return False
                    
        except Exception as e:
            logger.error(f"Error during certificate check: {e}")
            logger.warning("Continuing anyway...")
            return True  # Continue on error
    
    def initialize(self):
        """Initialize browser and database."""
        logger.info("Initializing automation...")
        
        # Check certificate BEFORE opening browser
        if not self.check_certificate():
            raise RuntimeError("Certificate check failed - cannot proceed")
        
        # Initialize database
        self.db = DatabaseManager()
        logger.info("Database initialized")
        
        # Initialize browser
        logger.info("Opening browser...")
        self.playwright = sync_playwright().start()
        browser_config = BROWSER_CONFIG.copy()
        browser_config['headless'] = self.headless
        
        # Generate fingerprint if enabled
        fingerprint = None
        if self.fingerprint_manager and FINGERPRINT_CONFIG.get('enabled', True):
            fingerprint = self.fingerprint_manager.generate_fingerprint()
            self.current_fingerprint = fingerprint
            logger.info("Generated browser fingerprint for stealth")
        else:
            # Use default config
            fingerprint = {
                'user_agent': browser_config['user_agent'],
                'viewport': browser_config['viewport'],
            }
        
        # Setup certificate auto-selection policy if enabled
        user_data_dir = None
        if CERTIFICATE_CONFIG.get('auto_select_certificate', True):
            logger.info("Setting up certificate auto-selection policy...")
            self.cert_policy_manager = CertificatePolicyManager()
            
            # Get URLs that require certificate
            cert_urls = [
                "https://sso.acesso.gov.br/*",
                "https://*.acesso.gov.br/*",
            ]
            
            cert_name = CERTIFICATE_CONFIG.get('certificate_name', 'novamobilidade')
            
            # Create a persistent user data directory for policy file
            user_data_dir = BASE_DIR / '.playwright_user_data'
            user_data_dir.mkdir(exist_ok=True)
            
            # Setup policy in user data directory
            # Note: We need to create the policy file before launching the browser
            # so Chrome can read it on startup
            self.cert_policy_manager.user_data_dir = user_data_dir
            policy_success = self.cert_policy_manager.setup_certificate_policy(
                urls=cert_urls,
                certificate_name=cert_name,
                user_data_dir=user_data_dir
            )
            
            if policy_success:
                logger.info("✓ Certificate auto-selection policy configured")
            else:
                logger.warning("⚠ Could not create certificate policy file (will use manual selection)")
        
        # Launch browser with window size arguments (to prevent fullscreen)
        window_size = browser_config.get('window_size', {'width': 1280, 'height': 720})
        launch_args = []
        
        if not browser_config['headless']:
            # Set window size to prevent fullscreen
            launch_args.extend([
                f'--window-size={window_size["width"]},{window_size["height"]}',
                '--start-maximized=false',
            ])
        
        # Add user data directory if policy is enabled
        # This allows Chrome to read the policy file we created
        if user_data_dir:
            launch_args.append(f'--user-data-dir={user_data_dir}')
            logger.info(f"Using user data directory: {user_data_dir}")
        
        # Launch browser
        launch_options = {
            'headless': browser_config['headless'],
            'slow_mo': browser_config['slow_mo'],
        }
        
        if launch_args:
            launch_options['args'] = launch_args
        
        self.browser = self.playwright.chromium.launch(**launch_options)
        
        # Create context with fingerprint
        context_options = {
            'viewport': fingerprint.get('viewport', browser_config['viewport']),
            'user_agent': fingerprint.get('user_agent', browser_config['user_agent']),
            'locale': fingerprint.get('locale', 'pt-BR'),
            'timezone_id': fingerprint.get('timezone', 'America/Sao_Paulo'),
        }
        
        self.context = self.browser.new_context(**context_options)
        
        # Apply stealth features if enabled
        if STEALTH_CONFIG.get('enabled', True):
            self._apply_stealth_features()
        
        # Apply fingerprint via CDP if enabled
        if self.fingerprint_manager and FINGERPRINT_CONFIG.get('enabled', True):
            self.fingerprint_manager.apply_fingerprint_to_context(self.context, fingerprint)
        
        self.page = self.context.new_page()
        logger.info("Browser initialized with stealth and fingerprint features")
    
    def _apply_stealth_features(self):
        """Apply stealth features to browser context using CDP."""
        try:
            # Inject stealth script on every new page
            stealth_script = """
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['pt-BR', 'pt', 'en-US', 'en']
            });
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Chrome runtime
            window.chrome = {
                runtime: {}
            };
            
            // Override WebGL getParameter
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Inc.';
                }
                if (parameter === 37446) {
                    return 'Intel Iris OpenGL Engine';
                }
                return getParameter.call(this, parameter);
            };
            """
            
            self.context.add_init_script(stealth_script)
            logger.info("Stealth features applied to browser context")
        except Exception as e:
            logger.warning(f"Error applying stealth features: {e}")
    
    def check_authentication_status(self) -> bool:
        """
        Check if already authenticated by trying to access a protected resource.
        
        Returns:
            True if already authenticated, False otherwise.
        """
        logger.info("Checking authentication status...")
        
        # Try to access the vehicle list page directly - this is a protected resource
        # If we're redirected to SSO, we're not authenticated
        from config import SENATRAN_VEHICLE_LIST_URL, DELAYS
        try:
            logger.info(f"Testing access to protected resource: {SENATRAN_VEHICLE_LIST_URL}")
            self.page.goto(SENATRAN_VEHICLE_LIST_URL, wait_until="load", timeout=DELAYS['navigation_timeout'])
            time.sleep(DELAYS['page_load'])
            
            current_url = self.page.url
            logger.info(f"Current URL after navigation: {current_url}")
            
            # Check if redirected to SSO (means not authenticated)
            if "sso.acesso.gov.br" in current_url:
                logger.info("✗ Redirected to SSO - not authenticated")
                return False
            
            # Check if we're on the vehicle list page (means authenticated)
            if SENATRAN_VEHICLE_LIST_URL in current_url or "/infracoes/consultar/veiculo" in current_url:
                logger.info("✓ Successfully accessed vehicle list - already authenticated")
                return True
            
            # If we're on Senatran but not sure, check login status
            if "portalservicos.senatran" in current_url:
                auth_handler = AuthHandler(self.page)
                is_logged_in = auth_handler._check_logged_in()
                if is_logged_in:
                    logger.info("✓ Already authenticated - skipping login")
                    auth_handler.is_authenticated = True
                    return True
            
            logger.info("Authentication status unclear - will attempt full authentication")
            return False
            
        except Exception as e:
            logger.warning(f"Error checking auth status: {e}")
            return False
    
    def authenticate(self) -> bool:
        """
        Perform authentication.
        
        Returns:
            True if authentication successful.
        """
        logger.info("="*60)
        logger.info("AUTHENTICATION PHASE")
        logger.info("="*60)
        
        auth_handler = AuthHandler(self.page)
        success = auth_handler.login()
        
        if success:
            logger.info("✓ Authentication successful")
        else:
            logger.error("✗ Authentication failed")
        
        return success
    
    def process_vehicles(self) -> dict:
        """
        Process all vehicles and extract fines.
        
        Returns:
            Dictionary with processing statistics.
        """
        logger.info("="*60)
        logger.info("VEHICLE PROCESSING PHASE")
        logger.info("="*60)
        
        stats = {
            'vehicles_processed': 0,
            'vehicles_failed': 0,
            'fines_extracted': 0,
            'fines_saved': 0,
            'errors': []
        }
        
        try:
            # Get vehicle list
            vehicle_scraper = VehicleScraper(self.page)
            vehicles = vehicle_scraper.get_vehicles()
            
            if not vehicles:
                logger.warning("No vehicles found")
                return stats
            
            logger.info(f"Found {len(vehicles)} vehicles to process")
            
            # Process each vehicle
            for i, vehicle in enumerate(vehicles, 1):
                vehicle_plate = vehicle.get('plate') or vehicle.get('identifier', 'UNKNOWN')
                logger.info(f"\n[{i}/{len(vehicles)}] Processing vehicle: {vehicle_plate}")
                
                try:
                    # Navigate to vehicle fines page
                    if not vehicle_scraper.navigate_to_vehicle_fines(vehicle):
                        logger.warning(f"Could not navigate to fines for {vehicle_plate}")
                        stats['vehicles_failed'] += 1
                        continue
                    
                    # Extract fines
                    fine_extractor = FineExtractor(self.page)
                    fines = fine_extractor.extract_fines(vehicle_plate)
                    
                    if not fines:
                        logger.warning(f"No fines found for {vehicle_plate}")
                        stats['vehicles_processed'] += 1
                        continue
                    
                    logger.info(f"Extracted {len(fines)} fines for {vehicle_plate}")
                    stats['fines_extracted'] += len(fines)
                    
                    # Save fines to database
                    saved_count = self.db.upsert_fines_batch(fines)
                    stats['fines_saved'] += saved_count
                    logger.info(f"Saved {saved_count} fines to database")
                    
                    stats['vehicles_processed'] += 1
                    
                    # Rate limiting delay (use enhanced rate limiting if available)
                    if i < len(vehicles):  # Don't delay after last vehicle
                        from config import RATE_LIMITING_ENHANCED
                        if RATE_LIMITING_ENHANCED.get('use_jitter', False):
                            # Use jitter for more natural delays
                            min_delay = RATE_LIMITING_ENHANCED.get('min_delay', RATE_LIMITING['min_delay'])
                            max_delay = RATE_LIMITING_ENHANCED.get('max_delay', RATE_LIMITING['max_delay'])
                            jitter_factor = RATE_LIMITING_ENHANCED.get('jitter_factor', 0.2)
                            base_delay = (min_delay + max_delay) / 2
                            delay = base_delay * (1 + random.uniform(-jitter_factor, jitter_factor))
                            delay = max(min_delay, min(max_delay, delay))  # Clamp to range
                        else:
                            delay = RATE_LIMITING.get('min_delay', 2)
                        
                        logger.debug(f"Rate limiting delay: {delay:.2f} seconds")
                        if HUMAN_BEHAVIOR_CONFIG.get('enabled', True) and HUMAN_BEHAVIOR_CONFIG.get('use_variable_delays', True):
                            HumanBehavior.sleep_with_variance(delay, HUMAN_BEHAVIOR_CONFIG.get('delay_variance', 0.3))
                        else:
                            time.sleep(delay)
                
                except Exception as e:
                    logger.error(f"Error processing vehicle {vehicle_plate}: {e}")
                    stats['vehicles_failed'] += 1
                    stats['errors'].append(f"{vehicle_plate}: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    
                    # Progressive delay on error
                    if RATE_LIMITING['progressive_delay_on_error']:
                        delay = RATE_LIMITING['max_delay']
                        logger.debug(f"Progressive delay after error: {delay} seconds")
                        time.sleep(delay)
        
        except Exception as e:
            logger.error(f"Error during vehicle processing: {e}")
            import traceback
            traceback.print_exc()
        
        return stats
    
    def generate_report(self, stats: dict):
        """
        Generate and display processing report.
        
        Args:
            stats: Processing statistics dictionary.
        """
        logger.info("\n" + "="*60)
        logger.info("PROCESSING REPORT")
        logger.info("="*60)
        logger.info(f"Vehicles processed: {stats['vehicles_processed']}")
        logger.info(f"Vehicles failed: {stats['vehicles_failed']}")
        logger.info(f"Fines extracted: {stats['fines_extracted']}")
        logger.info(f"Fines saved: {stats['fines_saved']}")
        
        if stats['errors']:
            logger.warning(f"\nErrors encountered: {len(stats['errors'])}")
            for error in stats['errors'][:10]:  # Show first 10
                logger.warning(f"  - {error}")
        
        # Database statistics
        db_stats = self.db.get_statistics()
        if db_stats:
            logger.info("\nDatabase Statistics:")
            logger.info(f"  Total fines in database: {db_stats.get('total_fines', 0)}")
            logger.info(f"  Unique vehicles: {db_stats.get('unique_vehicles', 0)}")
    
    def run(self):
        """Run the complete automation process."""
        try:
            # Initialize
            self.initialize()
            
            # Check if already authenticated by trying to access protected resource
            is_authenticated = self.check_authentication_status()
            
            if not is_authenticated:
                # Not authenticated - perform full authentication
                logger.info("Not authenticated - performing full authentication flow...")
                if not self.authenticate():
                    logger.error("Authentication failed. Cannot continue.")
                    return False
            else:
                logger.info("Already authenticated - proceeding to vehicle list")
            
            # Navigate to vehicle list page (if not already there)
            current_url = self.page.url
            from config import SENATRAN_VEHICLE_LIST_URL, DELAYS
            
            if SENATRAN_VEHICLE_LIST_URL in current_url or "/infracoes/consultar/veiculo" in current_url:
                logger.info("Already on vehicle list page")
            else:
                logger.info("="*60)
                logger.info("NAVIGATING TO VEHICLE LIST")
                logger.info("="*60)
                logger.info(f"Navigating to vehicle list: {SENATRAN_VEHICLE_LIST_URL}")
                try:
                    self.page.goto(SENATRAN_VEHICLE_LIST_URL, wait_until="load", timeout=DELAYS['navigation_timeout'])
                    time.sleep(DELAYS['page_load'])
                    logger.info(f"✓ Successfully navigated to vehicle list page")
                    logger.info(f"Current URL: {self.page.url}")
                    
                    # Verify we're actually on the vehicle list page (not redirected to SSO)
                    if "sso.acesso.gov.br" in self.page.url:
                        logger.error("✗ Redirected to SSO when accessing vehicle list")
                        logger.error("Authentication may have failed or session expired")
                        return False
                except Exception as e:
                    logger.error(f"Error navigating to vehicle list: {e}")
                    return False
            
            # Process vehicles
            stats = self.process_vehicles()
            
            # Generate report
            self.generate_report(stats)
            
            logger.info("\n✓ Automation completed successfully")
            return True
            
        except KeyboardInterrupt:
            logger.info("\n\nAutomation interrupted by user")
            return False
        except Exception as e:
            logger.error(f"\nFatal error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up...")
        
        if self.db:
            self.db.close()
        
        if self.browser:
            self.browser.close()
        
        if self.playwright:
            self.playwright.stop()
        
        logger.info("Cleanup complete")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Automate Senatran fine extraction',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Run with visible browser
  python main.py --headless         # Run in headless mode
        """
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode (may not work with certificate selection)'
    )
    
    args = parser.parse_args()
    
    # Create and run automation
    automation = SenatranAutomation(headless=args.headless)
    success = automation.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()



