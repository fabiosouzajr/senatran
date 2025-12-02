"""
Fine extractor to extract fine information from Senatran portal.
"""

import time
import logging
import re
from typing import List, Dict, Optional
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from config import (
    FINE_DETAIL_SELECTORS,
    DELAYS,
)

logger = logging.getLogger(__name__)

# Field name mappings (Portuguese to English/internal)
FIELD_MAPPINGS = {
    'Órgão Autuador': 'orgao_autuador',
    'Órgão Competente/Responsável': 'orgao_competente',
    'Local da Infração': 'local_infracao',
    'Data/Hora do Cometimento da Infração': 'data_hora_cometimento',
    'Número do Auto de Infração': 'numero_auto',
    'Código da Infração': 'codigo_infracao',
    'Número RENAINF': 'numero_renainf',
    'Valor Original': 'valor_original',
    'Data da Notificação de Autuação': 'data_notificacao_autuacao',
    'Data Limite para Interposição de Defesa Prévia': 'data_limite_defesa_previa',
    'Data Limite para Identificação do Condutor Infrator': 'data_limite_identificacao_condutor',
    'Data da Notificação de Penalidade': 'data_notificacao_penalidade',
    'Data Limite para Interposição de Recurso': 'data_limite_recurso',
    'Data do Vencimento do Desconto': 'data_vencimento_desconto',
}


