"""
Configuration file for Senatran automation.
Contains URLs, selectors, delays, and other configuration parameters.
"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "senatran_fines.db"

# URLs
SENATRAN_HOME_URL = "https://portalservicos.senatran.serpro.gov.br/#/home"
SENATRAN_VEHICLE_LIST_URL = "https://portalservicos.senatran.serpro.gov.br/#/infracoes/consultar/veiculo"
SSO_LOGIN_URL = "https://sso.acesso.gov.br/login"

# Authentication selectors
ENTRAR_COM_BUTTON_SELECTOR = 'span.ml-1:has-text("Entrar com")'
CERTIFICATE_SELECTOR = '#login-certificate'  # Button with id="login-certificate" and text "Seu certificado digital"

# Browser configuration
BROWSER_CONFIG = {
    'headless': False,  # Set to True for headless mode (may not work with certificate selection)
    'slow_mo': 1000,  # Slow down actions by 1 second (helps avoid detection)
    'viewport': {'width': 1920, 'height': 1080},
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'window_size': {'width': 1280, 'height': 720},  # Window size (not maximized)
    'no_viewport': False,  # Set to True to use window size instead of viewport
}

# Timing configuration (in seconds)
DELAYS = {
    'page_load': 8,  # Wait after page load (increased to avoid captcha)
    'after_click': 5,  # Wait after clicking elements (increased to avoid captcha)
    'between_actions': 5,  # Wait between actions (anti-captcha, increased)
    'between_vehicles': 3,  # Wait between processing vehicles
    'certificate_selection': 10,  # Wait for certificate selection dialog
    'authentication_timeout': 60,  # Timeout for authentication
    'navigation_timeout': 60000,  # Navigation timeout in milliseconds (60 seconds)
    'network_idle_timeout': 30000,  # Network idle timeout in milliseconds (fallback)
    'before_certificate_click': 5,  # Wait before clicking certificate button (anti-captcha, increased)
    'before_login_click': 5,  # Wait before clicking login button (anti-captcha)
}

# Rate limiting (to avoid triggering captchas)
RATE_LIMITING = {
    'min_delay': 2,  # Minimum delay between requests
    'max_delay': 5,  # Maximum delay between requests
    'progressive_delay_on_error': True,  # Increase delay on errors
    'max_retries': 3,  # Maximum retries on failure
}

# Vehicle list selectors (to be updated after exploration)
VEHICLE_LIST_SELECTORS = {
    'table': 'table',
    'rows': 'tbody tr',
    'vehicle_link': 'a, button, [role="button"]',
    'pagination_next': 'button:has-text("próximo"), a:has-text(">")',
    'pagination_prev': 'button:has-text("anterior"), a:has-text("<")',
}

# Fine details selectors (to be updated after exploration)
FINE_DETAIL_SELECTORS = {
    'fine_table': 'table',
    'fine_rows': 'tbody tr',
    'fine_cards': '[class*="card"], [class*="fine"]',
    # Field mappings will be added after exploration
    'fields': {
        'orgao_autuador': None,  # To be determined
        'orgao_competente': None,
        'local_infracao': None,
        'data_hora_cometimento': None,
        'numero_auto': None,
        'codigo_infracao': None,
        'numero_renainf': None,
        'valor_original': None,
        'data_notificacao_autuacao': None,
        'data_limite_defesa_previa': None,
        'data_limite_identificacao_condutor': None,
        'data_notificacao_penalidade': None,
        'data_limite_recurso': None,
        'data_vencimento_desconto': None,
    }
}

# Login success indicators
LOGIN_SUCCESS_INDICATORS = [
    'text=/sair|logout|usuário|user/i',
    '[class*="user"]',
    '[class*="logout"]',
]

# Certificate configuration
CERTIFICATE_CONFIG = {
    'certificate_path': BASE_DIR / 'cert' / 'certificado.crt',  # Path to certificate file
    'certificate_pem_path': BASE_DIR / 'cert' / 'certificado_novamobilidade-25.pem',  # Alternative PEM certificate
    'certificate_name': 'novamobilidade',  # Certificate name pattern for auto-selection
    'certificate_password': os.getenv('CERTIFICATE_PASSWORD'),  # Optional: certificate password (required if PEM is encrypted)
    'use_system_store': True,  # Use system certificate store (required for SSO)
    'manual_selection_timeout': 60,  # Timeout for manual certificate selection (increased for password entry)
    'auto_select_certificate': True,  # Whether to auto-select certificate using automation
    'wait_for_redirect_timeout': 60,  # Timeout for waiting for redirect after certificate selection
}

# Database configuration
DATABASE_CONFIG = {
    'path': DB_PATH,
    'timeout': 20,  # SQLite timeout in seconds
}

# Logging configuration
LOGGING_CONFIG = {
    'level': 'INFO',  # DEBUG, INFO, WARNING, ERROR
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': BASE_DIR / 'senatran_automation.log',
}

# Stealth configuration
STEALTH_CONFIG = {
    'enabled': True,  # Enable stealth features
    'remove_webdriver': True,  # Remove webdriver property
    'override_plugins': True,  # Override navigator.plugins
    'override_languages': True,  # Override navigator.languages
    'override_permissions': True,  # Override permissions API
    'add_chrome_runtime': True,  # Add chrome.runtime object
    'override_webgl': True,  # Override WebGL fingerprinting
}

# Fingerprint configuration
FINGERPRINT_CONFIG = {
    'enabled': True,  # Enable fingerprint randomization
    'rotate_user_agent': True,  # Rotate user agent per session
    'randomize_viewport': True,  # Randomize viewport size
    'randomize_timezone': True,  # Randomize timezone
    'randomize_locale': True,  # Randomize locale
    'randomize_color_depth': True,  # Randomize color depth
    'randomize_pixel_ratio': True,  # Randomize pixel ratio
    'persist_per_session': True,  # Use same fingerprint for entire session
}

# Human behavior configuration
HUMAN_BEHAVIOR_CONFIG = {
    'enabled': True,  # Enable human behavior simulation
    'use_variable_delays': True,  # Use variable delays instead of fixed
    'delay_variance': 0.3,  # Variance factor for delays (0.3 = ±30%)
    'simulate_mouse_movement': True,  # Simulate mouse movement before clicks
    'simulate_scrolling': True,  # Simulate human-like scrolling
    'simulate_typing': True,  # Simulate human-like typing speed
    'typing_speed': 0.1,  # Base typing speed in seconds per character
    'min_delay': 1.0,  # Minimum delay for human delays (seconds)
    'max_delay': 3.0,  # Maximum delay for human delays (seconds)
}

# Enhanced CAPTCHA configuration
CAPTCHA_CONFIG = {
    'detection_enabled': True,  # Enable CAPTCHA detection
    'auto_detect_types': True,  # Automatically detect CAPTCHA types
    'screenshot_on_detection': True,  # Take screenshot when CAPTCHA detected
    'screenshot_dir': BASE_DIR / 'captcha_screenshots',  # Directory for screenshots
    'max_wait_time': 300,  # Maximum wait time for manual CAPTCHA solving (seconds)
    'check_interval': 2,  # How often to check for CAPTCHA solution (seconds)
    'retry_on_captcha': True,  # Retry operation after CAPTCHA is solved
    'max_retries': 3,  # Maximum retries after CAPTCHA
}

# Enhanced rate limiting with jitter
RATE_LIMITING_ENHANCED = {
    'min_delay': 2,  # Minimum delay between requests (seconds)
    'max_delay': 5,  # Maximum delay between requests (seconds)
    'use_jitter': True,  # Add random jitter to delays
    'jitter_factor': 0.2,  # Jitter factor (0.2 = ±20% variation)
    'progressive_delay_on_error': True,  # Increase delay on errors
    'max_delay_on_error': 10,  # Maximum delay after error (seconds)
    'max_retries': 3,  # Maximum retries on failure
    'backoff_multiplier': 1.5,  # Multiplier for exponential backoff
}



