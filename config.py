"""
Configuration file for the Playwright browser automation project.
All application variables and parameters are defined here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

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

