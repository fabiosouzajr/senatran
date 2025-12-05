# Rate Limiting and CAPTCHA Error Solution

## Problem

The SENATRAN portal was returning **429 Too Many Requests** errors with the message:
> "Não foi possível validar o CAPTCHA para realizar a operação. Por favor tente novamente mais tarde."

Even though no visible CAPTCHA was displayed, the backend was rejecting requests due to:
1. **Rate limiting** - Too many requests in a short time
2. **Missing/invalid reCAPTCHA tokens** - The site requires reCAPTCHA validation for API calls
3. **Automation detection** - The site detected automated behavior patterns

## Solution Implemented

### 1. Rate Limit Detection and Handling (`rate_limit_handler.py`)

**Features:**
- **Network monitoring** - Detects 429 status codes in HTTP responses
- **Error detection** - Checks page content for CAPTCHA/rate limit error messages
- **Exponential backoff** - Automatically retries with increasing delays
- **CAPTCHA detection** - Identifies when CAPTCHA blocking occurs

**Key Functions:**
- `setup_rate_limit_monitoring()` - Monitors network requests for 429 errors
- `check_for_rate_limit_error()` - Scans page for error messages
- `handle_rate_limit()` - Implements exponential backoff retry logic
- `check_and_handle_captcha()` - Detects and handles CAPTCHA requirements
- `add_extra_delay_for_rate_limiting()` - Adds delays between requests

### 2. Integration into Scraper (`fine_scrapper.py`)

**Changes:**
- Rate limit monitoring enabled at start of scraping
- Extra delays added before processing each vehicle (3-8 seconds)
- Rate limit checks after navigation and clicks
- Automatic retry with exponential backoff on rate limit errors
- CAPTCHA detection and handling
- Rest periods when rate limiting is detected

### 3. Configuration (`config.py`)

**New Configuration Options:**
```python
RATE_LIMIT_ENABLED = True  # Enable/disable rate limiting protection
RATE_LIMIT_DELAY_MIN = 3.0  # Minimum delay between requests (seconds)
RATE_LIMIT_DELAY_MAX = 8.0  # Maximum delay between requests (seconds)
RATE_LIMIT_RETRY_ATTEMPTS = 3  # Max retry attempts on rate limit
RATE_LIMIT_REST_PERIOD = 60  # Rest period after rate limit (seconds)
```

### 4. Increased Default Delays (`human_behavior.py`)

**Updated Timing:**
- Minimum delay: 500ms → **1000ms**
- Maximum delay: 2000ms → **3000ms**
- Reading delays: 1-3s → **2-5s**
- Click delays: 200-800ms → **500-1500ms**

## How It Works

### Request Flow with Rate Limiting:

1. **Before each vehicle:**
   - Wait 3-8 seconds (configurable)
   - Check for existing rate limit errors

2. **During vehicle processing:**
   - Monitor network requests for 429 errors
   - Check page content for error messages
   - If rate limit detected:
     - Wait with exponential backoff (5s, 10s, 20s...)
     - Retry up to 3 times
     - If CAPTCHA blocking, wait 2 minutes

3. **After navigation:**
   - Check for rate limit errors
   - Handle CAPTCHA requirements
   - Add extra delays before next action

### Exponential Backoff:

```
Attempt 1: Wait 5 seconds
Attempt 2: Wait 10 seconds (5 * 2^1)
Attempt 3: Wait 20 seconds (5 * 2^2)
Max wait: 300 seconds (5 minutes)
```

## Configuration

### Via Environment Variables (`.env` file):

```env
# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DELAY_MIN=3.0
RATE_LIMIT_DELAY_MAX=8.0
RATE_LIMIT_RETRY_ATTEMPTS=3
RATE_LIMIT_REST_PERIOD=60
```

### Adjusting for Your Needs:

**If still getting rate limited:**
- Increase `RATE_LIMIT_DELAY_MIN` and `RATE_LIMIT_DELAY_MAX` (e.g., 5-10 seconds)
- Increase `RATE_LIMIT_REST_PERIOD` (e.g., 120 seconds)
- Increase `RATE_LIMIT_RETRY_ATTEMPTS` (e.g., 5)

**If too slow:**
- Decrease delays (but be careful not to trigger rate limits)
- Monitor logs for rate limit warnings

## Logging

The system logs:
- **INFO**: Normal operations, delays, retries
- **WARNING**: Rate limit detected, retrying
- **ERROR**: Max retries exceeded, CAPTCHA blocking

Example log output:
```
INFO - Rate limit monitoring enabled
INFO - Processing vehicle 1/5 on page 1...
INFO - Adding extra delay: 5.23 seconds to avoid rate limiting
WARNING - 429 Too Many Requests detected for: https://...
WARNING - Rate limit detected (attempt 1/3): Não foi possível validar o CAPTCHA
INFO - Waiting 5.0 seconds before retry...
```

## Limitations

1. **CAPTCHA Solving**: Currently only detects CAPTCHA requirements, doesn't solve them automatically
   - Solution: Integrate a CAPTCHA solving service (2Captcha, Anti-Captcha, etc.)

2. **Rate Limit Thresholds**: The exact rate limits are unknown
   - Solution: Monitor and adjust delays based on experience

3. **IP-based Blocking**: If your IP is blocked, delays won't help
   - Solution: Use proxy rotation (see `ANTI_CAPTCHA_OPTIONS.md`)

## Next Steps

If rate limiting persists:

1. **Increase delays further** - Try 5-15 seconds between requests
2. **Add rest periods** - Pause for 2-5 minutes after every 10 vehicles
3. **Implement CAPTCHA solving** - Use a service to solve reCAPTCHA tokens
4. **Use proxy rotation** - Distribute requests across multiple IPs
5. **Reduce request frequency** - Process fewer vehicles per session

## Testing

To test rate limiting handling:

1. Run the scraper normally
2. Monitor logs for rate limit warnings
3. Check if retries succeed
4. Adjust delays if needed

The system will automatically handle rate limits and retry with backoff.
