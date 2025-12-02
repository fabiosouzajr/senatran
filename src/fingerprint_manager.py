"""
Fingerprint manager for browser fingerprint randomization.
Generates realistic browser fingerprints to avoid detection.
"""

import random
import logging
from typing import Dict, Any
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

# Common viewport sizes (realistic resolutions)
COMMON_VIEWPORTS = [
    {'width': 1920, 'height': 1080},  # Full HD
    {'width': 1366, 'height': 768},   # Common laptop
    {'width': 1536, 'height': 864},   # Common laptop
    {'width': 1440, 'height': 900},   # MacBook
    {'width': 1600, 'height': 900},   # HD+
    {'width': 1280, 'height': 720},   # HD
    {'width': 2560, 'height': 1440}, # 2K
]

# Common timezones (Brazil and common ones)
COMMON_TIMEZONES = [
    'America/Sao_Paulo',
    'America/Manaus',
    'America/Fortaleza',
    'America/Recife',
    'America/Bahia',
    'America/Campo_Grande',
    'America/Cuiaba',
    'America/Belem',
    'America/Araguaina',
    'America/Maceio',
    'America/Natal',
    'America/Porto_Velho',
    'America/Rio_Branco',
    'America/Boa_Vista',
    'America/Santarem',
    'America/Eirunepe',
    'America/Acre',
]

# Common locales
COMMON_LOCALES = [
    'pt-BR',
    'pt-BR,pt',
    'pt-BR,en-US,en',
    'en-US,en',
]

# Screen color depths
COLOR_DEPTHS = [24, 32]

# Screen pixel ratios
PIXEL_RATIOS = [1, 1.25, 1.5, 2, 2.5, 3]


class FingerprintManager:
    """Manages browser fingerprint generation and randomization."""
    
    def __init__(self):
        """Initialize fingerprint manager."""
        try:
            self.ua = UserAgent()
        except Exception as e:
            logger.warning(f"Failed to initialize UserAgent: {e}. Using fallback.")
            self.ua = None
    
    def generate_fingerprint(self) -> Dict[str, Any]:
        """
        Generate a random but realistic browser fingerprint.
        
        Returns:
            Dictionary containing fingerprint properties.
        """
        fingerprint = {
            'user_agent': self._get_user_agent(),
            'viewport': random.choice(COMMON_VIEWPORTS),
            'timezone': random.choice(COMMON_TIMEZONES),
            'locale': random.choice(COMMON_LOCALES),
            'color_depth': random.choice(COLOR_DEPTHS),
            'pixel_ratio': random.choice(PIXEL_RATIOS),
            'platform': self._get_platform(),
            'languages': self._get_languages(),
        }
        
        logger.debug(f"Generated fingerprint: {fingerprint}")
        return fingerprint
    
    def _get_user_agent(self) -> str:
        """Get a random user agent string."""
        if self.ua:
            try:
                return self.ua.random
            except Exception:
                pass
        
        # Fallback user agents (Chrome on Windows)
        fallback_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        ]
        return random.choice(fallback_agents)
    
    def _get_platform(self) -> str:
        """Get a random platform string."""
        platforms = [
            'Win32',
            'Linux x86_64',
        ]
        return random.choice(platforms)
    
    def _get_languages(self) -> list:
        """Get a random language list."""
        language_sets = [
            ['pt-BR', 'pt', 'en-US', 'en'],
            ['pt-BR', 'pt'],
            ['en-US', 'en', 'pt-BR', 'pt'],
        ]
        return random.choice(language_sets)
    
    def get_cdp_stealth_script(self) -> str:
        """
        Get Chrome DevTools Protocol script to apply stealth features.
        
        Returns:
            JavaScript code to inject for stealth.
        """
        return """
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
        
        // Override toString methods
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
    
    def apply_fingerprint_to_context(self, context, fingerprint: Dict[str, Any]) -> None:
        """
        Apply fingerprint to Playwright browser context.
        
        Args:
            context: Playwright browser context.
            fingerprint: Fingerprint dictionary.
        """
        try:
            # Set user agent
            context.set_extra_http_headers({
                'Accept-Language': fingerprint['locale'],
            })
            
            # Inject stealth script on every page
            context.add_init_script(self.get_cdp_stealth_script())
            
            logger.info(f"Applied fingerprint to context: UA={fingerprint['user_agent'][:50]}...")
        except Exception as e:
            logger.warning(f"Error applying fingerprint: {e}")

