# SENATRAN Portal - Technical Website Audit Report

**Audit Date:** December 9, 2025  
**Target URL:** `https://portalservicos.senatran.serpro.gov.br/#/home`  
**Auditor:** Technical Website Auditor

---

## Executive Summary

This technical audit provides a comprehensive analysis of the SENATRAN (Serviço Nacional de Trânsito) portal's architecture, security policies, implementation details, and technical characteristics. The findings are intended to guide automation development and help avoid common pitfalls when interacting with this government portal.

### Key Findings

- **Framework:** Angular-based Single Page Application (SPA)
- **Architecture:** Hash-based routing (`#/` URLs)
- **Security:** HSTS enabled, but missing CSP and X-Frame-Options
- **CAPTCHA:** hCaptcha integration for bot protection
- **API Pattern:** RESTful API with `/portalservicos-ws/` prefix
- **Cache Strategy:** Aggressive caching for static assets, no-cache for API endpoints

---

## 1. Architecture & Framework Analysis

### 1.1 Framework Stack

**Primary Framework:** Angular
- **Detection:** Custom elements (`app-root`, `app-landing`, `app-campanha-vigente`, etc.)
- **Version:** Unknown (detected via DOM structure)
- **Routing:** Hash-based routing (`#/home`, `#/infracoes/consultar/veiculo`)
- **Change Detection:** Uses Angular's zone.js (requires waiting for Angular to stabilize)

**Additional Libraries:**
- jQuery (detected in JavaScript analysis)
- Angular Material / Custom Design System components (`br-*` elements)
- ngx-spinner (loading indicators)

### 1.2 Application Type

**Single Page Application (SPA)**
- ✅ Confirmed: Hash-based routing detected
- ✅ All navigation happens client-side
- ✅ Content is dynamically loaded via JavaScript
- ⚠️ **Critical:** Page content requires JavaScript execution before it's available

**Implications for Automation:**
1. **Wait Strategy:** Must wait for Angular to initialize and render content
2. **Navigation:** Use hash-based URLs (`#/path`) for direct navigation
3. **Content Loading:** Elements appear dynamically - use `wait_for_selector` instead of immediate queries
4. **State Management:** Angular manages state internally - page reloads may reset state

### 1.3 Custom Elements & Component Structure

**Detected Custom Elements:**
```
- app-root (main application container)
- app-landing (landing page component)
- app-campanha-vigente (campaign component)
- app-infracao-veiculo-lista (vehicle fine list - your target component)
- br-label, br-header, br-input (Brazil Design System components)
- br-alert-messages, br-main-layout, br-fieldset, br-breadcrumbs
- router-outlet (Angular router component)
- ngx-spinner (loading spinner)
```

**Selector Strategy:**
- ✅ Use custom element names: `app-infracao-veiculo-lista`
- ✅ Use Angular component selectors: `app-root > router-outlet`
- ✅ Combine with CSS classes: `app-infracao-veiculo-lista form`
- ⚠️ Avoid relying on IDs - Angular generates dynamic IDs

---

## 2. Security Analysis

### 2.1 Security Headers

| Header | Status | Value | Risk Level |
|--------|--------|-------|------------|
| **Strict-Transport-Security (HSTS)** | ✅ Present | `max-age=15768000` (~6 months) | Low |
| **Content-Security-Policy (CSP)** | ❌ Missing | None | Medium |
| **X-Frame-Options** | ❌ Missing | None | Medium |
| **X-Content-Type-Options** | ❌ Missing | None | Low |
| **X-XSS-Protection** | ❌ Missing | None | Low |
| **Referrer-Policy** | ❌ Missing | None | Low |
| **Permissions-Policy** | ❌ Missing | None | Low |

**Security Recommendations:**
1. ⚠️ **CSP Missing:** Website is vulnerable to XSS attacks. Automation should be careful with user input.
2. ⚠️ **X-Frame-Options Missing:** Site can be embedded in iframes (clickjacking risk). Automation should handle iframe contexts if needed.
3. ✅ **HSTS Present:** HTTPS is enforced, which is good for secure automation.

### 2.2 CAPTCHA Implementation

**CAPTCHA Provider:** hCaptcha
- **Site Key:** `86605651-413f-4902-9ff1-c5bb8d55b98c`
- **API Endpoint:** `https://api.hcaptcha.com/checksiteconfig`
- **Script URL:** `https://js.hcaptcha.com/1/api.js`
- **Language:** Portuguese (pt-BR)

