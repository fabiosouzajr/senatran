# Human-like Behavior Implementation Guide

## Overview

This document explains the human-like behavior features implemented to reduce CAPTCHA triggers and make browser automation appear more natural.

## Features Implemented

### 1. Random Delays
- **Between Actions**: Random delays (500-2000ms) between actions to simulate human thinking time
- **Before Clicks**: Random delays (200-800ms) before clicking elements
- **After Actions**: Small random delays (100-400ms) after actions

### 2. Human-like Mouse Movements
- **Smooth Movement**: Mouse moves with variable speed (5-15 steps) instead of instant jumps
- **Random Positioning**: Clicks don't always hit the exact center of elements (30-70% offset)
- **Random Mouse Movements**: Occasional random mouse movements to simulate human activity

### 3. Reading Simulation
- **Page Reading Time**: Random delays (1-3 seconds) to simulate reading content
- **Scroll While Reading**: 40% chance to scroll while "reading" a page
- **Variable Reading Times**: Different reading times for different page types

### 4. Random Scrolling
- **Variable Scroll Amounts**: Scrolls 200-600 pixels (not always full page)
- **Scroll Direction**: Mostly down (90%), occasionally up (10%)
- **Multiple Scrolls**: 1-3 scroll actions per page to simulate exploration

### 5. Human-like Navigation
- **Delays Before Navigation**: Random delays (300-800ms) before navigating
- **Reading After Navigation**: Simulates reading the new page (1-2.5 seconds)
- **Exploration**: 70% chance to scroll after navigation

### 6. Browser Configuration
- **Locale**: Set to Portuguese (Brazil) - `pt-BR`
- **Timezone**: Set to `America/Sao_Paulo`
- **Language**: Browser language set to match the target site
- **Anti-detection Flags**: Disabled automation indicators

## Files Modified

### `human_behavior.py` (New)
Contains all human-like behavior functions:
- `random_delay()` - Random delays between actions
- `human_like_click()` - Clicks with mouse movement and delays
- `random_scroll()` - Random scrolling behavior
- `simulate_reading()` - Simulates reading time
- `human_like_navigation()` - Navigation with human-like delays
- `human_like_back_navigation()` - Back navigation with delays
- `random_mouse_movement()` - Random mouse movements

### `fine_scrapper.py` (Updated)
Integrated human-like behavior into:
- Navigation to FINES_URL
- Clicking vehicle items
- Going back to vehicle list
- Navigating to next page
- Reading pages after navigation

### `config.py` (Updated)
Added configuration options:
- `ENABLE_HUMAN_BEHAVIOR` - Enable/disable human behavior
- `MIN_DELAY_MS` / `MAX_DELAY_MS` - Delay ranges
- `MIN_READING_TIME` / `MAX_READING_TIME` - Reading time ranges

### `main.py` (Updated)
Added browser configuration:
- Locale set to `pt-BR`
- Timezone set to `America/Sao_Paulo`
- Additional anti-detection browser arguments

## Configuration

You can adjust human behavior settings in `config.py` or via environment variables:

```env
ENABLE_HUMAN_BEHAVIOR=true
MIN_DELAY_MS=500
MAX_DELAY_MS=2000
MIN_READING_TIME=1.0
MAX_READING_TIME=3.0
```

## Best Practices

1. **Don't Disable Human Behavior**: Keep `ENABLE_HUMAN_BEHAVIOR=true` to avoid CAPTCHAs
2. **Adjust Delays if Needed**: If still getting CAPTCHAs, increase delay ranges
3. **Monitor Performance**: Human behavior adds time - balance between speed and detection
4. **Test Incrementally**: Test with one vehicle first to verify behavior

## Additional Anti-Detection Tips

1. **Use Persistent Context**: Already implemented - cookies and cache persist
2. **Vary Timing**: Random delays prevent pattern detection
3. **Simulate Reading**: Don't navigate too quickly between pages
4. **Scroll Naturally**: Random scrolling shows human-like exploration
5. **Mouse Movements**: Smooth, variable-speed mouse movements

## Troubleshooting

### Still Getting CAPTCHAs?

1. **Increase Delays**: Increase `MAX_DELAY_MS` and `MAX_READING_TIME`
2. **Add More Randomness**: Increase scroll frequency and mouse movements
3. **Check Browser Flags**: Ensure automation flags are disabled
4. **Verify Locale**: Ensure locale and timezone match the target region
5. **Slow Down**: Process fewer vehicles per session, take breaks

### Performance Too Slow?

1. **Reduce Delays**: Decrease `MIN_DELAY_MS` and `MIN_READING_TIME`
2. **Reduce Reading Time**: Lower `MAX_READING_TIME`
3. **Disable Some Features**: Comment out random scrolling if not needed

## Testing

To test human behavior:
1. Run the scraper and observe the browser
2. Check that delays are random and natural
3. Verify mouse movements are smooth
4. Confirm scrolling happens occasionally
5. Monitor for CAPTCHA triggers

## Future Enhancements

Potential improvements:
- Typing simulation with variable speeds
- More complex mouse movement patterns
- Keyboard shortcuts simulation
- Tab switching behavior
- Form filling with human-like delays