class FineExtractor:
    """Extracts fine information from Senatran portal."""
    
    def __init__(self, page: Page):
        """
        Initialize fine extractor.
        
        Args:
            page: Playwright page object.
        """
        self.page = page
    
    def extract_fines(self, vehicle_plate: str) -> List[Dict[str, str]]:
        """
        Extract all fines for the current vehicle page.
        
        Args:
            vehicle_plate: Vehicle plate for associating fines.
        
        Returns:
            List of dictionaries containing fine information.
        """
        logger.info(f"Extracting fines for vehicle: {vehicle_plate}")
        
        fines = []
        
        try:
            # Wait for page to load
            time.sleep(DELAYS['page_load'])
            
            # Try multiple extraction methods
            # Method 1: Extract from table
            table_fines = self._extract_from_table(vehicle_plate)
            if table_fines:
                fines.extend(table_fines)
            
            # Method 2: Extract from cards/list
            if not fines:
                card_fines = self._extract_from_cards(vehicle_plate)
                if card_fines:
                    fines.extend(card_fines)
            
            # Method 3: Extract from detail view
            if not fines:
                detail_fines = self._extract_from_detail_view(vehicle_plate)
                if detail_fines:
                    fines.extend(detail_fines)
            
            logger.info(f"Extracted {len(fines)} fines for vehicle {vehicle_plate}")
            return fines
            
        except Exception as e:
            logger.error(f"Error extracting fines: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _extract_from_table(self, vehicle_plate: str) -> List[Dict[str, str]]:
        """Extract fines from table structure."""
        fines = []
        
        try:
            tables = self.page.locator(FINE_DETAIL_SELECTORS['fine_table'])
            if tables.count() == 0:
                return fines
            
            logger.info("Extracting fines from table...")
            table = tables.first
            
            # Get headers
            headers = table.locator('thead th, thead td')
            header_texts = [h.inner_text().strip() for h in headers.all()]
            logger.debug(f"Table headers: {header_texts}")
            
            # Get rows (skip header)
            rows = table.locator(FINE_DETAIL_SELECTORS['fine_rows'])
            row_count = rows.count()
            logger.info(f"Found {row_count} fine rows")
            
            for i in range(row_count):
                row = rows.nth(i)
                cells = row.locator('td')
                cell_texts = [c.inner_text().strip() for c in cells.all()]
                
                # Parse row into fine data
                fine_data = self._parse_fine_row(header_texts, cell_texts, vehicle_plate)
                if fine_data:
                    fines.append(fine_data)
            
        except Exception as e:
            logger.debug(f"Error extracting from table: {e}")
        
        return fines
    
    def _extract_from_cards(self, vehicle_plate: str) -> List[Dict[str, str]]:
        """Extract fines from card/list structure."""
        fines = []
        
        try:
            cards = self.page.locator(FINE_DETAIL_SELECTORS['fine_cards'])
            count = cards.count()
            
            if count > 0:
                logger.info(f"Extracting fines from cards ({count} cards)...")
                
                for i in range(count):
                    card = cards.nth(i)
                    fine_data = self._parse_fine_card(card, vehicle_plate)
                    if fine_data:
                        fines.append(fine_data)
        
        except Exception as e:
            logger.debug(f"Error extracting from cards: {e}")
        
        return fines
    
    def _extract_from_detail_view(self, vehicle_plate: str) -> List[Dict[str, str]]:
        """Extract fine from detail view (single fine displayed)."""
        fines = []
        
        try:
            # Look for field-value pairs
            page_text = self.page.inner_text('body')
            
            fine_data = {'vehicle_plate': vehicle_plate}
            
            # Try to extract each required field
            for pt_field, en_field in FIELD_MAPPINGS.items():
                value = self._extract_field_value(pt_field, page_text)
                if value:
                    fine_data[en_field] = value
                    # Special handling for renainf (used as primary key)
                    if en_field == 'numero_renainf':
                        fine_data['renainf'] = value
            
            # If we found at least RENAINF, consider it a valid fine
            if 'renainf' in fine_data or 'numero_renainf' in fine_data:
                renainf = fine_data.get('renainf') or fine_data.get('numero_renainf')
                if not renainf:
                    renainf = fine_data.get('numero_auto', 'UNKNOWN')
                fine_data['renainf'] = renainf
                fines.append(fine_data)
        
        except Exception as e:
            logger.debug(f"Error extracting from detail view: {e}")
        
        return fines
    
    def _parse_fine_row(self, headers: List[str], cells: List[str], vehicle_plate: str) -> Optional[Dict[str, str]]:
        """Parse a table row into fine data dictionary."""
        if len(headers) != len(cells):
            logger.debug("Header/cell count mismatch")
            return None
        
        fine_data = {'vehicle_plate': vehicle_plate}
        
        # Create mapping from headers to cells
        for header, cell_value in zip(headers, cells):
            header_lower = header.lower()
            cell_value = cell_value.strip()
            
            # Map header to field name
            for pt_field, en_field in FIELD_MAPPINGS.items():
                if pt_field.lower() in header_lower or any(word in header_lower for word in pt_field.lower().split()):
                    fine_data[en_field] = cell_value
                    # Special handling for renainf
                    if en_field == 'numero_renainf':
                        fine_data['renainf'] = cell_value
                    break
        
        # Ensure we have renainf (use numero_auto as fallback)
        if 'renainf' not in fine_data:
            renainf = fine_data.get('numero_renainf') or fine_data.get('numero_auto', 'UNKNOWN')
            fine_data['renainf'] = renainf
        
        # Only return if we have at least some data
        if len(fine_data) > 2:  # More than just vehicle_plate and renainf
            return fine_data
        
        return None
    
    def _parse_fine_card(self, card_element, vehicle_plate: str) -> Optional[Dict[str, str]]:
        """Parse a card element into fine data dictionary."""
        fine_data = {'vehicle_plate': vehicle_plate}
        card_text = card_element.inner_text()
        
        # Try to extract each field from card text
        for pt_field, en_field in FIELD_MAPPINGS.items():
            value = self._extract_field_value(pt_field, card_text)
            if value:
                fine_data[en_field] = value
                if en_field == 'numero_renainf':
                    fine_data['renainf'] = value
        
        # Ensure renainf exists
        if 'renainf' not in fine_data:
            renainf = fine_data.get('numero_renainf') or fine_data.get('numero_auto', 'UNKNOWN')
            fine_data['renainf'] = renainf
        
        # Try to extract from structured elements (labels/values)
        try:
            labels = card_element.locator('label, [class*="label"], dt')
            values = card_element.locator('[class*="value"], dd, span')
            
            for i in range(min(labels.count(), values.count())):
                label_text = labels.nth(i).inner_text().strip()
                value_text = values.nth(i).inner_text().strip()
                
                for pt_field, en_field in FIELD_MAPPINGS.items():
                    if pt_field.lower() in label_text.lower():
                        fine_data[en_field] = value_text
                        if en_field == 'numero_renainf':
                            fine_data['renainf'] = value_text
        except:
            pass
        
        if len(fine_data) > 2:
            return fine_data
        
        return None
    
    def _extract_field_value(self, field_name: str, text: str) -> Optional[str]:
        """
        Extract field value from text by looking for field label.
        
        Args:
            field_name: Portuguese field name to search for.
            text: Text to search in.
        
        Returns:
            Extracted value or None.
        """
        # Look for field name followed by value
        # Pattern: "Field Name: Value" or "Field Name\nValue"
        patterns = [
            rf'{re.escape(field_name)}\s*[:]\s*([^\n]+)',
            rf'{re.escape(field_name)}\s+([^\n]+)',
            rf'{re.escape(field_name)}\n\s*([^\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                value = match.group(1).strip()
                # Clean up value (remove extra whitespace, colons, etc.)
                value = re.sub(r'\s+', ' ', value)
                if value and value != field_name:
                    return value
        
        return None
    
    def expand_fine_details(self, fine_element) -> bool:
        """
        Expand fine details if they are in a collapsible section.
        
        Args:
            fine_element: Playwright locator for fine element.
        
        Returns:
            True if expansion was attempted/successful.
        """
        try:
            # Look for expand buttons
            expand_buttons = fine_element.locator(
                '[class*="expand"], [class*="more"], [aria-expanded="false"], button:has-text("ver mais"), button:has-text("detalhes")'
            )
            
            if expand_buttons.count() > 0:
                logger.debug("Expanding fine details...")
                expand_buttons.first.click()
                time.sleep(DELAYS['after_click'])
                return True
        
        except Exception as e:
            logger.debug(f"Error expanding fine details: {e}")
        
        return False