**CAPTCHA Characteristics:**
- Loaded asynchronously via external script
- Rendered explicitly (not automatic)
- Compatible with reCAPTCHA API (for migration purposes)
- Uses Cloudflare for CDN (`__cf_bm` cookies)

**Implications for Automation:**
1. ⚠️ **CAPTCHA Triggers:** Likely triggered by:
   - Rapid requests
   - Suspicious browser fingerprints
   - Unusual navigation patterns
   - Multiple failed login attempts

2. ✅ **CAPTCHA Solving:** Your project already has `captcha_solver.py` - ensure it supports hCaptcha (not just reCAPTCHA)

3. ⚠️ **Timing:** CAPTCHA may appear:
   - On initial page load
   - After form submissions
   - During navigation between pages
   - When accessing protected endpoints

### 2.3 Cookie Security

**Cookie Analysis:**
- **Total Cookies:** 2 (from hCaptcha/Cloudflare)
- **HttpOnly:** 2/2 (100%) ✅
- **Secure:** 2/2 (100%) ✅
- **SameSite:** 
  - `None`: 2 cookies
  - `Strict`: 0
  - `Lax`: 0

**Cookie Details:**
```
Domain: .hcaptcha.com, .w.hcaptcha.com
Name: __cf_bm (Cloudflare Bot Management)
Secure: Yes
HttpOnly: Yes
SameSite: None
```

**Cookie Recommendations:**
1. ⚠️ **SameSite=None:** Cookies are set with `SameSite=None`, which is required for cross-site requests but less secure
2. ✅ **Secure Flag:** All cookies use Secure flag (HTTPS only)
3. ✅ **HttpOnly:** All cookies are HttpOnly (protected from JavaScript access)

**Session Management:**
- No application-level session cookies detected in initial load
- Session likely managed via:
  - JWT tokens in localStorage/sessionStorage
  - Server-side sessions with cookies set after authentication
  - API tokens in request headers

---

## 3. Cache Implementation

### 3.1 Cache Strategy

**Static Assets (CSS, JS, Fonts):**
- **Cache-Control:** `max-age=31536000` (1 year)
- **ETag:** Present (24 resources)
- **Last-Modified:** Present (21 resources)
- **Strategy:** Aggressive long-term caching

**API Endpoints:**
- **Cache-Control:** `no-cache, no-store, max-age=0, must-revalidate`
- **Strategy:** No caching - always fetch fresh data

**Third-Party Resources:**
- **hCaptcha:** `max-age=300` to `max-age=3024000` (5 minutes to 35 days)
- **CDN Assets:** `max-age=604800` to `max-age=31536000` (1 week to 1 year)

### 3.2 Cache Implications

**For Automation:**
1. ✅ **Static Assets:** Cached aggressively - won't reload on subsequent visits
2. ⚠️ **API Calls:** Always fresh - cannot rely on cached responses
3. ✅ **Performance:** Good caching strategy reduces load times
4. ⚠️ **Updates:** Static assets may be stale if website updates - clear cache if issues occur

**Cache Headers Examples:**
```
Static Assets:
  Cache-Control: max-age=31536000, public, max-age=31536000

API Endpoints:
  Cache-Control: no-cache, no-store, max-age=0, must-revalidate
```

---

## 4. API Architecture

### 4.1 API Pattern

**Base Pattern:** `/portalservicos-ws/` prefix

**Detected Endpoints:**
1. `GET /portalservicos-ws/funcionalidade/home`
   - Purpose: Home page functionality data
   - Cache: No-cache
   - Content-Type: `application/json`

2. `GET /portalservicos-ws/campanha/vigentes/ambito/2`
   - Purpose: Active campaigns for scope 2
   - Cache: No-cache
   - Content-Type: `application/json`

3. `GET /assets/cookiebar/dados/arquivoconfiguracao.json`
   - Purpose: Cookie bar configuration
   - Cache: Unknown

4. `GET /assets/cookiebar/dados/arquivocompleto.json`
   - Purpose: Complete cookie bar data
   - Cache: Unknown

### 4.2 API Characteristics

**Request Headers:**
```
Accept: application/json, text/plain, */*
Content-Type: application/json (for POST)
Referer: https://portalservicos.senatran.serpro.gov.br/
User-Agent: [Browser User Agent]
Accept-Language: pt-BR
```

**Response Format:**
- JSON responses
- No-cache headers (always fresh data)
- Likely requires authentication for protected endpoints

