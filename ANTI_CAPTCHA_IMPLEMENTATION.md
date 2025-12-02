# Anti-CAPTCHA and Anti-Bot Detection Implementation

## Overview

This document describes the implementation of comprehensive anti-detection and anti-CAPTCHA measures for the Senatran automation system. The implementation focuses on avoiding CAPTCHA triggers through stealth browser automation, fingerprint randomization, and human-like behavior simulation.

## Implementation Summary

The system now includes:

1. **Stealth Browser Features**: Masks automation indicators using Chrome DevTools Protocol (CDP)
2. **Fingerprint Randomization**: Generates realistic browser fingerprints per session
3. **Human Behavior Simulation**: Variable delays, mouse movements, and natural interactions
4. **Enhanced CAPTCHA Detection**: Centralized CAPTCHA detection and handling
5. **Improved Rate Limiting**: Jitter-based delays for more natural request patterns

## Architecture

### New Modules

#### `src/fingerprint_manager.py`
- Generates random but realistic browser fingerprints
- Rotates user agents from real browser pool
- Randomizes viewport, timezone, locale, and other properties
- Applies fingerprint via CDP to browser context

#### `src/human_behavior.py`
- Variable delay functions using Gaussian distribution
- Human-like mouse movement simulation
- Natural scrolling patterns
- Typing speed variation

#### `src/captcha_handler.py`
- Centralized CAPTCHA detection
- Support for multiple CAPTCHA types (reCAPTCHA, hCaptcha, image, text, generic)
- Automatic screenshot capture for debugging
- Enhanced waiting logic for manual CAPTCHA solving

### Updated Modules

#### `src/config.py`
Added new configuration sections:
- `STEALTH_CONFIG`: Stealth plugin settings
- `FINGERPRINT_CONFIG`: Fingerprint randomization options
- `HUMAN_BEHAVIOR_CONFIG`: Behavior simulation parameters
- `CAPTCHA_CONFIG`: Enhanced CAPTCHA handling settings
- `RATE_LIMITING_ENHANCED`: Jitter-based rate limiting

#### `src/main.py`
- Integrated stealth features into browser initialization
- Applied fingerprint randomization on context creation
- Enhanced rate limiting with jitter

#### `src/auth_handler.py`
- Integrated new CAPTCHA handler
- Replaced fixed delays with human behavior simulation
- Enhanced CAPTCHA detection and handling

## Configuration

### Stealth Configuration

```python
STEALTH_CONFIG = {
    'enabled': True,  # Enable stealth features
    'remove_webdriver': True,  # Remove webdriver property
    'override_plugins': True,  # Override navigator.plugins
    'override_languages': True,  # Override navigator.languages
    'override_permissions': True,  # Override permissions API
    'add_chrome_runtime': True,  # Add chrome.runtime object
    'override_webgl': True,  # Override WebGL fingerprinting
}
```

### Fingerprint Configuration

```python
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
```

### Human Behavior Configuration

```python
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
```

### CAPTCHA Configuration

```python
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
```

### Enhanced Rate Limiting

```python
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
```

## Usage

### Basic Usage

The stealth and anti-detection features are enabled by default. Simply run the automation as usual:

```bash
python run.py
```

### Disabling Features

To disable specific features, edit `src/config.py`:

```python
# Disable stealth features
STEALTH_CONFIG['enabled'] = False

# Disable fingerprint randomization
FINGERPRINT_CONFIG['enabled'] = False

# Disable human behavior simulation
HUMAN_BEHAVIOR_CONFIG['enabled'] = False
```

### Adjusting Behavior

To adjust human behavior simulation:

```python
# Increase delay variance (more randomness)
HUMAN_BEHAVIOR_CONFIG['delay_variance'] = 0.5  # ±50% variation

# Disable mouse movement simulation (faster but less human-like)
HUMAN_BEHAVIOR_CONFIG['simulate_mouse_movement'] = False
```

## How It Works

### Stealth Features

The stealth implementation uses Chrome DevTools Protocol (CDP) to inject JavaScript that:

1. Removes the `navigator.webdriver` property
2. Overrides `navigator.plugins` to return realistic values
3. Overrides `navigator.languages` to match fingerprint
4. Adds `window.chrome.runtime` object
5. Modifies WebGL fingerprinting to return consistent values

