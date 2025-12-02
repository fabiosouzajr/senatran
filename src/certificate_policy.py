"""
Certificate policy manager for automatic certificate selection.
Creates Chrome/Chromium policy files to auto-select certificates.
"""

import json
import logging
import platform
from pathlib import Path
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class CertificatePolicyManager:
    """Manages Chrome/Chromium certificate auto-selection policies."""
    
    def __init__(self, user_data_dir: Optional[Path] = None):
        """
        Initialize certificate policy manager.
        
        Args:
            user_data_dir: Chrome user data directory (default: Playwright's default)
        """
        self.user_data_dir = user_data_dir
        self.platform = platform.system()
    
    def get_policy_directory(self, user_data_dir: Optional[Path] = None) -> Optional[Path]:
        """
        Get the policy directory for the current platform.
        
        Args:
            user_data_dir: User data directory (if provided, use this instead of auto-detect)
        
        Returns:
            Path to policy directory or None if not supported.
        """
        if user_data_dir:
            # Use provided user data dir
            # Chrome expects policies in: user_data_dir/Default/Managed Preferences/auto_select_cert.json
            # OR: user_data_dir/Default/policies/managed/auto_select_cert.json
            # OR: user_data_dir/Default/policies/auto_select_cert.json
            # Try the most common location first
            policy_dir = user_data_dir / "Default" / "policies"
        elif self.user_data_dir:
            policy_dir = self.user_data_dir / "Default" / "policies"
        else:
            # Use Playwright's default location
            if self.platform == "Linux":
                # Playwright uses ~/.cache/ms-playwright/chromium-*/Default
                policy_dir = Path.home() / ".cache" / "ms-playwright" / "chromium-*" / "Default" / "policies"
            elif self.platform == "Windows":
                policy_dir = Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Default" / "policies"
            elif self.platform == "Darwin":  # macOS
                policy_dir = Path.home() / "Library" / "Application Support" / "Google" / "Chrome" / "Default" / "policies"
            else:
                logger.warning(f"Unsupported platform for policy files: {self.platform}")
                return None
        
        return policy_dir
    
    def create_policy_file(self, 
                          urls: List[str], 
                          certificate_name: str,
                          policy_dir: Optional[Path] = None,
                          user_data_dir: Optional[Path] = None) -> Optional[Path]:
        """
        Create Chrome policy file for automatic certificate selection.
        
        Args:
            urls: List of URL patterns to match (e.g., ["https://sso.acesso.gov.br/*"])
            certificate_name: Name or pattern of certificate to auto-select
            policy_dir: Directory to create policy file (default: auto-detect)
            user_data_dir: User data directory (for determining policy location)
        
        Returns:
            Path to created policy file or None if failed.
        """
        if policy_dir is None:
            policy_dir = self.get_policy_directory(user_data_dir)
        
        if policy_dir is None:
            logger.warning("Cannot determine policy directory")
            return None
        
        try:
            # Create policy directory structure
            policy_dir.mkdir(parents=True, exist_ok=True)
            
            # Policy file path - Chrome expects it in the policies directory
            policy_file = policy_dir / "auto_select_cert.json"
            
            # Create policy structure
            # Chrome expects the format:
            # [{"pattern": "https://example.com/*", "filter": {"SUBJECT": {"CN": "Certificate Name"}}}]
            # OR with wildcard matching:
            # [{"pattern": "https://example.com/*", "filter": {"SUBJECT": {"CN": "*certificate_name*"}}}]
            policy_data = []
            
            for url_pattern in urls:
                # Try both exact match and pattern match
                policy_entry = {
                    "pattern": url_pattern,
                    "filter": {
                        "SUBJECT": {
                            "CN": certificate_name
                        }
                    }
                }
                policy_data.append(policy_entry)
                
                # Also add a wildcard version for better matching
                if "*" not in certificate_name:
                    policy_entry_wildcard = {
                        "pattern": url_pattern,
                        "filter": {
                            "SUBJECT": {
                                "CN": f"*{certificate_name}*"
                            }
                        }
                    }
                    policy_data.append(policy_entry_wildcard)
            
            # Write policy file
            with open(policy_file, 'w', encoding='utf-8') as f:
                json.dump(policy_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Created certificate policy file: {policy_file}")
            logger.debug(f"Policy content: {json.dumps(policy_data, indent=2)}")
            
            return policy_file
            
        except Exception as e:
            logger.error(f"Error creating policy file: {e}")
            return None
    
    def create_policy_file_alternative_format(self,
                                            urls: List[str],
                                            certificate_name: str,
                                            policy_dir: Optional[Path] = None,
                                            user_data_dir: Optional[Path] = None) -> Optional[Path]:
        """
        Create policy file using alternative format (if first format doesn't work).
        
        Some Chrome versions use a different format:
        {
          "AutoSelectCertificateForUrls": [
            {
              "pattern": "https://example.com/*",
              "filter": {
                "SUBJECT": {
                  "CN": "Certificate Name"
                }
              }
            }
          ]
        }
        
        Args:
            urls: List of URL patterns
            certificate_name: Certificate name pattern
            policy_dir: Policy directory
        
        Returns:
            Path to policy file or None
        """
        if policy_dir is None:
            policy_dir = self.get_policy_directory(user_data_dir)
        
        if policy_dir is None:
            return None
        
        try:
            policy_dir.mkdir(parents=True, exist_ok=True)
            policy_file = policy_dir / "auto_select_cert.json"
            
            policy_entries = []
            for url_pattern in urls:
                policy_entries.append({
                    "pattern": url_pattern,
                    "filter": {
                        "SUBJECT": {
                            "CN": certificate_name
                        }
                    }
                })
            
            policy_data = {
                "AutoSelectCertificateForUrls": policy_entries
            }
            
            with open(policy_file, 'w', encoding='utf-8') as f:
                json.dump(policy_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Created alternative format policy file: {policy_file}")
            return policy_file
            
        except Exception as e:
            logger.error(f"Error creating alternative policy file: {e}")
            return None
    
    def setup_certificate_policy(self,
                                urls: List[str],
                                certificate_name: str,
                                user_data_dir: Optional[Path] = None) -> bool:
        """
        Setup certificate auto-selection policy for Chrome/Chromium.
        
        Args:
            urls: List of URL patterns to match
            certificate_name: Certificate name pattern
            user_data_dir: User data directory (for Playwright context)
        
        Returns:
            True if policy was created successfully
        """
        if user_data_dir:
            self.user_data_dir = user_data_dir
        
        # Try primary format first
        policy_file = self.create_policy_file(urls, certificate_name)
        
        if policy_file and policy_file.exists():
            logger.info("✓ Certificate policy file created successfully")
            return True
        
        # Try alternative format
        logger.info("Trying alternative policy file format...")
        policy_file = self.create_policy_file_alternative_format(urls, certificate_name)
        
        if policy_file and policy_file.exists():
            logger.info("✓ Certificate policy file created (alternative format)")
            return True
        
        logger.warning("Failed to create certificate policy file")
        return False
    
    def get_user_data_dir_for_context(self, context) -> Optional[Path]:
        """
        Get user data directory from Playwright context.
        
        Args:
            context: Playwright browser context
        
        Returns:
            Path to user data directory or None
        """
        try:
            # Playwright stores user data in a temporary directory
            # We can get it from the context's pages
            if hasattr(context, '_browser') and hasattr(context._browser, '_user_data_dir'):
                return Path(context._browser._user_data_dir)
        except:
            pass
        
        return None

