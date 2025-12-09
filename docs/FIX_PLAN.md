# Fix Plan: Vehicle Count and CAPTCHA Error Issues

## Problems Identified

1. **Incorrect Vehicle Count**: The application identifies 22 vehicles when there are only 9 actual vehicles
2. **CAPTCHA Error on Navigation**: When navigating to the first vehicle, the site displays a CAPTCHA error message even though no CAPTCHA widget is visible

---

## Multi-Step Plan to Fix Issues

### Problem 1: Fix Vehicle Count Detection

#### Step 1.1: Analyze Current Selector Issues ✅ COMPLETE
- **File**: `src/fine_scrapper.py` (lines 211-300)
- **Issue**: The XPath selector `xpath=//app-infracao-veiculo-lista/form/div[3]/div[2]/div/div[1]` is too broad and matches nested divs or other structural elements, not just vehicle items
- **Action**: Inspect the actual DOM structure of the vehicle list page to identify unique attributes or patterns that distinguish vehicle items from other divs
- **Implementation**: Created diagnostic script `tools/analyze_vehicle_selectors.py` that:
  - Navigates to the vehicle list page
  - Tests the current XPath selector and counts matched elements
  - Analyzes each matched element for:
    - Tag name, class, ID, text content
    - Parent and sibling structure
    - Presence of vehicle-specific keywords (license plate, vehicle info)
    - Click handlers and interactive styles
    - Computed CSS properties
  - Tests alternative selectors
  - Generates a detailed JSON report (`vehicle_selector_analysis.json`)
  - Provides recommendations based on findings
- **Next Steps**: 
  1. Run the diagnostic script: `python tools/analyze_vehicle_selectors.py`
  2. Review the console output and JSON file
  3. Identify patterns that distinguish the 9 actual vehicles from the 22 matched elements
  4. Use findings to implement better selectors in Step 1.2

#### Step 1.2: Implement More Specific Selector Strategy ✅ COMPLETE
- **File**: `src/fine_scrapper.py` (function `get_vehicle_items()`)
- **Changes**:
  1. ✅ Use semantic selectors based on the audit recommendations (Section 7.4)
  2. ✅ Look for data attributes, specific classes, or text patterns that identify vehicle items
  3. ✅ Consider using Angular component selectors if vehicles are rendered as custom components
  4. ✅ Add validation to ensure selected elements contain vehicle-specific content (e.g., license plate, vehicle model)
- **Reference**: `docs/WEBSITE_TECHNICAL_AUDIT.md` Section 7.4 (Dynamic Selectors)
- **Implementation**: 
  - Changed from fragile XPath `div[3]/div[2]/div/div[1]` to class-based selector `div.card-list-item`
  - Added validation to filter out non-vehicle elements (pagination, etc.)
  - Validates clickability and content presence
  - Includes fallback selectors for robustness

#### Step 1.3: Add Element Validation ✅ COMPLETE
- **File**: `src/fine_scrapper.py` (function `get_vehicle_items()`)
- **Changes**:
  1. ✅ After finding potential vehicle items, validate each element contains expected vehicle data
  2. ✅ Filter out elements that don't match vehicle item patterns
  3. ✅ Add logging to show which elements were filtered and why
  4. ✅ Ensure the final count matches the expected 9 vehicles
- **Implementation**:
  - Validates clickability (cursor: pointer, onclick handlers)
  - Validates content presence (text length > 10 chars)
  - Filters out pagination elements (checks for "Exibir", "Página", etc.)
  - Logs validation results for debugging

#### Step 1.4: Improve Wait Strategy for Angular ✅ COMPLETE
- **File**: `src/fine_scrapper.py` (function `get_vehicle_items()`)
- **Changes**:
  1. ✅ According to the audit (Section 8.1), wait for Angular to stabilize before querying
  2. ✅ Wait for `app-infracao-veiculo-lista` component to be visible
  3. ✅ Wait for network idle or specific API calls to complete (Section 4.1 mentions `/portalservicos-ws/` endpoints)
  4. ✅ Add additional `asyncio.sleep(1.5)` after component appears to allow Angular change detection to complete
