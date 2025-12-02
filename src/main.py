#!/usr/bin/env python3
"""
Main controller for Senatran fine automation.
Terminal-based CLI interface to orchestrate the automation process.
"""

import sys
import time
import logging
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    BROWSER_CONFIG,
    DELAYS,
    RATE_LIMITING,
    LOGGING_CONFIG,
)
from auth_handler import AuthHandler
from vehicle_scraper import VehicleScraper
from fine_extractor import FineExtractor
from database import DatabaseManager

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
        
        self.browser = self.playwright.chromium.launch(
            headless=browser_config['headless'],
            slow_mo=browser_config['slow_mo']
        )
        
        self.context = self.browser.new_context(
            viewport=browser_config['viewport'],
            user_agent=browser_config['user_agent']
        )
        
        self.page = self.context.new_page()
        logger.info("Browser initialized")
    
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
                    
                    # Rate limiting delay
                    if i < len(vehicles):  # Don't delay after last vehicle
                        delay = RATE_LIMITING['min_delay']
                        logger.debug(f"Rate limiting delay: {delay} seconds")
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



