"""
Configuration file for the Playwright browser automation project.
All application variables and parameters are defined here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "senatran_fines.db"
LOGS_DIR = BASE_DIR / "logs"

# Project root directory
PROJECT_ROOT = Path(__file__).parent

# Browser Configuration
BROWSER_TYPE = os.getenv("BROWSER_TYPE", "chromium")  # Options: chromium, firefox, webkit
BROWSER_HEADLESS = os.getenv("BROWSER_HEADLESS", "false").lower() == "true"

# Target URL
TARGET_URL = os.getenv("TARGET_URL", "https://portalservicos.senatran.serpro.gov.br/#/home")
FINES_URL = os.getenv("FINES_URL", "https://portalservicos.senatran.serpro.gov.br/#/infracoes/consultar/veiculo")

# User Data Directory (for persistent cookies, cache, plugins)
USER_DATA_DIR = PROJECT_ROOT / os.getenv("USER_DATA_DIR", ".playwright_user_data")

# Browser configuration
BROWSER_CONFIG = {
    'headless': BROWSER_HEADLESS,  # Use environment variable
    'slow_mo': 1000,  # Slow down actions by 1 second (helps avoid detection)
    'viewport': {'width': 1280, 'height': 720},  # Viewport size (smaller to allow scrollbars)
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'window_size': {'width': 1280, 'height': 720},  # Window size (not maximized, matches viewport)
    'no_viewport': False,  # Set to True to use window size instead of viewport
}

# Timing configuration (in seconds)
DELAYS = {
    'page_load': 8,  # Wait after page load (increased significantly to avoid captcha)
    'after_click': 5,  # Wait after clicking elements (increased to avoid captcha)
    'between_actions': 8,  # Wait between actions (anti-captcha, increased)
    'between_vehicles': 3,  # Wait between processing vehicles
    'certificate_selection': 10,  # Wait for certificate selection dialog
    'authentication_timeout': 60,  # Timeout for authentication
    'navigation_timeout': 60000,  # Navigation timeout in milliseconds (60 seconds)
    'network_idle_timeout': 30000,  # Network idle timeout in milliseconds (fallback)
    'before_certificate_click': 10,  # Wait before clicking certificate button (anti-captcha, increased significantly)
    'before_login_click': 10,  # Wait before clicking login button (anti-captcha, increased)
    'before_captcha_solve': 30,  # Wait before solving CAPTCHA (critical - let page stabilize) - INCREASED for hCaptcha
    'after_captcha_appears': 25,  # Wait after CAPTCHA appears before interacting - INCREASED for hCaptcha
    'before_captcha_interaction': 15,  # Wait before clicking/interacting with CAPTCHA - INCREASED for hCaptcha
    'after_erl_error': 30,  # Wait after ERL0033800 error before retrying - NEW
    'hcaptcha_extra_delay': 20,  # Extra delay specifically for hCaptcha - NEW
}

# Browser Launch Arguments for Human-like Behavior
# These arguments help make the browser appear more like a normal user browser
BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",  # Remove automation flags
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-web-security",
    "--disable-features=IsolateOrigins,site-per-process",
    "--disable-site-isolation-trials",
    # Additional anti-detection flags
    "--disable-infobars",  # Disable "Chrome is being controlled" infobar
    "--disable-notifications",  # Disable notifications
    "--disable-popup-blocking",  # Allow popups (more human-like)
    "--lang=pt-BR",  # Set language to Portuguese (Brazil)
]

# Viewport Configuration
VIEWPORT_WIDTH = int(os.getenv("VIEWPORT_WIDTH", "1280"))
VIEWPORT_HEIGHT = int(os.getenv("VIEWPORT_HEIGHT", "720"))

# User Agent (optional - Playwright uses realistic defaults)
USER_AGENT = os.getenv("USER_AGENT", None)  # None = use Playwright default

# Timeout Settings (in milliseconds)
NAVIGATION_TIMEOUT = int(os.getenv("NAVIGATION_TIMEOUT", "30000"))  # 30 seconds
DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "30000"))  # 30 seconds

# Wait for User Input
WAIT_MESSAGE = os.getenv(
    "WAIT_MESSAGE",
    "Browser opened. Press Enter to continue with automation..."
)

# Human Behavior Configuration (to avoid CAPTCHA)
ENABLE_HUMAN_BEHAVIOR = os.getenv("ENABLE_HUMAN_BEHAVIOR", "true").lower() == "true"
MIN_DELAY_MS = int(os.getenv("MIN_DELAY_MS", "500"))  # Minimum delay between actions
MAX_DELAY_MS = int(os.getenv("MAX_DELAY_MS", "2000"))  # Maximum delay between actions
MIN_READING_TIME = float(os.getenv("MIN_READING_TIME", "1.0"))  # Minimum reading time in seconds
MAX_READING_TIME = float(os.getenv("MAX_READING_TIME", "3.0"))  # Maximum reading time in seconds

# Logging configuration
LOGGING_CONFIG = {
    'level': 'INFO',  # DEBUG, INFO, WARNING, ERROR
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': LOGS_DIR / 'senatran_automation.log',
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
    'enabled': ENABLE_HUMAN_BEHAVIOR,  # Use environment variable if set
    'use_variable_delays': True,  # Use variable delays instead of fixed
    'delay_variance': 0.3,  # Variance factor for delays (0.3 = ±30%)
    'simulate_mouse_movement': True,  # Simulate mouse movement before clicks
    'simulate_scrolling': True,  # Simulate human-like scrolling
    'simulate_typing': True,  # Simulate human-like typing speed
    'typing_speed': 0.1,  # Base typing speed in seconds per character
    'min_delay': MIN_DELAY_MS / 1000.0,  # Convert from ms to seconds
    'max_delay': MAX_DELAY_MS / 1000.0,  # Convert from ms to seconds
}

# Enhanced CAPTCHA configuration
CAPTCHA_CONFIG = {
    'detection_enabled': True,  # Enable CAPTCHA detection
    'auto_detect_types': True,  # Automatically detect CAPTCHA types
    'screenshot_on_detection': True,  # Take screenshot when CAPTCHA detected
    'screenshot_dir': LOGS_DIR / 'captcha_screenshots',  # Directory for screenshots
    'max_wait_time': 180,  # Maximum wait time for manual CAPTCHA solving (seconds)
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

# Anti-automation bypass configuration
ANTI_AUTOMATION_CONFIG = {
    'enabled': True,  # Enable anti-automation bypass features
    'use_enhanced_stealth': True,  # Use enhanced stealth JavaScript injection
    'remove_automation_flags': True,  # Remove Chrome automation flags
    'add_pre_action_delays': True,  # Add random delays before critical actions
    'pre_action_delay_min': 2,  # Minimum delay before actions (seconds)
    'pre_action_delay_max': 5,  # Maximum delay before actions (seconds)
    'use_cdp_stealth': True,  # Use Chrome DevTools Protocol for additional stealth
    'randomize_timing': True,  # Randomize all timing to avoid patterns
}

# CAPTCHA Solving Configuration
CAPTCHA_API_KEY = os.getenv("CAPTCHA_API_KEY", None)  # 2Captcha API key
ENABLE_CAPTCHA_SOLVING = os.getenv("ENABLE_CAPTCHA_SOLVING", "true").lower() == "true"
CAPTCHA_SERVICE = os.getenv("CAPTCHA_SERVICE", "2captcha")  # Service to use: 2captcha, anticaptcha, etc.
