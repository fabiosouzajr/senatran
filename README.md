# Senatran Fine Automation

Automated system for extracting fine information from the Senatran portal and storing it in a SQLite database.

## Overview

This system automates the process of:
1. Logging into the Senatran portal using certificate-based authentication
2. Iterating through all vehicles
3. Extracting fine information for each vehicle
4. Storing the data in a SQLite database

## Features

- Certificate-based authentication through SSO
- Automated vehicle iteration
- Fine data extraction with all required fields
- SQLite database storage with upsert logic
- Terminal-based CLI interface
- Cross-platform support (Windows and Linux)
- Rate limiting to avoid triggering captchas
- Comprehensive logging

## Installation

### Prerequisites

- Python 3.8 or higher
- Digital certificate file in `./cert` folder (.p12, .pfx, or .pem with private key)
- Digital certificate installed in your system certificate store (required for SSO authentication)

### Quick Certificate Installation

Before running the automation, install your certificate:

```bash
python install_certificate.py
```

This script will:
- Find compatible certificate files in `./cert` folder
- Check for required dependencies
- Prompt for password if needed
- Install the certificate to the browser's certificate store
- Playwright browser binaries

### Setup

1. Clone or navigate to the project directory:
```bash
cd /home/fabio/git/senatran
```

2. **Activate the virtual environment** (recommended):

   **On Linux/Mac:**
   ```bash
   source activate.sh
   ```
   Or manually:
   ```bash
   source .venv/bin/activate
   ```

   **On Windows (PowerShell):**
   ```powershell
   .\activate.ps1
   ```
   Or manually:
   ```powershell
   .venv\Scripts\Activate.ps1
   ```

   **Note:** The activation scripts will automatically create the virtual environment and install dependencies if they don't exist.

3. If not using the activation script, install Python dependencies manually:
```bash
pip install -r requirements.txt
```

4. Install Playwright browsers:
```bash
playwright install chromium
```

## Usage

### Exploratory Scripts

Before running the main automation, you may want to explore the website structure:

1. **Explore login flow:**
```bash
python exploratory/explore_login.py
```

2. **Explore vehicle list:**
```bash
python exploratory/explore_vehicle_list.py
```

3. **Explore fine details:**
```bash
python exploratory/explore_fine_details.py
```

### Main Automation

Run the main automation script:

```bash
# Option 1: Using the convenience script from project root
python run.py

# Option 2: Direct execution from src directory
python src/main.py

# With visible browser (recommended for certificate selection)
python run.py
# or
python src/main.py

# In headless mode (may not work with certificate selection)
python run.py --headless
# or
python src/main.py --headless
```

## Configuration

Configuration is managed in `src/config.py`. Key settings include:

- **URLs**: Senatran and SSO URLs
- **Selectors**: CSS selectors for page elements (may need adjustment after exploration)
- **Delays**: Timing configuration for rate limiting
- **Browser settings**: Viewport, user agent, etc.

## Database

The SQLite database (`senatran_fines.db`) stores fine information with the following schema:

- `renainf` (PRIMARY KEY): RENAINF number
- `vehicle_plate`: Vehicle plate/identifier
- `orgao_autuador`: Issuing authority
- `orgao_competente`: Competent authority
- `local_infracao`: Infraction location
- `data_hora_cometimento`: Date/time of infraction
- `numero_auto`: Infraction number
- `codigo_infracao`: Infraction code
- `valor_original`: Original value
- `data_notificacao_autuacao`: Notification date
- `data_limite_defesa_previa`: Defense deadline
- `data_limite_identificacao_condutor`: Driver identification deadline
- `data_notificacao_penalidade`: Penalty notification date
- `data_limite_recurso`: Appeal deadline
- `data_vencimento_desconto`: Discount expiration date
- `last_updated`: Timestamp of last update

## Project Structure

```
senatran/
├── exploratory/
│   ├── explore_login.py          # Login flow exploration
│   ├── explore_vehicle_list.py   # Vehicle list exploration
│   └── explore_fine_details.py   # Fine details exploration
├── src/
│   ├── auth_handler.py           # Authentication handler
│   ├── vehicle_scraper.py         # Vehicle list scraper
│   ├── fine_extractor.py          # Fine data extractor
│   ├── database.py                # Database manager
│   ├── config.py                  # Configuration
│   └── main.py                    # Main controller
├── requirements.txt               # Python dependencies
├── README.md                      # This file
└── senatran_fines.db             # SQLite database (created on first run)
```