- **Reference**: `docs/WEBSITE_TECHNICAL_AUDIT.md` Section 8.1 (Wait Strategies) and Section 7.1 (Timing Issues)
- **Implementation**:
  - Added `wait_for_load_state("networkidle")` with timeout fallback
  - Added 1.5 second delay for Angular change detection
  - Maintains human-like reading simulation

---

### Problem 2: Fix CAPTCHA Error Detection and Handling

#### Step 2.1: Improve hCaptcha Detection
- **File**: `src/captcha_solver.py` (function `detect_and_solve_captcha()`, lines 319-417)
- **Issue**: Current detection only looks for iframes with `src*='hcaptcha'`, but hCaptcha might not be visible or might be loaded differently
- **Changes**:
  1. Check for hCaptcha script presence: `script[src*='hcaptcha.com']`
  2. Check for hCaptcha widget container: `div[id*='hcaptcha']` or `div[class*='hcaptcha']`
  3. Check for hCaptcha site key in page source (known key: `86605651-413f-4902-9ff1-c5bb8d55b98c` from audit Section 2.2)
  4. Check for hCaptcha API calls in network requests
  5. Wait for hCaptcha to fully load before attempting detection
- **Reference**: `docs/WEBSITE_TECHNICAL_AUDIT.md` Section 2.2 (CAPTCHA Implementation)

#### Step 2.2: Detect CAPTCHA Error Messages
- **File**: `src/captcha_solver.py` and `src/rate_limit_handler.py`
- **Issue**: The site shows a CAPTCHA error message even when no CAPTCHA widget is visible - this is likely an API response error
- **Changes**:
  1. Monitor network responses for CAPTCHA-related errors (check response bodies for "captcha" keywords)
  2. Check page content for error messages like "Não foi possível validar o CAPTCHA" (already partially implemented in `rate_limit_handler.py` line 112)
  3. Distinguish between visible CAPTCHA widget and CAPTCHA error messages
  4. Handle API-level CAPTCHA errors differently from visible CAPTCHA widgets

#### Step 2.3: Improve CAPTCHA Error Handling in Vehicle Navigation
- **File**: `src/fine_scrapper.py` (function `process_vehicle()`, lines 303-393)
- **Changes**:
  1. Before checking for visible CAPTCHA, check for CAPTCHA error messages in page content
  2. If CAPTCHA error is detected but no widget is visible:
     - Wait longer before retrying (as per audit Section 7.3)
     - Check if hCaptcha needs to be triggered/loaded
     - Consider that the error might be from a previous failed request
  3. Add better error logging to distinguish between:
     - Visible CAPTCHA widget requiring solving
     - CAPTCHA error message from API
     - Rate limiting triggering CAPTCHA requirement
- **Reference**: `docs/WEBSITE_TECHNICAL_AUDIT.md` Section 7.3 (CAPTCHA Triggers)

#### Step 2.4: Enhance Wait Strategy After Vehicle Click
- **File**: `src/fine_scrapper.py` (function `process_vehicle()`)
- **Changes**:
  1. After clicking a vehicle, wait for Angular router to complete navigation (audit Section 6.2)
  2. Wait for the vehicle details component to appear
  3. Wait for network requests to complete (especially API calls to `/portalservicos-ws/`)
  4. Check for error messages before assuming CAPTCHA is needed
  5. Add longer wait times if CAPTCHA error is detected (2-5 seconds as per audit recommendations)
- **Reference**: `docs/WEBSITE_TECHNICAL_AUDIT.md` Section 6.2 (Navigation Strategy) and Section 8.1

#### Step 2.5: Fix hCaptcha Solution Injection
- **File**: `src/captcha_solver.py` (function `inject_solution()`, lines 247-316)
- **Issue**: Current hCaptcha injection might not work correctly for the SENATRAN portal's implementation
- **Changes**:
  1. Verify hCaptcha widget is present before injecting solution
  2. Use the correct hCaptcha callback mechanism for this site
  3. Check if hCaptcha needs to be explicitly rendered/triggered
  4. Monitor network requests to verify solution was accepted
  5. Add retry logic if injection fails

