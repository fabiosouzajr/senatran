# Debugging Guide for Fine Scraper

## How to Double-Check Your Logic

### 1. Inspect the Page Structure

Before running the scraper, manually inspect the page to verify selectors:

1. **Open the browser** and navigate to `FINES_URL`
2. **Open Developer Tools** (F12)
3. **Inspect the vehicle list element**:
   - Find `<app-infracao-veiculo-lista>` in the DOM
   - Check what child elements contain the vehicle links/buttons
   - Note the exact structure and classes

4. **Inspect a vehicle link**:
   - Click on a vehicle to see the fine details page
   - Find `<div class="col-md-12 autuacao border">` elements
   - Check if the class names are exactly as expected (case-sensitive)

### 2. Test Selectors Manually

You can test selectors in the browser console:

```javascript
// Test vehicle list selector
document.querySelector('app-infracao-veiculo-lista')

// Test vehicle items
document.querySelectorAll('app-infracao-veiculo-lista a')

// Test fine elements
document.querySelectorAll('div.col-md-12.autuacao.border')
```

### 3. Add Debug Logging

The scraper already includes comprehensive logging. To see more details:

1. **Change log level** in `fine_scrapper.py`:
   ```python
   logging.basicConfig(level=logging.DEBUG)  # More verbose
   ```

2. **Add breakpoints** in your IDE or use `await page.pause()` in the code

### 4. Verify Step-by-Step

Run the scraper and verify each step:

1. **Navigation**: Does it navigate to FINES_URL correctly?
2. **Vehicle List**: Does it find `app-infracao-veiculo-lista`?
3. **Vehicle Items**: How many vehicles does it find? Does this match what you see?
4. **Vehicle Click**: Does clicking a vehicle navigate correctly?
5. **Fine Elements**: Does it find the fine divs? How many?
6. **Pagination**: Does it detect and navigate to the next page?

### 5. Common Issues and Solutions

#### Issue: "No vehicle items found"
**Solution**: 
- Check the actual HTML structure
- Update selectors in `get_vehicle_items()` function
- The vehicle items might be loaded dynamically - add wait for specific elements

#### Issue: "No fine elements found"
**Solution**:
- Verify the exact class name (check for typos, case sensitivity)
- The page might need more time to load - increase timeout
- Some vehicles might genuinely have no fines

#### Issue: Pagination not working
**Solution**:
- Inspect the pagination buttons in DevTools
- Update selectors in `check_for_next_page()` and `navigate_to_next_page()`
- Check if pagination uses different text (Portuguese vs English)

### 6. Use Playwright's Built-in Tools

```python
# Take a screenshot for debugging
await page.screenshot(path="debug_screenshot.png")

# Print page HTML
html = await page.content()
print(html)

# Check if element exists
exists = await page.locator("selector").count() > 0
```

### 7. Test with a Single Vehicle First

Modify the code to process only the first vehicle:

```python
# In process_all_vehicle_pages(), limit to first vehicle
vehicle_items = vehicle_items[:1]  # Process only first vehicle
```

### 8. Verify Element Visibility

Some elements might exist but not be visible:

```python
# Check visibility
is_visible = await page.locator("selector").is_visible()
```

## Recommended Testing Flow

1. **Manual Inspection**: Open the site, inspect elements
2. **Single Page Test**: Run scraper for one page only
3. **Single Vehicle Test**: Process only first vehicle
4. **Full Test**: Run complete scraper with logging
5. **Error Handling**: Test with edge cases (no vehicles, no fines, etc.)

## Logging Output Interpretation

- `INFO`: Normal operation flow
- `WARNING`: Non-critical issues (e.g., vehicle with no fines)
- `ERROR`: Critical errors that stop execution
- `DEBUG`: Detailed information for troubleshooting

## Next Steps After Verification

Once iteration logic is verified:
1. Implement data extraction from fine elements
2. Add data storage (file, database)
3. Add retry logic for failed requests
4. Optimize performance if needed

