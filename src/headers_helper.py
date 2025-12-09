"""
HTTP Headers Enhancement Helper
Sets realistic and complete HTTP headers to match real browsers.
This helps avoid basic detection by ensuring headers match expected browser behavior.
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


def get_enhanced_headers(
    locale: str = "pt-BR",
    browser_type: str = "chromium",
    user_agent: str = None
) -> Dict[str, str]:
    """
    Generate comprehensive HTTP headers that match real browser behavior.
    
    Args:
        locale: Browser locale (e.g., "pt-BR", "en-US")
        browser_type: Browser type ("chromium", "firefox", "webkit")
        user_agent: User agent string (used to determine browser version)
    
    Returns:
        Dictionary of HTTP headers
    """
    # Base headers that work for all browsers
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": _get_accept_language(locale),
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "DNT": "1",  # Do Not Track
    }
    
    # Browser-specific headers
    if browser_type == "chromium":
        headers.update(_get_chromium_headers(user_agent))
    elif browser_type == "firefox":
        headers.update(_get_firefox_headers(user_agent))
    elif browser_type == "webkit":
        headers.update(_get_webkit_headers(user_agent))
    
    return headers


def _get_accept_language(locale: str) -> str:
    """
    Generate Accept-Language header based on locale.
    
    Args:
        locale: Browser locale (e.g., "pt-BR", "en-US")
    
    Returns:
        Accept-Language header value
    """
    # Map locales to language preferences
    language_map = {
        "pt-BR": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "en-US": "en-US,en;q=0.9",
        "en-GB": "en-GB,en;q=0.9",
        "es-ES": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
        "fr-FR": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    return language_map.get(locale, "en-US,en;q=0.9")


def _get_chromium_headers(user_agent: str = None) -> Dict[str, str]:
    """
    Get Chromium/Chrome-specific headers.
    
    Args:
        user_agent: User agent string to determine Chrome version
    
    Returns:
        Dictionary of Chromium-specific headers
    """
    headers = {
        "sec-ch-ua": _get_sec_ch_ua(user_agent),
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }
    
    return headers


def _get_firefox_headers(user_agent: str = None) -> Dict[str, str]:
    """
    Get Firefox-specific headers.
    
    Args:
        user_agent: User agent string (not used for Firefox currently)
    
    Returns:
        Dictionary of Firefox-specific headers
    """
    # Firefox doesn't use sec-ch-ua headers
    return {}


def _get_webkit_headers(user_agent: str = None) -> Dict[str, str]:
    """
    Get WebKit/Safari-specific headers.
    
    Args:
        user_agent: User agent string (not used for WebKit currently)
    
    Returns:
        Dictionary of WebKit-specific headers
    """
    # Safari uses different headers
    return {}


def _get_sec_ch_ua(user_agent: str = None) -> str:
    """
    Generate sec-ch-ua header for Chromium browsers.
    This header indicates browser brand and version.
    
    Args:
        user_agent: User agent string to extract version info
    
    Returns:
        sec-ch-ua header value
    """
    # Default Chrome 120 values (update as needed)
    default = '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"'
    
    if not user_agent:
        return default
    
    # Try to extract Chrome version from user agent
    try:
        # User agent format: "Mozilla/5.0 ... Chrome/120.0.0.0 ..."
        if "Chrome/" in user_agent:
            # Extract version number
            chrome_part = user_agent.split("Chrome/")[1].split()[0]
            version = chrome_part.split(".")[0]
            
            # Generate sec-ch-ua based on version
            # Chrome 120+ format
            return f'"Not_A Brand";v="8", "Chromium";v="{version}", "Google Chrome";v="{version}"'
    except Exception:
        pass
    
    return default


def apply_headers_to_context(context, headers: Dict[str, str]) -> None:
    """
    Apply HTTP headers to a Playwright browser context.
    
    Args:
        context: Playwright BrowserContext object
        headers: Dictionary of HTTP headers to apply
    """
    try:
        context.set_extra_http_headers(headers)
        logger.debug(f"Applied {len(headers)} HTTP headers to context")
    except Exception as e:
        logger.warning(f"Failed to apply HTTP headers: {e}")


def get_navigation_headers(url: str, referer: str = None) -> Dict[str, str]:
    """
    Get headers specific to navigation requests.
    These may differ from initial page load headers.
    
    Args:
        url: Target URL
        referer: Referer URL (if navigating from another page)
    
    Returns:
        Dictionary of navigation-specific headers
    """
    headers = {
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin" if referer else "none",
        "Sec-Fetch-User": "?1",
    }
    
    if referer:
        headers["Referer"] = referer
    
    return headers


def get_ajax_headers(referer: str) -> Dict[str, str]:
    """
    Get headers for AJAX/XHR requests.
    These differ from navigation headers.
    
    Args:
        referer: Referer URL
    
    Returns:
        Dictionary of AJAX request headers
    """
    return {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Content-Type": "application/json",
        "Referer": referer,
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "X-Requested-With": "XMLHttpRequest",
    }