## Certificate Authentication

The system handles certificate authentication through the SSO portal. The certificate file is located at `cert/certificado.crt`.

**Important**: For SSO authentication to work automatically, the certificate must be installed in your system's certificate store. The `.crt` file is used for reference, but the browser needs the certificate in the system store to automatically select it.

### Certificate Installation

**Quick Installation (Recommended):**

Use the provided installation script:

```bash
python install_certificate.py
```

This script will:
- Automatically find compatible certificate files in `./cert` folder
- Check for required dependencies
- Prompt for password if needed
- Install the certificate to the appropriate certificate store
- Work on Linux, Windows, and macOS

**Manual Installation - Linux (for browser use with Playwright/Chromium):**

The certificate needs to be installed in Chromium's NSS database. Here are the steps:

1. **Install NSS tools** (if not already installed):
```bash
# Ubuntu/Debian
sudo apt-get install libnss3-tools

# Fedora/RHEL
sudo dnf install nss-tools
```

2. **Create NSS database** (if it doesn't exist):
```bash
mkdir -p ~/.pki/nssdb
certutil -d sql:~/.pki/nssdb -N --empty-password
```

3. **Import the certificate** (if you have a .p12 or .pfx file):
```bash
# If you have a .p12/.pfx file with private key:
pk12util -d sql:~/.pki/nssdb -i certificado.p12

# If you only have .crt file, you need to convert it first or use a different method
```

4. **For .crt files**, you may need to:
   - Convert to PKCS#12 format first (requires private key)
   - Or use Chromium's certificate import feature manually:
     - Open Chromium
     - Go to Settings > Privacy and Security > Security > Manage certificates
     - Import your certificate

**Note**: Playwright uses Chromium, which uses the NSS database at `~/.pki/nssdb`. The certificate must be in this database for automatic selection.

**Alternative**: If you have a .pem file with both certificate and private key, you can convert it:
```bash
# Convert PEM to PKCS#12 (requires openssl)
openssl pkcs12 -export -out certificado.p12 -inkey certificado.key -in certificado.crt -name "novamobilidade"
# Then import:
pk12util -d sql:~/.pki/nssdb -i certificado.p12
```

**Windows:**
1. Double-click the `.crt` file
2. Click "Install Certificate"
3. Choose "Current User" or "Local Machine"
4. Select "Place all certificates in the following store"
5. Click "Browse" and select "Personal" or "Trusted Root Certification Authorities"
6. Complete the installation

The authentication process:
1. Navigate to Senatran home page
2. Click "Entrar com" button
3. Redirect to SSO login page
4. Trigger certificate selection dialog
5. Browser automatically selects certificate from system store (if installed)
6. Verify authentication success

**Note**: If the certificate is not in the system store, you may need to manually select it from the certificate dialog.

## Troubleshooting

### Authentication Issues

- Ensure your digital certificate is installed and accessible
- Run with visible browser (`--headless` flag not set) for certificate selection
- Check browser console for errors
- Verify certificate is valid and not expired

### Extraction Issues

- Run exploratory scripts to verify selectors are correct
- Website structure may have changed - update selectors in `config.py`
- Check logs in `senatran_automation.log`

### Rate Limiting

- If captchas are triggered, increase delays in `config.py`
- Reduce processing speed by increasing `DELAYS` values
- Process vehicles in smaller batches

## Logging

Logs are written to:
- Console (stdout)
- File: `senatran_automation.log`

Log levels can be configured in `config.py`.

## Development

After running exploratory scripts, you may need to update:

1. **Selectors** in `src/config.py` based on actual website structure
2. **Field mappings** in `src/fine_extractor.py` if field names differ
3. **Extraction logic** if website uses non-standard structures

## License

This project is for personal/internal use. Ensure compliance with Senatran's terms of service.

## Support

For issues or questions:
1. Check logs for error messages
2. Run exploratory scripts to verify website structure
3. Update selectors and configuration as needed