---

## Future Potential Problems

Based on the current code implementation and the technical audit, the following potential issues may arise:

### 1. **Selector Fragility**
The current approach relies heavily on XPath selectors with hardcoded indices (`div[3]/div[2]/div[1]`). According to the audit (Section 7.4), Angular generates dynamic IDs and the structure may change. If the website updates its Angular version or component structure, these selectors will break. **Recommendation**: Implement fallback selectors and use data attributes or semantic classes when available.

### 2. **Angular Change Detection Timing**
The code uses fixed `asyncio.sleep()` delays (1.0-1.5 seconds) to wait for Angular to stabilize. However, the audit (Section 7.2) indicates that Angular's zone.js change detection timing can vary based on page complexity and network conditions. On slower connections or with more complex pages, these fixed delays may be insufficient, leading to race conditions where elements are queried before they're fully rendered. **Recommendation**: Implement dynamic waiting based on element visibility and Angular-specific indicators (e.g., checking for `ng-version` attribute or waiting for specific Angular events).

### 3. **CAPTCHA Triggering Patterns**
The audit (Section 2.2 and 7.3) indicates that hCaptcha can be triggered by rapid requests, suspicious browser fingerprints, unusual navigation patterns, and multiple failed login attempts. The current implementation may trigger CAPTCHA more frequently as it processes more vehicles, especially if the rate limiting delays (currently 3 seconds minimum between API calls) are insufficient. **Recommendation**: Implement adaptive delays that increase after each vehicle processed, and monitor CAPTCHA appearance frequency to adjust behavior dynamically.

### 4. **API Rate Limiting**
The audit (Section 4.2) notes that rate limiting on API endpoints is unknown. The current rate limit handler (`rate_limit_handler.py`) monitors for 429 errors, but the site might use different rate limiting strategies (e.g., IP-based blocking, request pattern analysis). If the site implements stricter rate limiting, the automation may be blocked entirely. **Recommendation**: Implement more conservative rate limiting (1 request per second as per audit Section 9.3), and add monitoring for subtle rate limit indicators (slower responses, different error codes).

### 5. **Session Management**
The audit (Section 2.3) indicates that session management is likely via JWT tokens in localStorage/sessionStorage or server-side sessions with cookies set after authentication. The current implementation uses persistent browser context, but if sessions expire or tokens need refresh, the automation will fail silently. **Recommendation**: Implement session validation checks, monitor for authentication redirects, and handle token refresh if implemented.

### 6. **Pagination Edge Cases**
The pagination detection (`check_for_next_page()` and `navigate_to_next_page()`) uses multiple fallback selectors, but the audit doesn't specify the exact pagination implementation. If pagination uses Angular router navigation or dynamic loading, the current approach might miss pages or get stuck in loops. **Recommendation**: Add validation to ensure pagination actually advances (check URL hash changes or page number indicators), and implement maximum page limits to prevent infinite loops.

### 7. **Network Request Interception Limitations**
The `intercept_and_delay_api_calls()` function in `rate_limit_handler.py` intercepts fetch and XMLHttpRequest, but modern Angular applications might use other mechanisms (e.g., Angular HttpClient, which may not be intercepted). Additionally, the interception adds JavaScript to the page, which might be detected as automation. **Recommendation**: Monitor actual network requests via Playwright's request/response handlers instead of JavaScript interception, and verify that delays are actually being applied.

### 8. **Error Recovery Robustness**
When errors occur (e.g., CAPTCHA errors, timeouts), the code attempts to recover by going back to the vehicle list. However, if the error occurs during navigation or if the browser state is corrupted, the recovery might fail, leaving the automation in an unknown state. **Recommendation**: Implement state validation after recovery attempts, add more robust error handling with multiple recovery strategies, and consider implementing a "reset" function that navigates directly to the vehicle list URL if recovery fails.

---

**Document Version**: 1.0  
**Created**: Based on technical audit and current codebase analysis  
**Next Steps**: Review and approve plan before implementation