### Fingerprint Randomization

On each browser context creation:

1. Generates a random but realistic fingerprint
2. Randomizes user agent from real browser pool
3. Randomizes viewport size from common resolutions
4. Randomizes timezone (Brazil-focused)
5. Randomizes locale and language settings
6. Applies fingerprint to browser context

### Human Behavior Simulation

Replaces fixed delays with:

1. **Variable Delays**: Gaussian distribution around base delay
2. **Mouse Movement**: Bezier curve paths before clicks
3. **Natural Scrolling**: Multiple small scroll steps
4. **Typing Speed**: Variable character-by-character typing

### CAPTCHA Detection

The CAPTCHA handler:

1. Detects multiple CAPTCHA types automatically
2. Takes screenshots for debugging (if enabled)
3. Pauses automation and waits for manual solving
4. Monitors page for CAPTCHA resolution
5. Automatically continues when solved

## Dependencies

New dependencies added to `requirements.txt`:

- `fake-useragent>=1.4.0`: For user agent rotation
- `numpy>=1.24.0`: For Gaussian distribution in delays

Install with:

```bash
pip install -r requirements.txt
```

## Troubleshooting

### CAPTCHAs Still Appearing Frequently

1. **Increase delays**: Adjust `HUMAN_BEHAVIOR_CONFIG['delay_variance']` to add more randomness
2. **Enable all features**: Ensure `STEALTH_CONFIG['enabled']` and `FINGERPRINT_CONFIG['enabled']` are `True`
3. **Check rate limiting**: Increase `RATE_LIMITING_ENHANCED['min_delay']` and `max_delay`
4. **Review screenshots**: Check `captcha_screenshots/` directory for CAPTCHA types

### Browser Detection Issues

1. **Verify stealth script**: Check browser console for `navigator.webdriver` (should be `undefined`)
2. **Check fingerprint**: Logs should show fingerprint generation on browser initialization
3. **Test in non-headless mode**: Some detection methods work better in visible mode

### Performance Impact

Human behavior simulation adds delays. To balance stealth and speed:

1. Disable mouse movement: `HUMAN_BEHAVIOR_CONFIG['simulate_mouse_movement'] = False`
2. Reduce delay variance: `HUMAN_BEHAVIOR_CONFIG['delay_variance'] = 0.1`
3. Use fixed delays: `HUMAN_BEHAVIOR_CONFIG['use_variable_delays'] = False`

## Limitations

1. **Image-Based CAPTCHA Solving**: Truly free automated solving for image-based CAPTCHAs is very limited. The focus is on avoiding detection.

2. **Stealth Effectiveness**: Stealth plugins help but aren't 100% effective against advanced detection. Combined with human behavior, they significantly reduce detection.

3. **Performance Impact**: Human behavior simulation adds delays. Balance between stealth and speed.

4. **Maintenance**: Detection methods evolve. Regular updates to stealth techniques may be needed.

## Future Enhancements

Potential future improvements:

1. **CAPTCHA Solving Services**: Integration with paid services (2Captcha, Anti-Captcha) for automated solving
2. **Machine Learning**: Train models to solve specific CAPTCHA types
3. **Proxy Rotation**: Add proxy support for IP rotation
4. **Session Management**: Better session persistence and rotation
5. **Advanced Fingerprinting**: More sophisticated fingerprint randomization

## Testing

To test the implementation:

1. **Monitor CAPTCHA Rate**: Compare CAPTCHA appearance rate before/after implementation
2. **Check Logs**: Verify fingerprint generation and stealth application in logs
3. **Browser Console**: Check `navigator.webdriver` in browser console (should be `undefined`)
4. **Screenshots**: Review CAPTCHA screenshots if detection occurs

## Success Metrics

Track these metrics to measure effectiveness:

- **CAPTCHA Appearance Rate**: Should decrease significantly
- **Automation Success Rate**: Should increase
- **Manual Intervention**: Should decrease
- **Session Longevity**: Sessions should last longer before detection

## Support

For issues or questions:

1. Check logs in `senatran_automation.log`
2. Review CAPTCHA screenshots in `captcha_screenshots/` (if enabled)
3. Verify configuration in `src/config.py`
4. Test with stealth features disabled to isolate issues

## License

This implementation is part of the Senatran automation project and follows the same license terms.

