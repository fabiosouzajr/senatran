"""
Certificate checker to verify if certificate is installed in system certificate store.
"""

import logging
import platform
import subprocess
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class CertificateChecker:
    """Checks if certificate is installed in system certificate store."""
    
    def __init__(self):
        """Initialize certificate checker."""
        self.platform = platform.system()
    
    def check_certificate_installed(self, certificate_name: Optional[str] = None) -> Tuple[bool, str]:
        """
        Check if certificate is installed in system certificate store.
        
        Args:
            certificate_name: Name or pattern to search for in certificate store
        
        Returns:
            Tuple of (is_installed: bool, message: str)
        """
        if self.platform == "Windows":
            return self._check_windows(certificate_name)
        elif self.platform == "Linux":
            return self._check_linux(certificate_name)
        elif self.platform == "Darwin":  # macOS
            return self._check_macos(certificate_name)
        else:
            return False, f"Certificate checking not implemented for platform: {self.platform}"
    
    def _check_windows(self, certificate_name: Optional[str]) -> Tuple[bool, str]:
        """Check certificate store on Windows."""
        try:
            # Use certutil to list certificates
            # Check in CurrentUser/My store (personal certificates)
            result = subprocess.run(
                ['certutil', '-store', '-user', 'My'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                output = result.stdout.lower()
                
                # If certificate name provided, search for it
                if certificate_name:
                    if certificate_name.lower() in output:
                        return True, f"Certificate '{certificate_name}' found in Windows certificate store"
                    else:
                        return False, f"Certificate '{certificate_name}' not found in Windows certificate store"
                else:
                    # Just check if any certificates exist
                    if "certificate" in output and "serial number" in output:
                        return True, "Certificates found in Windows certificate store"
                    else:
                        return False, "No certificates found in Windows certificate store"
            else:
                return False, f"Error checking Windows certificate store: {result.stderr}"
                
        except FileNotFoundError:
            return False, "certutil not found - cannot check Windows certificate store"
        except subprocess.TimeoutExpired:
            return False, "Timeout checking Windows certificate store"
        except Exception as e:
            return False, f"Error checking Windows certificate store: {e}"
    
    def _check_linux(self, certificate_name: Optional[str]) -> Tuple[bool, str]:
        """Check certificate store on Linux."""
        # Linux certificate stores vary by distribution and browser
        # Common locations:
        # - NSS (Firefox/Chrome): ~/.pki/nssdb
        # - System-wide: /etc/ssl/certs/
        # - User: ~/.local/share/ca-certificates/
        
        checks = []
        
        # Check NSS database (Firefox/Chrome)
        nss_db_path = Path.home() / '.pki' / 'nssdb'
        if nss_db_path.exists():
            try:
                result = subprocess.run(
                    ['certutil', '-L', '-d', f'sql:{nss_db_path}'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0 and result.stdout:
                    checks.append("NSS database found")
                    if certificate_name and certificate_name.lower() in result.stdout.lower():
                        return True, f"Certificate '{certificate_name}' found in NSS database"
            except:
                pass
        
        # Check system certificates
        system_certs = Path('/etc/ssl/certs')
        if system_certs.exists():
            cert_count = len(list(system_certs.glob('*.crt'))) + len(list(system_certs.glob('*.pem')))
            if cert_count > 0:
                checks.append(f"System certificates found ({cert_count} files)")
        
        # Check user certificates
        user_certs = Path.home() / '.local' / 'share' / 'ca-certificates'
        if user_certs.exists():
            cert_count = len(list(user_certs.glob('*.crt'))) + len(list(user_certs.glob('*.pem')))
            if cert_count > 0:
                checks.append(f"User certificates found ({cert_count} files)")
        
        if checks:
            return True, f"Certificate stores found: {', '.join(checks)}"
        else:
            return False, "No certificate stores found on Linux system"
    
    def _check_macos(self, certificate_name: Optional[str]) -> Tuple[bool, str]:
        """Check certificate store on macOS (Keychain)."""
        try:
            # Use security command to list certificates
            result = subprocess.run(
                ['security', 'find-certificate', '-a', '-p', '/Library/Keychains/System.keychain'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout:
                if certificate_name:
                    if certificate_name.lower() in result.stdout.lower():
                        return True, f"Certificate '{certificate_name}' found in macOS Keychain"
                    else:
                        return False, f"Certificate '{certificate_name}' not found in macOS Keychain"
                else:
                    return True, "Certificates found in macOS Keychain"
            else:
                # Try user keychain
                result = subprocess.run(
                    ['security', 'find-certificate', '-a', '-p', '~/Library/Keychains/login.keychain-db'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0 and result.stdout:
                    return True, "Certificates found in user Keychain"
                else:
                    return False, "No certificates found in macOS Keychain"
                    
        except FileNotFoundError:
            return False, "security command not found - cannot check macOS Keychain"
        except subprocess.TimeoutExpired:
            return False, "Timeout checking macOS Keychain"
        except Exception as e:
            return False, f"Error checking macOS Keychain: {e}"
    
    def get_installation_instructions(self) -> str:
        """Get platform-specific instructions for installing certificate."""
        if self.platform == "Windows":
            return """
To install the certificate on Windows:
1. Double-click the certificate file (certificado.crt or certificado_novamobilidade-25.pem)
2. Click "Install Certificate"
3. Select "Current User" or "Local Machine"
4. Choose "Place all certificates in the following store"
5. Click "Browse" and select "Personal" or "Trusted Root Certification Authorities"
6. Click "Next" and "Finish"
            """
        elif self.platform == "Linux":
            return """
To install the certificate on Linux:

Option 1 - System-wide (requires sudo):
  sudo cp cert/certificado.crt /usr/local/share/ca-certificates/
  sudo update-ca-certificates

Option 2 - Firefox/Chrome (NSS database):
  certutil -d sql:$HOME/.pki/nssdb -A -t "C,," -n "Senatran Certificate" -i cert/certificado.crt

Option 3 - User certificates:
  mkdir -p ~/.local/share/ca-certificates
  cp cert/certificado.crt ~/.local/share/ca-certificates/
            """
        elif self.platform == "Darwin":  # macOS
            return """
To install the certificate on macOS:
1. Double-click the certificate file
2. Keychain Access will open
3. Select "login" or "System" keychain
4. Enter your password if prompted
5. The certificate will be added to your keychain
            """
        else:
            return f"Installation instructions not available for platform: {self.platform}"

