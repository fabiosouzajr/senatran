"""
Website Technical Auditor
Comprehensive analysis tool for understanding website architecture, security, and implementation details.
Analyzes frameworks, security policies, cache implementation, cookies, and more.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, urljoin

from playwright.async_api import async_playwright, Page, Response, Request
from bs4 import BeautifulSoup
import httpx

import src.config as config


class WebsiteAuditor:
    """Comprehensive website auditor for technical analysis."""
    
    def __init__(self, target_url: str):
        self.target_url = target_url
        self.parsed_url = urlparse(target_url)
        self.base_url = f"{self.parsed_url.scheme}://{self.parsed_url.netloc}"
        self.findings: Dict[str, Any] = {
            "url": target_url,
            "audit_date": datetime.now().isoformat(),
            "frameworks": {},
            "security": {},
            "cookies": {},
            "cache": {},
            "architecture": {},
            "api_endpoints": [],
            "resources": [],
            "headers": {},
            "javascript": {},
            "performance": {},
            "recommendations": []
        }
        self.network_requests: List[Dict] = []
        self.network_responses: List[Dict] = []
        
    async def audit(self) -> Dict[str, Any]:
        """Run comprehensive website audit."""
        print(f"🔍 Starting technical audit of {self.target_url}")
        print("=" * 80)
        
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=False,  # Use headed mode for better compatibility
                args=config.BROWSER_ARGS
            )
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=config.USER_AGENT or None,
                locale="pt-BR",
                timezone_id="America/Sao_Paulo",
                ignore_https_errors=True
            )
            
            page = await context.new_page()
            
            # Set up network monitoring
            page.on("request", self._on_request)
            page.on("response", self._on_response)
            
            try:
                # Navigate and wait for page load
                print("\n📡 Loading page and capturing network traffic...")
                try:
                    response = await page.goto(
                        self.target_url,
                        wait_until="domcontentloaded",
                        timeout=90000
                    )
                except Exception as e:
                    print(f"⚠️  Navigation timeout/error: {e}")
                    print("Continuing with partial analysis...")
                    response = None
                
                if response:
                    self.findings["status_code"] = response.status
                    self.findings["headers"] = dict(response.headers)
                
                # Wait a bit for SPA to initialize
                await asyncio.sleep(5)
                
                # Try to wait for specific elements that indicate page is loaded
                try:
                    await page.wait_for_selector("body", timeout=10000)
                except:
                    pass
                
                # Get page content
                print("\n📄 Analyzing page content...")
                html_content = await page.content()
                self._analyze_html(html_content)
                
                # Analyze security headers
                print("\n🔒 Analyzing security headers...")
                self._analyze_security_headers(response.headers if response else {})
                
                # Analyze cookies
                print("\n🍪 Analyzing cookies...")
                cookies = await context.cookies()
                self._analyze_cookies(cookies)
                
                # Analyze cache policies
                print("\n💾 Analyzing cache policies...")
                self._analyze_cache_policies()
                
                # Analyze JavaScript
                print("\n📜 Analyzing JavaScript...")
                await self._analyze_javascript(page)
                
                # Analyze frameworks
                print("\n⚙️  Detecting frameworks and technologies...")
                await self._detect_frameworks(page)
                
                # Analyze API endpoints
                print("\n🔌 Analyzing API endpoints...")
                self._analyze_api_endpoints()
                
                # Analyze architecture
                print("\n🏗️  Analyzing architecture patterns...")
                self._analyze_architecture()
                
                # Generate recommendations
                print("\n💡 Generating recommendations...")
                self._generate_recommendations()
                
            except Exception as e:
                print(f"\n❌ Error during audit: {e}")
                self.findings["error"] = str(e)
            finally:
                await browser.close()
        
        return self.findings
    
    def _on_request(self, request: Request):
        """Capture network requests."""
        self.network_requests.append({
            "url": request.url,
            "method": request.method,
            "headers": request.headers,
            "resource_type": request.resource_type,
            "post_data": request.post_data
        })
    
    def _on_response(self, response: Response):
        """Capture network responses."""
        self.network_responses.append({
            "url": response.url,
            "status": response.status,
            "headers": dict(response.headers),
            "content_type": response.headers.get("content-type", ""),
        })
    
    def _analyze_html(self, html: str):
        """Analyze HTML structure and content."""
        soup = BeautifulSoup(html, 'lxml')
        
        # Detect meta tags
        meta_tags = {}
        for meta in soup.find_all("meta"):
            name = meta.get("name") or meta.get("property") or meta.get("http-equiv")
            content = meta.get("content")
            if name and content:
                meta_tags[name.lower()] = content
        
        self.findings["architecture"]["meta_tags"] = meta_tags
        
        # Detect Angular/AngularJS
        if soup.find("app-root") or soup.find("ng-app") or soup.find_all(attrs={"ng-controller": True}):
            self.findings["frameworks"]["angular"] = True
            # Try to detect version
            scripts = soup.find_all("script", src=True)
            for script in scripts:
                src = script.get("src", "")
                if "angular" in src.lower():
                    self.findings["frameworks"]["angular_version"] = "detected"
        
        # Detect React
        if soup.find(id="root") or soup.find_all(attrs={"data-reactroot": True}):
            self.findings["frameworks"]["react"] = True
        
        # Detect Vue
        if soup.find(id="app") or soup.find_all(attrs={"v-if": True}):
            self.findings["frameworks"]["vue"] = True
        
        # Detect custom elements (Web Components)
        custom_elements = [tag.name for tag in soup.find_all() if "-" in tag.name]
        if custom_elements:
            self.findings["architecture"]["custom_elements"] = list(set(custom_elements))[:20]
        
        # Detect routing pattern (SPA)
        if "#/" in self.target_url or soup.find_all(attrs={"ng-view": True}) or soup.find_all(attrs={"ui-view": True}):
            self.findings["architecture"]["spa"] = True
            self.findings["architecture"]["routing"] = "hash-based" if "#/" in self.target_url else "history-based"
        
        # Detect CDN usage
        cdn_domains = set()
        for script in soup.find_all("script", src=True):
            src = script.get("src", "")
            if src.startswith("http"):
                domain = urlparse(src).netloc
                if domain != self.parsed_url.netloc:
                    cdn_domains.add(domain)
        
        for link in soup.find_all("link", href=True):
            href = link.get("href", "")
            if href.startswith("http"):
                domain = urlparse(href).netloc
                if domain != self.parsed_url.netloc:
                    cdn_domains.add(domain)
        
        if cdn_domains:
            self.findings["architecture"]["cdn_domains"] = list(cdn_domains)
    
    def _analyze_security_headers(self, headers: Dict[str, str]):
        """Analyze security-related HTTP headers."""
        security_headers = {
            "content_security_policy": headers.get("content-security-policy"),
            "strict_transport_security": headers.get("strict-transport-security"),
            "x_frame_options": headers.get("x-frame-options"),
            "x_content_type_options": headers.get("x-content-type-options"),
            "x_xss_protection": headers.get("x-xss-protection"),
            "referrer_policy": headers.get("referrer-policy"),
            "permissions_policy": headers.get("permissions-policy"),
            "cross_origin_embedder_policy": headers.get("cross-origin-embedder-policy"),
            "cross_origin_opener_policy": headers.get("cross-origin-opener-policy"),
            "cross_origin_resource_policy": headers.get("cross-origin-resource-policy"),
        }
        
        self.findings["security"]["headers"] = security_headers
        
        # Security analysis
        security_analysis = {
            "csp_present": bool(security_headers["content_security_policy"]),
            "hsts_present": bool(security_headers["strict_transport_security"]),
            "frame_protection": bool(security_headers["x_frame_options"]),
            "mime_sniffing_protection": bool(security_headers["x_content_type_options"]),
            "xss_protection": bool(security_headers["x_xss_protection"]),
        }
        
        self.findings["security"]["analysis"] = security_analysis
        
        # Check for vulnerabilities
        if not security_headers["strict_transport_security"]:
            self.findings["recommendations"].append(
                "⚠️  HSTS header not present - consider adding Strict-Transport-Security"
            )
        
        if not security_headers["content_security_policy"]:
            self.findings["recommendations"].append(
                "⚠️  CSP header not present - consider adding Content-Security-Policy"
            )
        
        if not security_headers["x_frame_options"]:
            self.findings["recommendations"].append(
                "⚠️  X-Frame-Options not present - consider adding to prevent clickjacking"
            )
    
    def _analyze_cookies(self, cookies: List[Dict]):
        """Analyze cookie usage and policies."""
        cookie_analysis = {
            "total_cookies": len(cookies),
            "http_only": 0,
            "secure": 0,
            "same_site": {"strict": 0, "lax": 0, "none": 0, "unspecified": 0},
            "session_cookies": 0,
            "persistent_cookies": 0,
            "cookies_by_domain": {},
            "cookie_names": []
        }
        
        for cookie in cookies:
            cookie_analysis["cookie_names"].append(cookie.get("name", ""))
            
            if cookie.get("httpOnly"):
                cookie_analysis["http_only"] += 1
            
            if cookie.get("secure"):
                cookie_analysis["secure"] += 1
            
            same_site = cookie.get("sameSite", "").lower()
            if same_site in cookie_analysis["same_site"]:
                cookie_analysis["same_site"][same_site] += 1
            else:
                cookie_analysis["same_site"]["unspecified"] += 1
            
            if cookie.get("expires") == -1:
                cookie_analysis["session_cookies"] += 1
            else:
                cookie_analysis["persistent_cookies"] += 1
            
            domain = cookie.get("domain", "")
            cookie_analysis["cookies_by_domain"][domain] = \
                cookie_analysis["cookies_by_domain"].get(domain, 0) + 1
        
        self.findings["cookies"] = cookie_analysis
        
        # Recommendations
        insecure_cookies = cookie_analysis["total_cookies"] - cookie_analysis["secure"]
        if insecure_cookies > 0:
            self.findings["recommendations"].append(
                f"⚠️  {insecure_cookies} cookie(s) not marked as Secure - consider using Secure flag for HTTPS-only cookies"
            )
        
        if cookie_analysis["same_site"]["unspecified"] > 0:
            self.findings["recommendations"].append(
                f"⚠️  {cookie_analysis['same_site']['unspecified']} cookie(s) without SameSite attribute - consider setting SameSite=Lax or Strict"
            )
    
    def _analyze_cache_policies(self):
        """Analyze cache control policies from responses."""
        cache_analysis = {
            "cache_control_present": 0,
            "etag_present": 0,
            "last_modified_present": 0,
            "cache_policies": [],
            "no_cache_resources": 0,
            "max_age_values": []
        }
        
        for response in self.network_responses:
            headers = response.get("headers", {})
            
            cache_control = headers.get("cache-control", "")
            if cache_control:
                cache_analysis["cache_control_present"] += 1
                cache_analysis["cache_policies"].append({
                    "url": response["url"],
                    "cache_control": cache_control
                })
                
                if "no-cache" in cache_control.lower() or "no-store" in cache_control.lower():
                    cache_analysis["no_cache_resources"] += 1
                
                # Extract max-age
                if "max-age" in cache_control.lower():
                    try:
                        max_age = int(cache_control.lower().split("max-age=")[1].split(",")[0].strip())
                        cache_analysis["max_age_values"].append(max_age)
                    except:
                        pass
            
            if headers.get("etag"):
                cache_analysis["etag_present"] += 1
            
            if headers.get("last-modified"):
                cache_analysis["last_modified_present"] += 1
        
        self.findings["cache"] = cache_analysis
    
    async def _analyze_javascript(self, page: Page):
        """Analyze JavaScript usage and frameworks."""
        js_analysis = {
            "total_scripts": 0,
            "inline_scripts": 0,
            "external_scripts": 0,
            "frameworks_detected": [],
            "libraries_detected": []
        }
        
        # Check for common frameworks in window object
        framework_checks = {
            "angular": "window.angular || window.ng",
            "react": "window.React",
            "vue": "window.Vue",
            "jquery": "window.jQuery || window.$",
            "backbone": "window.Backbone",
            "ember": "window.Ember",
        }
        
        for framework, check in framework_checks.items():
            try:
                result = await page.evaluate(f"typeof {check.split(' || ')[0].split('.')[1]} !== 'undefined'")
                if result:
                    js_analysis["frameworks_detected"].append(framework)
            except:
                pass
        
        # Count scripts
        script_count = await page.evaluate("document.querySelectorAll('script').length")
        js_analysis["total_scripts"] = script_count
        
        # Check for inline vs external
        inline_count = await page.evaluate("""
            Array.from(document.querySelectorAll('script')).filter(s => !s.src).length
        """)
        js_analysis["inline_scripts"] = inline_count
        js_analysis["external_scripts"] = script_count - inline_count
        
        self.findings["javascript"] = js_analysis
    
    async def _detect_frameworks(self, page: Page):
        """Detect web frameworks and technologies."""
        # Check for Angular
        angular_detected = await page.evaluate("""
            () => {
                return !!(
                    window.angular ||
                    window.ng ||
                    document.querySelector('app-root') ||
                    document.querySelector('[ng-app]')
                );
            }
        """)
        
        if angular_detected:
            self.findings["frameworks"]["angular"] = True
            # Try to get Angular version
            try:
                version = await page.evaluate("window.angular?.version?.full || 'unknown'")
                self.findings["frameworks"]["angular_version"] = version
            except:
                self.findings["frameworks"]["angular_version"] = "detected"
        
        # Check for React
        react_detected = await page.evaluate("""
            () => {
                return !!(
                    window.React ||
                    document.querySelector('#root') ||
                    document.querySelector('[data-reactroot]')
                );
            }
        """)
        
        if react_detected:
            self.findings["frameworks"]["react"] = True
        
        # Check for Vue
        vue_detected = await page.evaluate("""
            () => {
                return !!(
                    window.Vue ||
                    document.querySelector('#app') ||
                    document.querySelector('[v-if]')
                );
            }
        """)
        
        if vue_detected:
            self.findings["frameworks"]["vue"] = True
        
        # Detect if it's a SPA
        is_spa = await page.evaluate("""
            () => {
                return window.history && window.history.pushState && 
                       (window.location.hash || document.querySelector('[ng-view]') || 
                        document.querySelector('[ui-view]'));
            }
        """)
        
        if is_spa:
            self.findings["architecture"]["spa"] = True
            self.findings["architecture"]["routing"] = "hash-based" if "#/" in self.target_url else "history-based"
    
    def _analyze_api_endpoints(self):
        """Analyze API endpoints from network requests."""
        api_endpoints = []
        api_patterns = ["/api/", "/rest/", "/graphql", "/v1/", "/v2/", ".json", ".xml"]
        
        for request in self.network_requests:
            url = request["url"]
            resource_type = request["resource_type"]
            
            # Check if it's an API call
            is_api = any(pattern in url.lower() for pattern in api_patterns) or \
                     resource_type == "xhr" or resource_type == "fetch"
            
            if is_api:
                endpoint_info = {
                    "url": url,
                    "method": request["method"],
                    "resource_type": resource_type,
                    "headers": request.get("headers", {})
                }
                api_endpoints.append(endpoint_info)
        
        self.findings["api_endpoints"] = api_endpoints[:50]  # Limit to 50
        self.findings["architecture"]["api_count"] = len(api_endpoints)
    
    def _analyze_architecture(self):
        """Analyze overall architecture patterns."""
        # Analyze resource types
        resource_types = {}
        for request in self.network_requests:
            rtype = request["resource_type"]
            resource_types[rtype] = resource_types.get(rtype, 0) + 1
        
        self.findings["architecture"]["resource_types"] = resource_types
        
        # Analyze domains
        domains = set()
        for request in self.network_requests:
            try:
                domain = urlparse(request["url"]).netloc
                domains.add(domain)
            except:
                pass
        
        self.findings["architecture"]["external_domains"] = list(domains)[:20]
        
        # Detect if using CDN
        cdn_indicators = ["cdn", "cloudfront", "cloudflare", "fastly", "akamai"]
        cdn_domains = [d for d in domains if any(indicator in d.lower() for indicator in cdn_indicators)]
        if cdn_domains:
            self.findings["architecture"]["cdn_detected"] = True
            self.findings["architecture"]["cdn_domains"] = cdn_domains
    
    def _generate_recommendations(self):
        """Generate recommendations based on findings."""
        # Add architecture-specific recommendations
        if self.findings.get("architecture", {}).get("spa"):
            self.findings["recommendations"].append(
                "✅ SPA detected - use hash-based or history-based routing for navigation"
            )
            self.findings["recommendations"].append(
                "⚠️  SPA requires waiting for JavaScript to render content - use wait_for_selector or networkidle"
            )
        
        if self.findings.get("frameworks", {}).get("angular"):
            self.findings["recommendations"].append(
                "✅ Angular framework detected - look for custom elements like <app-*> for selectors"
            )
            self.findings["recommendations"].append(
                "⚠️  Angular uses zone.js for change detection - wait for Angular to stabilize before interactions"
            )
        
        # Cookie recommendations
        cookie_count = self.findings.get("cookies", {}).get("total_cookies", 0)
        if cookie_count > 0:
            self.findings["recommendations"].append(
                f"✅ {cookie_count} cookie(s) detected - ensure persistent context is used to maintain session"
            )
        
        # Cache recommendations
        if self.findings.get("cache", {}).get("cache_control_present", 0) == 0:
            self.findings["recommendations"].append(
                "⚠️  No Cache-Control headers detected - resources may not be cached efficiently"
            )


async def main():
    """Main entry point for website auditor."""
    target_url = config.TARGET_URL
    
    print("=" * 80)
    print("🌐 WEBSITE TECHNICAL AUDITOR")
    print("=" * 80)
    print(f"Target: {target_url}\n")
    
    auditor = WebsiteAuditor(target_url)
    findings = await auditor.audit()
    
    # Save findings to JSON
    output_file = Path("website_audit_results.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(findings, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 80)
    print("✅ Audit completed!")
    print(f"📄 Results saved to: {output_file}")
    print("=" * 80)
    
    return findings


if __name__ == "__main__":
    asyncio.run(main())

