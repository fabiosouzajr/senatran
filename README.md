# Playwright Browser Automation Project

A Python project for browser automation using Playwright with persistent storage (cookies, cache, plugins) to behave like a normal user browser.

## Features

- Opens a browser window to a configured URL
- Maintains persistent cookies, cache, and browser plugins across sessions
- Human-like browser behavior (no automation detection flags)
- Waits for user input before proceeding with automation
- Configurable browser type, visibility, and settings

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## Setup

### Windows (PowerShell)

1. Run the setup script:
   ```powershell
   .\setup.ps1
   ```

2. Activate the virtual environment:
   ```powershell
   .\activate.ps1
   ```
   Or manually:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

### Linux/macOS (Bash)

1. Make the setup script executable:
   ```bash
   chmod +x setup.sh
   ```

2. Run the setup script:
   ```bash
   ./setup.sh
   ```

3. Activate the virtual environment:
   ```bash
   source activate.sh
   ```
   Or manually:
   ```bash
   source venv/bin/activate
   ```

### Manual Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

2. Activate the virtual environment:
   - Windows: `venv\Scripts\Activate.ps1`
   - Linux/macOS: `source venv/bin/activate`

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install Playwright browsers:
   ```bash
   playwright install chromium
   ```

## Configuration

All configuration is managed in `config.py`. You can also use environment variables or a `.env` file to override defaults.

### Key Configuration Options

- `BROWSER_TYPE`: Browser to use (chromium, firefox, webkit) - default: chromium
- `BROWSER_HEADLESS`: Run browser in headless mode (true/false) - default: false
- `TARGET_URL`: URL to open when script starts - default: https://portalservicos.senatran.serpro.gov.br/#/home
- `USER_DATA_DIR`: Directory for persistent browser data - default: .playwright_user_data
- `VIEWPORT_WIDTH` / `VIEWPORT_HEIGHT`: Browser viewport size
- `WAIT_MESSAGE`: Message displayed while waiting for user input

### Using Environment Variables

Create a `.env` file in the project root (see `.env.example`):

```env
BROWSER_TYPE=chromium
BROWSER_HEADLESS=false
TARGET_URL=https://portalservicos.senatran.serpro.gov.br/#/home
USER_DATA_DIR=.playwright_user_data
```

## Usage

1. Ensure the virtual environment is activated
2. Run the main script:
   ```bash
   python main.py
   ```

3. The browser will open and navigate to the configured URL
4. Press Enter in the terminal to continue with automation
5. Add your automation code in `main.py` after the input wait

## Project Structure

```
.
├── main.py              # Main automation script
├── config.py            # Configuration file
├── requirements.txt     # Python dependencies
├── setup.ps1            # Windows setup script
├── setup.sh             # Linux/macOS setup script
├── activate.ps1         # Windows activation script
├── activate.sh          # Linux/macOS activation script
├── .gitignore           # Git ignore patterns
├── .env.example         # Example environment variables
├── README.md            # This file
└── venv/                # Virtual environment (created by setup)
```

## Browser Persistence

The browser uses a persistent user data directory (`.playwright_user_data/` by default) to store:
- Cookies
- Cache
- Browser plugins/extensions
- Local storage
- Session storage

This ensures that the browser behaves like a normal user browser with persistent state across sessions.

## Customization

To add custom automation after the browser opens:

1. Edit `main.py`
2. Add your automation code after the `input()` call
3. Use the `page` object to interact with the browser

Example:
```python
# After input() in main.py
await page.click("button#submit")
await page.fill("input#username", "your_username")
```

## Troubleshooting

### Browser not installing
If Playwright browsers fail to install, try:
```bash
playwright install --with-deps chromium
```

### Permission errors on Linux
You may need to install system dependencies:
```bash
playwright install-deps
```

### Virtual environment not activating
- Windows: Ensure execution policy allows scripts: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
- Linux/macOS: Ensure the script is executable: `chmod +x activate.sh`

## License

This project is for educational and automation purposes.