**API Recommendations:**
1. ✅ **RESTful Pattern:** Follows REST conventions
2. ⚠️ **Authentication:** May require tokens/credentials for protected endpoints
3. ⚠️ **Rate Limiting:** Unknown - implement delays between requests
4. ✅ **CORS:** Likely configured for same-origin requests only

---

## 5. Resource Loading & Dependencies

### 5.1 External Dependencies

**CDN Domains:**
- `cdngovbr-ds.estaleiro.serpro.gov.br` - Brazil Design System (fonts, styles)
- `cdn.jsdelivr.net` - JavaScript CDN (vlibras plugin)
- `newassets.hcaptcha.com` - hCaptcha assets
- `js.hcaptcha.com` - hCaptcha scripts
- `barra.brasil.gov.br` - Government bar component
- `vlibras.gov.br` - Accessibility plugin

**Resource Types:**
- Documents: 3
- Stylesheets: 4
- Scripts: 12
- Fonts: 8
- XHR/Fetch: 7 (API calls)

### 5.2 JavaScript Loading

**Script Analysis:**
- **Total Scripts:** 12
- **Inline Scripts:** 1
- **External Scripts:** 11
- **Frameworks Detected:** jQuery, Angular

**Key JavaScript Files:**
```
- runtime-es2015.f00ddbbd4a6c51e569f7.js (Angular runtime)
- polyfills-es2015.9ba952a0c6baeb75eab0.js (Polyfills)
- main-es2015.27bb3ae484a4022c35a4.js (Main application bundle)
- scripts.09171577a9f36ccaf9fe.js (Additional scripts)
- styles.09d70d377c460f2fb0ba.css (Styles)
```

**Loading Implications:**
1. ⚠️ **Async Loading:** Scripts load asynchronously - wait for `networkidle` or specific selectors
2. ⚠️ **Bundle Size:** Large JavaScript bundles - initial load may be slow
3. ✅ **ES2015:** Modern JavaScript - ensure browser compatibility

---

## 6. Navigation & Routing

### 6.1 Routing Mechanism

**Type:** Hash-based routing (`#/path`)

**Examples:**
- Home: `https://portalservicos.senatran.serpro.gov.br/#/home`
- Fines: `https://portalservicos.senatran.serpro.gov.br/#/infracoes/consultar/veiculo`

**Router Component:** `<router-outlet>` (Angular Router)

### 6.2 Navigation Strategy

**For Automation:**
1. ✅ **Direct Navigation:** Can navigate directly to hash URLs
2. ✅ **No Page Reload:** Hash changes don't trigger full page reloads
3. ⚠️ **Wait for Router:** Must wait for Angular router to complete navigation
4. ⚠️ **State Preservation:** State may be preserved during navigation

**Recommended Navigation Pattern:**
```python
# Direct navigation to hash URL
await page.goto("https://portalservicos.senatran.serpro.gov.br/#/infracoes/consultar/veiculo")

# Wait for Angular router to complete
await page.wait_for_selector("app-infracao-veiculo-lista", state="visible")

# Wait for Angular to stabilize (zone.js)
await asyncio.sleep(1)  # Give Angular time to render
```

---

## 7. Common Pitfalls & Solutions

### 7.1 Timing Issues

**Problem:** Content not available immediately after navigation

**Solution:**
```python
# ❌ BAD: Immediate query
await page.goto(url)
element = await page.query_selector("app-infracao-veiculo-lista")  # May be None

# ✅ GOOD: Wait for element
await page.goto(url)
await page.wait_for_selector("app-infracao-veiculo-lista", state="visible", timeout=30000)
await asyncio.sleep(1)  # Additional wait for Angular to stabilize
element = await page.query_selector("app-infracao-veiculo-lista")  # Will exist
```

### 7.2 Angular Change Detection

**Problem:** Angular may not have updated the DOM yet

**Solution:**
```python
# Wait for Angular to stabilize
await page.wait_for_load_state("networkidle")
await asyncio.sleep(1.5)  # Give zone.js time to run change detection

# Or wait for specific content
await page.wait_for_selector("app-infracao-veiculo-lista form", state="visible")
```

### 7.3 CAPTCHA Triggers

**Problem:** CAPTCHA appears unexpectedly

**Solution:**
1. Implement human-like delays between actions
2. Use persistent browser context (cookies, cache)
3. Rotate user agents if needed
4. Monitor for CAPTCHA and solve automatically
5. Avoid rapid-fire requests

