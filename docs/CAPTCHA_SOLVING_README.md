# CAPTCHA Solving Integration

## Overview

This project includes automatic CAPTCHA solving using the 2Captcha service. When a CAPTCHA is detected on a page, it will be automatically solved and the solution injected into the page.

## Setup

### 1. Get a 2Captcha API Key

1. Sign up at [2Captcha.com](https://2captcha.com/?from=1234567)
2. Get your API key from the dashboard
3. Add funds to your account (CAPTCHAs cost ~$2.99 per 1000 solves)

### 2. Configure API Key

Add your API key to `.env` file:

```env
CAPTCHA_API_KEY=your_api_key_here
ENABLE_CAPTCHA_SOLVING=true
```

Or set it directly in `config.py`:

```python
CAPTCHA_API_KEY = "your_api_key_here"
```

### 3. Install Dependencies

The required dependency `aiohttp` should already be installed. If not:

```bash
pip install aiohttp
```

## How It Works

1. **Detection**: The scraper automatically detects CAPTCHAs on pages:
   - reCAPTCHA v2
   - reCAPTCHA v3
   - hCaptcha

2. **Solving**: When detected, the CAPTCHA is:
   - Submitted to 2Captcha service
   - Solved by human workers (takes 10-30 seconds)
   - Solution retrieved automatically

3. **Injection**: The solution is injected into the page:
   - Token is set in the form fields
   - Callbacks are triggered
   - Page can proceed normally

## Testing

Run the test script to verify everything works:

```bash
python test_captcha.py
```

This will:
- Check if API key is configured
- Test API connection
- Check account balance
- Detect CAPTCHAs on the test page
- Attempt to solve if found

## Usage

The CAPTCHA solving is automatically integrated into the scraper. It will:

1. Check for CAPTCHAs when navigating to FINES_URL
2. Check for CAPTCHAs when opening vehicle pages
3. Automatically solve and inject solutions

You can disable it by setting in `.env`:

```env
ENABLE_CAPTCHA_SOLVING=false
```

## Cost Estimation

- **reCAPTCHA v2**: ~$2.99 per 1000 solves
- **reCAPTCHA v3**: ~$2.99 per 1000 solves
- **hCaptcha**: ~$2.99 per 1000 solves

Average solving time: 10-30 seconds per CAPTCHA

## Troubleshooting

### "API key not configured"
- Make sure `CAPTCHA_API_KEY` is set in `.env` or `config.py`
- Check for typos in the API key

### "Failed to submit CAPTCHA"
- Check your account balance
- Verify API key is correct
- Check internet connection

### "Timeout waiting for solution"
- 2Captcha may be busy, try again
- Check your account status
- Some CAPTCHAs take longer (up to 2 minutes)

### "CAPTCHA detected but could not be solved"
- Check if the CAPTCHA type is supported (reCAPTCHA v2/v3, hCaptcha)
- Verify site key extraction is working
- Check browser console for errors

## Supported CAPTCHA Types

- ✅ reCAPTCHA v2
- ✅ reCAPTCHA v3
- ✅ hCaptcha
- ❌ Other types (not yet supported)

## Configuration Options

In `config.py` or `.env`:

```python
CAPTCHA_API_KEY = "your_key"          # Required
ENABLE_CAPTCHA_SOLVING = True         # Enable/disable
CAPTCHA_SERVICE = "2captcha"          # Service name (for future expansion)
```

## Notes

- CAPTCHA solving adds 10-30 seconds delay per CAPTCHA
- Costs money per solve (~$0.003 per CAPTCHA)
- Solutions are valid for a limited time
- Some sites may detect automated solving (rare)

## Alternative Services

The code is structured to support other services. Currently only 2Captcha is implemented, but you can add:
- Anti-Captcha
- CapSolver
- DeathByCaptcha
- etc.

## Legal Notice

Make sure you comply with:
- Website terms of service
- Local laws regarding automation
- CAPTCHA service terms of use

