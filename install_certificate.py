#!/usr/bin/env python3
"""
Certificate Installation Script

This script helps install digital certificates into the system certificate store
for use with browser automation (Playwright/Chromium).

It supports:
- .p12 and .pfx files (PKCS#12 format with certificate + private key)
- .pem files (if they contain both certificate and private key)
- Automatic detection of certificate files in ./cert folder
- Password prompting for encrypted certificates
- Platform-specific installation (Linux NSS database, Windows certificate store, macOS Keychain)
"""

import os
import sys
import platform
import subprocess
import getpass
from pathlib import Path
from typing import Optional, Tuple, List

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_success(msg: str):
    print(f"{Colors.GREEN}✓{Colors.RESET} {msg}")

def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {msg}")

def print_error(msg: str):
    print(f"{Colors.RED}✗{Colors.RESET} {msg}")

def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ{Colors.RESET} {msg}")

def print_header(msg: str):
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{msg}{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")


class CertificateInstaller:
    """Handles certificate installation for different platforms."""
    
    def __init__(self, cert_dir: Path):
        self.cert_dir = cert_dir
        self.platform = platform.system()
        self.nss_db_path = Path.home() / '.pki' / 'nssdb'
        
    def find_certificate_files(self) -> List[Path]:
        """Find compatible certificate files in cert directory."""
        cert_files = []
        
        if not self.cert_dir.exists():
            print_error(f"Certificate directory not found: {self.cert_dir}")
            return cert_files
        
        # Look for PKCS#12 files (.p12, .pfx)
        for ext in ['.p12', '.pfx']:
            cert_files.extend(list(self.cert_dir.glob(f'*{ext}')))
        
        # Look for PEM files
        for pem_file in self.cert_dir.glob('*.pem'):
            if self._pem_has_private_key(pem_file):
                cert_files.append(pem_file)
        
        return cert_files
    
    def _pem_has_private_key(self, pem_file: Path) -> bool:
        """Check if PEM file contains a private key."""
        try:
            content = pem_file.read_text()
            # Check for private key indicators
            return '-----BEGIN PRIVATE KEY-----' in content or \
                   '-----BEGIN RSA PRIVATE KEY-----' in content or \
                   '-----BEGIN EC PRIVATE KEY-----' in content
        except Exception as e:
            print_warning(f"Error reading PEM file {pem_file}: {e}")
            return False
    
    def check_dependencies(self) -> bool:
        """Check if required tools are installed."""
        if self.platform == "Linux":
            # Check for certutil and pk12util
            # Try multiple ways to find them
            tools_found = {'certutil': False, 'pk12util': False}
            
            # Method 1: Try direct execution - just check if command exists and produces output
            for tool in ['certutil', 'pk12util']:
                # Try running the tool - it will show usage/help even with non-zero exit code
                try:
                    result = subprocess.run(
                        [tool],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        timeout=5,
                        text=True
                    )
                    # Check if we got any output (usage/help means tool exists)
                    output = result.stdout or ''
                    if output and len(output.strip()) > 0:
                        # Verify it's actually the right tool by checking for key words
                        output_lower = output.lower()
                        if tool in output_lower or 'usage' in output_lower or 'nss' in output_lower:
                            tools_found[tool] = True
                            print_success(f"Found {tool}")
                            continue
                except FileNotFoundError:
                    # Tool not in PATH - try absolute path
                    for path in ['/usr/bin/certutil', '/usr/bin/pk12util']:
                        if Path(path).name == tool and Path(path).exists():
                            try:
                                result = subprocess.run(
                                    [path],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    timeout=5,
                                    text=True
                                )
                                output = result.stdout or ''
                                if output and len(output.strip()) > 0:
                                    output_lower = output.lower()
                                    if tool in output_lower or 'usage' in output_lower or 'nss' in output_lower:
                                        tools_found[tool] = True
                                        print_success(f"Found {tool} at {path}")
                                        break
                            except Exception:
                                pass
                except subprocess.TimeoutExpired:
                    pass
                except Exception as e:
                    # Other errors - might still mean tool exists
                    pass
            
            # Method 2: Try to find in common locations
            if not tools_found['certutil'] or not tools_found['pk12util']:
                common_paths = [
                    '/usr/bin/certutil',
                    '/usr/bin/pk12util',
                    '/usr/local/bin/certutil',
                    '/usr/local/bin/pk12util',
                ]
                for path in common_paths:
                    tool_name = Path(path).name
                    if Path(path).exists() and tool_name in tools_found:
                        try:
                            result = subprocess.run(
                                [path, '--version'],
                                capture_output=True,
                                timeout=5,
                                stderr=subprocess.DEVNULL
                            )
                            if result.returncode in [0, 1]:
                                tools_found[tool_name] = True
                                print_success(f"Found {tool_name} at {path}")
                        except Exception:
                            pass
            
            # Check if both tools are found
            if tools_found['certutil'] and tools_found['pk12util']:
                return True
            else:
                missing = [tool for tool, found in tools_found.items() if not found]
                print_error(f"Required tools not found: {', '.join(missing)}")
                print_info("Install with: sudo apt-get install libnss3-tools (Ubuntu/Debian)")
                print_info("Or: sudo dnf install nss-tools (Fedora/RHEL)")
                print_info("After installation, you may need to log out and log back in, or restart your terminal")
                return False
        elif self.platform == "Windows":
            # Windows has certutil built-in
            return True
        elif self.platform == "Darwin":  # macOS
            # macOS has security command built-in
            return True
        return True
    
    def create_nss_database(self) -> bool:
        """Create NSS database if it doesn't exist."""
        if self.platform != "Linux":
            return True
        
        if self.nss_db_path.exists():
            print_success(f"NSS database already exists: {self.nss_db_path}")
            return True
        
        print_info(f"Creating NSS database at {self.nss_db_path}...")
        self.nss_db_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            result = subprocess.run(
                ['certutil', '-d', f'sql:{self.nss_db_path}', '-N', '--empty-password'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print_success("NSS database created successfully")
                return True
            else:
                print_error(f"Failed to create NSS database: {result.stderr}")
                return False
        except Exception as e:
            print_error(f"Error creating NSS database: {e}")
            return False
    
    def install_p12_certificate(self, cert_file: Path, password: Optional[str] = None) -> bool:
        """Install PKCS#12 certificate to NSS database."""
        if self.platform != "Linux":
            print_warning(f"PKCS#12 installation for {self.platform} not yet implemented")
            print_info("Please install certificate manually for this platform")
            return False
        
        print_info(f"Installing certificate: {cert_file.name}")
        
        # Check if password is needed
        if password is None:
            # Try without password first
            result = subprocess.run(
                ['pk12util', '-d', f'sql:{self.nss_db_path}', '-i', str(cert_file)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print_success("Certificate installed successfully (no password required)")
                return True
            
            # If it failed, might need password
            if 'password' in result.stderr.lower() or 'incorrect password' in result.stderr.lower():
                print_info("Certificate requires a password")
                password = getpass.getpass("Enter certificate password: ")
            else:
                print_error(f"Failed to install certificate: {result.stderr}")
                return False
        
        # Install with password
        try:
            # Use stdin to provide password
            process = subprocess.Popen(
                ['pk12util', '-d', f'sql:{self.nss_db_path}', '-i', str(cert_file)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(input=password + '\n', timeout=30)
            
            if process.returncode == 0:
                print_success("Certificate installed successfully")
                return True
            else:
                print_error(f"Failed to install certificate: {stderr}")
                if 'incorrect password' in stderr.lower():
                    print_error("Incorrect password provided")
                return False
        except subprocess.TimeoutExpired:
            print_error("Certificate installation timed out")
            return False
        except Exception as e:
            print_error(f"Error installing certificate: {e}")
            return False
    
    def convert_pem_to_p12(self, pem_file: Path, password: Optional[str] = None) -> Optional[Path]:
        """Convert PEM file to PKCS#12 format."""
        print_info(f"Converting PEM file to PKCS#12: {pem_file.name}")
        
        # Check if openssl is available
        try:
            subprocess.run(['openssl', 'version'], 
                         capture_output=True, check=True, timeout=5)
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            print_error("openssl not found. Cannot convert PEM to PKCS#12.")
            print_info("Install with: sudo apt-get install openssl (Ubuntu/Debian)")
            return None
        
        # Generate output filename
        p12_file = pem_file.parent / f"{pem_file.stem}.p12"
        
        # Prompt for password if not provided
        if password is None:
            password = getpass.getpass("Enter password for PKCS#12 file (or press Enter for no password): ")
            if not password:
                password = None
        
        try:
            # Extract certificate and key from PEM
            # This assumes the PEM file has both certificate and private key
            cmd = [
                'openssl', 'pkcs12', '-export',
                '-out', str(p12_file),
                '-in', str(pem_file),
                '-name', 'novamobilidade',
                '-nodes'  # Don't encrypt private key in output
            ]
            
            if password:
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = process.communicate(input=password + '\n' + password + '\n', timeout=30)
            else:
                process = subprocess.Popen(
                    cmd + ['-passout', 'pass:'],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = process.communicate(timeout=30)
            
            if process.returncode == 0 and p12_file.exists():
                print_success(f"Converted to PKCS#12: {p12_file.name}")
                return p12_file
            else:
                print_error(f"Conversion failed: {stderr}")
                return None
        except Exception as e:
            print_error(f"Error converting PEM to PKCS#12: {e}")
            return None
    
    def list_installed_certificates(self) -> List[str]:
        """List certificates installed in NSS database."""
        if self.platform != "Linux" or not self.nss_db_path.exists():
            return []
        
        try:
            result = subprocess.run(
                ['certutil', '-d', f'sql:{self.nss_db_path}', '-L'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Parse certificate names from output
                lines = result.stdout.strip().split('\n')
                certs = []
                for line in lines[2:]:  # Skip header lines
                    if line.strip():
                        parts = line.split()
                        if len(parts) > 0:
                            certs.append(parts[0])
                return certs
        except Exception as e:
            print_warning(f"Error listing certificates: {e}")
        
        return []
    
    def install_certificate(self, cert_file: Path) -> bool:
        """Install a certificate file."""
        print_header(f"Installing Certificate: {cert_file.name}")
        
        # Check file exists
        if not cert_file.exists():
            print_error(f"Certificate file not found: {cert_file}")
            return False
        
        # Handle different file types
        if cert_file.suffix.lower() in ['.p12', '.pfx']:
            # Try to install directly
            password = None
            # Check if password might be needed
            print_info("Attempting to install PKCS#12 certificate...")
            return self.install_p12_certificate(cert_file, password)
        
        elif cert_file.suffix.lower() == '.pem':
            # Convert PEM to P12 first
            print_info("PEM file detected. Converting to PKCS#12 format...")
            p12_file = self.convert_pem_to_p12(cert_file)
            if p12_file:
                return self.install_p12_certificate(p12_file)
            else:
                return False
        
        else:
            print_error(f"Unsupported certificate format: {cert_file.suffix}")
            print_info("Supported formats: .p12, .pfx, .pem (with private key)")
            return False


def main():
    """Main installation script."""
    print_header("Certificate Installation Script")
    
    # Determine cert directory
    script_dir = Path(__file__).parent
    cert_dir = script_dir / 'cert'
    
    print_info(f"Certificate directory: {cert_dir}")
    
    installer = CertificateInstaller(cert_dir)
    
    # Check dependencies
    print_header("Checking Dependencies")
    if not installer.check_dependencies():
        print_error("Required dependencies not found. Please install them and try again.")
        sys.exit(1)
    print_success("All dependencies found")
    
    # Find certificate files
    print_header("Searching for Certificate Files")
    cert_files = installer.find_certificate_files()
    
    if not cert_files:
        print_error("No compatible certificate files found in ./cert directory")
        print_info("Looking for: .p12, .pfx, or .pem files (with private key)")
        print_info(f"Checked directory: {cert_dir}")
        sys.exit(1)
    
    print_success(f"Found {len(cert_files)} compatible certificate file(s):")
    for i, cert_file in enumerate(cert_files, 1):
        print(f"  {i}. {cert_file.name}")
    
    # Select certificate to install
    if len(cert_files) == 1:
        selected_file = cert_files[0]
        print_info(f"Auto-selecting: {selected_file.name}")
    else:
        print("\nSelect certificate to install:")
        for i, cert_file in enumerate(cert_files, 1):
            print(f"  {i}. {cert_file.name}")
        
        while True:
            try:
                choice = input(f"\nEnter number (1-{len(cert_files)}): ").strip()
                idx = int(choice) - 1
                if 0 <= idx < len(cert_files):
                    selected_file = cert_files[idx]
                    break
                else:
                    print_error("Invalid choice")
            except ValueError:
                print_error("Please enter a valid number")
            except KeyboardInterrupt:
                print("\n\nInstallation cancelled")
                sys.exit(0)
    
    # Create NSS database if needed (Linux)
    if installer.platform == "Linux":
        print_header("Preparing Certificate Store")
        if not installer.create_nss_database():
            print_error("Failed to create NSS database")
            sys.exit(1)
    
    # Install certificate
    print_header("Installing Certificate")
    success = installer.install_certificate(selected_file)
    
    if success:
        print_header("Installation Complete")
        print_success("Certificate installed successfully!")
        
        # List installed certificates
        if installer.platform == "Linux":
            print_info("Installed certificates in NSS database:")
            installed = installer.list_installed_certificates()
            if installed:
                for cert in installed:
                    print(f"  - {cert}")
            else:
                print("  (No certificates found)")
        
        print("\nNext steps:")
        print("  1. Restart your browser if it's running")
        print("  2. Run the automation script again")
        print("  3. The certificate should now be automatically selected")
    else:
        print_header("Installation Failed")
        print_error("Certificate installation failed")
        print_info("Please check the error messages above and try again")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

