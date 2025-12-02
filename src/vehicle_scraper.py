"""
Vehicle scraper to extract vehicle list from Senatran portal.
"""

import time
import logging
import re
from typing import List, Dict, Optional
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from config import (
    SENATRAN_VEHICLE_LIST_URL,
    VEHICLE_LIST_SELECTORS,
    DELAYS,
)

logger = logging.getLogger(__name__)


class VehicleScraper:
    """Scrapes vehicle list from Senatran portal."""
    
    def __init__(self, page: Page):
        """
        Initialize vehicle scraper.
        
        Args:
            page: Playwright page object.
        """
        self.page = page
    
    def get_vehicles(self) -> List[Dict[str, str]]:
        """
        Extract list of vehicles from the portal.
        
        Returns:
            List of dictionaries containing vehicle information.
            Each dict should have at least 'plate' or 'identifier' key.
        """
        logger.info("Starting vehicle list extraction...")
        
        try:
            # Check if already on vehicle list page
            current_url = self.page.url
            if SENATRAN_VEHICLE_LIST_URL in current_url or "/infracoes/consultar/veiculo" in current_url:
                logger.info("Already on vehicle list page, skipping navigation")
                time.sleep(DELAYS['page_load'])
            else:
                # Navigate to vehicle list page
                logger.info(f"Navigating to {SENATRAN_VEHICLE_LIST_URL}")
                
                # Use "load" instead of "networkidle" for more reliable navigation
                try:
                    self.page.goto(
                        SENATRAN_VEHICLE_LIST_URL,
                        wait_until="load",
                        timeout=DELAYS.get('navigation_timeout', 60000)
                    )
                except PlaywrightTimeoutError:
                    logger.warning("Navigation timeout, trying domcontentloaded...")
                    self.page.goto(
                        SENATRAN_VEHICLE_LIST_URL,
                        wait_until="domcontentloaded",
                        timeout=DELAYS.get('navigation_timeout', 60000)
                    )
                
                time.sleep(DELAYS['page_load'])
            
            vehicles = []
            
            # Try multiple extraction methods
            # Method 1: Extract from table
            vehicles.extend(self._extract_from_table())
            
            # Method 2: Extract from list/cards
            if not vehicles:
                vehicles.extend(self._extract_from_list())
            
            # Method 3: Extract from links/buttons
            if not vehicles:
                vehicles.extend(self._extract_from_links())
            
            # Method 4: Extract using regex patterns
            if not vehicles:
                vehicles.extend(self._extract_using_regex())
            
            logger.info(f"Extracted {len(vehicles)} vehicles")
            return vehicles
            
        except Exception as e:
            logger.error(f"Error extracting vehicles: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _extract_from_table(self) -> List[Dict[str, str]]:
        """Extract vehicles from table structure."""
        vehicles = []
        
        try:
            tables = self.page.locator(VEHICLE_LIST_SELECTORS['table'])
            if tables.count() == 0:
                return vehicles
            
            logger.info("Extracting vehicles from table...")
            table = tables.first
            
            # Get headers
            headers = table.locator('thead th, thead td')
            header_texts = [h.inner_text().strip() for h in headers.all()]
            logger.debug(f"Table headers: {header_texts}")
            
            # Get rows
            rows = table.locator(VEHICLE_LIST_SELECTORS['rows'])
            row_count = rows.count()
            logger.info(f"Found {row_count} vehicle rows")
            
            for i in range(row_count):
                row = rows.nth(i)
                cells = row.locator('td')
                cell_texts = [c.inner_text().strip() for c in cells.all()]
                
                # Try to identify vehicle plate/identifier
                vehicle_data = self._parse_vehicle_row(header_texts, cell_texts, row)
                if vehicle_data:
                    vehicles.append(vehicle_data)
            
        except Exception as e:
            logger.debug(f"Error extracting from table: {e}")
        
        return vehicles
    
    def _extract_from_list(self) -> List[Dict[str, str]]:
        """Extract vehicles from list/card structure."""
        vehicles = []
        
        try:
            # Look for list items or cards
            items = self.page.locator('[class*="list"] li, [class*="card"], [class*="vehicle"], [class*="veiculo"]')
            count = items.count()
            
            if count > 0:
                logger.info(f"Extracting vehicles from list/cards ({count} items)...")
                
                for i in range(count):
                    item = items.nth(i)
                    text = item.inner_text()
                    
                    # Try to extract vehicle identifier
                    vehicle_data = self._parse_vehicle_text(text, item)
                    if vehicle_data:
                        vehicles.append(vehicle_data)
        
        except Exception as e:
            logger.debug(f"Error extracting from list: {e}")
        
        return vehicles
    
    def _extract_from_links(self) -> List[Dict[str, str]]:
        """Extract vehicles from clickable links/buttons."""
        vehicles = []
        
        try:
            # Look for links that might lead to vehicle details
            links = self.page.locator(VEHICLE_LIST_SELECTORS['vehicle_link'])
            count = links.count()
            
            if count > 0:
                logger.info(f"Found {count} potential vehicle links")
                
                # Sample first few links for debugging
                sample_count = min(5, count)
                logger.debug(f"Sample of first {sample_count} links:")
                for i in range(sample_count):
                    link = links.nth(i)
                    text = link.inner_text().strip()
                    logger.debug(f"  Link {i}: '{text[:80]}'")
                
                for i in range(min(count, 100)):  # Limit to first 100
                    link = links.nth(i)
                    text = link.inner_text().strip()
                    href = link.get_attribute('href') or ''
                    
                    # Try to extract vehicle plate from text (more flexible)
                    plate = self._extract_plate_from_text(text)
                    if plate:
                        vehicles.append({
                            'plate': plate,
                            'identifier': plate,
                            'href': href,
                            'element_index': i,
                            'raw_text': text[:100]  # Store first 100 chars for debugging
                        })
                        logger.debug(f"Extracted vehicle {len(vehicles)}: {plate} from text '{text[:50]}'")
        
        except Exception as e:
            logger.debug(f"Error extracting from links: {e}")
        
        return vehicles
    
    def _extract_plate_from_text(self, text: str) -> Optional[str]:
        """Extract vehicle plate from text using flexible patterns."""
        if not text:
            return None
        
        # Brazilian plate patterns (without anchors to allow partial matches)
        patterns = [
            r'[A-Z]{3}-?\d{4}',  # Old format: ABC-1234 or ABC1234
            r'[A-Z]{3}\d{1}[A-Z]\d{2}',  # Mercosul format: ABC1D23
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.upper())
            if match:
                plate = match.group().upper()
                # Normalize: remove dashes for consistency
                plate = plate.replace('-', '')
                return plate
        
        return None
    
    def _extract_using_regex(self) -> List[Dict[str, str]]:
        """Extract vehicles using regex patterns on page text."""
        vehicles = []
        
        try:
            page_text = self.page.inner_text('body')
            
            # Use the same extraction method
            found_plates = set()
            lines = page_text.split('\n')
            
            for line in lines:
                plate = self._extract_plate_from_text(line)
                if plate and plate not in found_plates:
                    found_plates.add(plate)
                    vehicles.append({
                        'plate': plate,
                        'identifier': plate,
                        'extraction_method': 'regex'
                    })
            
            if vehicles:
                logger.info(f"Extracted {len(vehicles)} vehicles using regex")
        
        except Exception as e:
            logger.debug(f"Error extracting with regex: {e}")
        
        return vehicles
    
    def _parse_vehicle_row(self, headers: List[str], cells: List[str], row_element) -> Optional[Dict[str, str]]:
        """Parse a table row to extract vehicle information."""
        vehicle_data = {}
        
        # Create a dict from headers and cells
        row_dict = dict(zip(headers, cells))
        
        # Look for common vehicle identifier fields
        identifier_fields = ['placa', 'plate', 'veiculo', 'vehicle', 'identificador', 'id']
        
        for field in identifier_fields:
            for key, value in row_dict.items():
                if field.lower() in key.lower() and value.strip():
                    vehicle_data['plate'] = value.strip()
                    vehicle_data['identifier'] = value.strip()
                    break
        
        # If no identifier found, try to find it in cell values
        if 'plate' not in vehicle_data:
            for cell in cells:
                if self._is_vehicle_identifier(cell):
                    vehicle_data['plate'] = cell
                    vehicle_data['identifier'] = cell
                    break
        
        # Store all row data
        vehicle_data['raw_data'] = row_dict
        
        # Try to get clickable element (link to fines)
        try:
            link = row_element.locator('a, button')
            if link.count() > 0:
                vehicle_data['href'] = link.first.get_attribute('href') or ''
        except:
            pass
        
        return vehicle_data if 'plate' in vehicle_data else None
    
    def _parse_vehicle_text(self, text: str, element) -> Optional[Dict[str, str]]:
        """Parse text to extract vehicle information."""
        # Look for vehicle plate pattern in text
        patterns = [
            r'[A-Z]{3}-?\d{4}',
            r'[A-Z]{3}\d{1}[A-Z]\d{2}',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                plate = match.group().upper()
                vehicle_data = {
                    'plate': plate,
                    'identifier': plate,
                    'raw_text': text[:200]  # First 200 chars
                }
                
                # Try to get link
                try:
                    link = element.locator('a, button')
                    if link.count() > 0:
                        vehicle_data['href'] = link.first.get_attribute('href') or ''
                except:
                    pass
                
                return vehicle_data
        
        return None
    
    def _is_vehicle_identifier(self, text: str) -> bool:
        """Check if text looks like a vehicle plate/identifier."""
        if not text or len(text) < 6:
            return False
        
        # Use the extraction method to check
        return self._extract_plate_from_text(text) is not None
    
    def navigate_to_vehicle_fines(self, vehicle: Dict[str, str]) -> bool:
        """
        Navigate to fines page for a specific vehicle.
        
        Args:
            vehicle: Vehicle dictionary with at least 'plate' or 'href'.
        
        Returns:
            True if navigation successful, False otherwise.
        """
        try:
            # If vehicle has an href, use it
            if 'href' in vehicle and vehicle['href']:
                logger.info(f"Navigating to vehicle fines via href: {vehicle['href']}")
                try:
                    self.page.goto(vehicle['href'], wait_until="load", timeout=DELAYS.get('navigation_timeout', 60000))
                except PlaywrightTimeoutError:
                    self.page.goto(vehicle['href'], wait_until="domcontentloaded", timeout=30000)
                time.sleep(DELAYS['page_load'])
                return True
            
            # Otherwise, try to find and click the vehicle link
            plate = vehicle.get('plate') or vehicle.get('identifier')
            if plate:
                logger.info(f"Looking for vehicle link: {plate}")
                # Try to find link containing the plate
                link = self.page.locator(f'a, button').filter(has_text=plate)
                if link.count() > 0:
                    link.first.click()
                    time.sleep(DELAYS['after_click'])
                    # Use "load" instead of "networkidle"
                    try:
                        self.page.wait_for_load_state("load", timeout=DELAYS.get('navigation_timeout', 60000))
                    except PlaywrightTimeoutError:
                        self.page.wait_for_load_state("domcontentloaded", timeout=30000)
                    time.sleep(DELAYS['page_load'])
                    return True
            
            logger.warning(f"Could not navigate to fines for vehicle: {vehicle}")
            return False
            
        except Exception as e:
            logger.error(f"Error navigating to vehicle fines: {e}")
            return False