### 7.4 Dynamic Selectors

**Problem:** Selectors break when structure changes

**Solution:**
```python
# ❌ BAD: Fragile XPath with hardcoded indices
xpath = "//form/div[3]/div[2]/div[1]/div[1]"

# ✅ GOOD: Use semantic selectors
selector = "app-infracao-veiculo-lista form > div > div > div > div:first-child"

# ✅ BETTER: Use data attributes or classes
selector = "app-infracao-veiculo-lista [data-vehicle-item]"
```

### 7.5 API Rate Limiting

**Problem:** Too many API requests trigger rate limiting

**Solution:**
1. Implement delays between API calls (500-2000ms)
2. Use exponential backoff on errors
3. Monitor response headers for rate limit indicators
4. Cache responses when possible (but respect no-cache headers)

### 7.6 Session Management

**Problem:** Session expires or is lost

**Solution:**
1. Use persistent browser context (your project already does this)
2. Monitor for authentication redirects
3. Handle session timeout gracefully
4. Re-authenticate if needed

---

## 8. Best Practices for Automation

### 8.1 Wait Strategies

**Recommended Approach:**
```python
# 1. Navigate with appropriate wait strategy
await page.goto(url, wait_until="domcontentloaded", timeout=30000)

# 2. Wait for specific Angular component
await page.wait_for_selector("app-infracao-veiculo-lista", state="visible", timeout=30000)

# 3. Wait for network to be idle (optional, but recommended)
await page.wait_for_load_state("networkidle", timeout=10000)

# 4. Give Angular time to stabilize
await asyncio.sleep(1.5)

# 5. Now interact with elements
```

### 8.2 Error Handling

**Recommended Pattern:**
```python
try:
    await page.goto(url, timeout=30000)
    await page.wait_for_selector("app-infracao-veiculo-lista", timeout=30000)
except PlaywrightTimeoutError:
    # Check for CAPTCHA
    captcha_present = await detect_captcha(page)
    if captcha_present:
        await solve_captcha(page)
        # Retry navigation
    else:
        # Log error and retry with backoff
        await asyncio.sleep(5)
        # Retry logic
```

### 8.3 Human-Like Behavior

**Your project already implements this - maintain these practices:**
1. ✅ Random delays between actions (500-2000ms)
2. ✅ Simulate reading time (1-3 seconds)
3. ✅ Random scrolling
4. ✅ Human-like mouse movements
5. ✅ Persistent browser context

### 8.4 Monitoring & Logging

**Recommended:**
1. Log all navigation events
2. Monitor for CAPTCHA appearances
3. Track API response times
4. Log errors with context
5. Monitor for rate limiting indicators

---

## 9. Security Considerations

### 9.1 Authentication

**Unknown Authentication Mechanism:**
- May use:
  - OAuth/OIDC (common in government portals)
  - JWT tokens
  - Session-based authentication
  - Certificate-based authentication

**Recommendations:**
1. Monitor network requests during login to identify auth flow
2. Preserve authentication cookies/tokens in persistent context
3. Handle token refresh if implemented
4. Monitor for authentication redirects

### 9.2 Data Privacy

**Sensitive Data:**
- Vehicle information
- Personal identification
- Fine details
- License information

**Recommendations:**
1. ⚠️ Ensure secure storage of any scraped data
2. ⚠️ Comply with data protection regulations
3. ⚠️ Don't log sensitive information
4. ⚠️ Use HTTPS for all communications (already enforced via HSTS)

### 9.3 Rate Limiting & Abuse Prevention

**Potential Protections:**
1. CAPTCHA (hCaptcha) - confirmed
2. Rate limiting on API endpoints - unknown
3. IP-based blocking - possible
4. Browser fingerprinting - possible (via hCaptcha)

**Recommendations:**
1. Implement respectful rate limiting (max 1 request per second)
2. Use persistent browser context to appear as returning user
3. Rotate user agents if needed (but be consistent)
4. Monitor for blocking/rate limit responses

---

## 10. Performance Characteristics

### 10.1 Load Times

**Factors Affecting Performance:**
- Large JavaScript bundles (Angular app)
- Multiple external dependencies (CDN resources)
- API calls on page load
- CAPTCHA loading (external script)

**Typical Load Sequence:**
1. HTML document loads
2. JavaScript bundles download (may take 2-5 seconds)
3. Angular initializes
4. API calls fetch data
5. Components render
6. CAPTCHA loads (if triggered)

**Estimated Total Load Time:** 5-10 seconds for initial load

### 10.2 Optimization Opportunities

**For Automation:**
1. ✅ Use persistent context (reduces repeated downloads)
2. ✅ Cache static assets (browser handles this)
3. ⚠️ Cannot cache API responses (no-cache headers)
4. ✅ Pre-load common pages if possible

---

## 11. Testing Recommendations

### 11.1 Test Scenarios

**Critical Paths to Test:**
1. ✅ Navigation to fines page
2. ✅ Vehicle list loading
3. ✅ Vehicle detail page navigation
4. ✅ Pagination handling
5. ✅ CAPTCHA solving
6. ✅ Error handling (timeouts, network errors)
7. ✅ Session persistence

### 11.2 Monitoring Points

**Key Metrics to Monitor:**
1. Page load success rate
2. CAPTCHA appearance frequency
3. API response times
4. Error rates
5. Session expiration events
6. Rate limiting triggers

---

## 12. Conclusion & Next Steps

### 12.1 Key Takeaways

1. **Angular SPA:** Requires waiting for JavaScript execution and Angular initialization
2. **Hash Routing:** Use hash-based URLs for direct navigation
3. **CAPTCHA:** hCaptcha is present - ensure your solver supports it
4. **Security:** Missing some security headers, but HSTS is present
5. **API Pattern:** RESTful API with `/portalservicos-ws/` prefix
6. **Cache Strategy:** Aggressive caching for static assets, no-cache for APIs

### 12.2 Immediate Actions

1. ✅ Verify hCaptcha support in `captcha_solver.py`
2. ✅ Ensure wait strategies account for Angular initialization
3. ✅ Test navigation with hash-based URLs
4. ✅ Monitor for rate limiting on API endpoints
5. ✅ Implement proper error handling for CAPTCHA triggers

### 12.3 Long-Term Considerations

1. Monitor for website updates (Angular version, structure changes)
2. Implement adaptive wait strategies based on load times
3. Consider implementing API-level automation (if allowed)
4. Maintain compatibility with security policy changes
5. Document any new endpoints discovered during development

---

## Appendix A: Technical Specifications

### A.1 Detected Technologies

- **Frontend Framework:** Angular (version unknown)
- **Routing:** Angular Router (hash-based)
- **UI Components:** Brazil Design System (`br-*` components)
- **CAPTCHA:** hCaptcha
- **CDN:** Cloudflare (for hCaptcha), jsDelivr, SERPRO CDN
- **Accessibility:** VLibras plugin
- **Government Bar:** Barra Brasil component

### A.2 Network Architecture

```
Client Browser
    ↓
HTTPS (HSTS enforced)
    ↓
portalservicos.senatran.serpro.gov.br
    ├── Static Assets (CDN cached)
    ├── API Endpoints (/portalservicos-ws/*)
    └── External Dependencies
        ├── hCaptcha (js.hcaptcha.com)
        ├── Brazil Design System (cdngovbr-ds.estaleiro.serpro.gov.br)
        └── Accessibility Tools (vlibras.gov.br)
```

### A.3 File Structure Patterns

**JavaScript Bundles:**
- `runtime-*.js` - Angular runtime
- `polyfills-*.js` - Browser polyfills
- `main-*.js` - Main application code
- `scripts-*.js` - Additional scripts
- `styles-*.css` - Compiled styles

**Naming Convention:** Hash-based filenames for cache busting (e.g., `main-es2015.27bb3ae484a4022c35a4.js`)

---

## Appendix B: Reference URLs

### B.1 Main URLs
- Home: `https://portalservicos.senatran.serpro.gov.br/#/home`
- Fines: `https://portalservicos.senatran.serpro.gov.br/#/infracoes/consultar/veiculo`

### B.2 API Endpoints
- Home Data: `GET /portalservicos-ws/funcionalidade/home`
- Campaigns: `GET /portalservicos-ws/campanha/vigentes/ambito/2`

### B.3 External Services
- hCaptcha: `https://js.hcaptcha.com/1/api.js`
- Brazil Design System: `https://cdngovbr-ds.estaleiro.serpro.gov.br/`
- VLibras: `https://vlibras.gov.br/app2/vlibras-plugin.js`

---

**Document Version:** 1.0  
**Last Updated:** December 9, 2025  
**Next Review:** When website structure changes or new features are added

