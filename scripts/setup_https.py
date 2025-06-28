#!/usr/bin/env python3
"""
HTTPS Setup Script for MakerMatrix
Comprehensive HTTPS setup for the entire MakerMatrix application
Supports multiple options: self-signed, mkcert, and production certificates
"""

import os
import subprocess
import sys
import shutil
from pathlib import Path
import argparse

class HTTPSSetup:
    def __init__(self):
        self.cert_dir = Path("certs")
        self.cert_dir.mkdir(exist_ok=True)
    
    def check_dependencies(self):
        """Check if required tools are available"""
        deps = {
            'openssl': self._check_openssl(),
            'mkcert': self._check_mkcert()
        }
        return deps
    
    def _check_openssl(self):
        try:
            result = subprocess.run(["openssl", "version"], capture_output=True, text=True)
            return result.returncode == 0, result.stdout.strip()
        except FileNotFoundError:
            return False, "Not installed"
    
    def _check_mkcert(self):
        try:
            result = subprocess.run(["mkcert", "-version"], capture_output=True, text=True)
            return result.returncode == 0, result.stdout.strip()
        except FileNotFoundError:
            return False, "Not installed"
    
    def create_self_signed_cert(self, domain="localhost", additional_domains=None):
        """Create self-signed certificate for development"""
        print(f"🔑 Creating self-signed certificate for {domain}...")
        
        cert_file = self.cert_dir / "cert.pem"
        key_file = self.cert_dir / "key.pem"
        config_file = self.cert_dir / "openssl.conf"
        
        # Create OpenSSL config with Subject Alternative Names
        domains = [domain] + (additional_domains or [])
        san_entries = [f"DNS:{d}" for d in domains]
        
        config_content = f"""[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = US
ST = Development
L = Local
O = MakerMatrix
CN = {domain}

[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names

[alt_names]
{chr(10).join([f'DNS.{i+1} = {entry.replace("DNS:", "")}' for i, entry in enumerate(san_entries)])}
"""
        
        with open(config_file, "w") as f:
            f.write(config_content)
        
        # Generate private key
        subprocess.run([
            "openssl", "genrsa", "-out", str(key_file), "2048"
        ], check=True)
        
        # Generate certificate
        subprocess.run([
            "openssl", "req", "-new", "-x509", "-key", str(key_file),
            "-out", str(cert_file), "-days", "365", 
            "-config", str(config_file), "-extensions", "v3_req"
        ], check=True)
        
        # Set secure permissions
        os.chmod(key_file, 0o600)
        os.chmod(cert_file, 0o644)
        
        print(f"✅ Self-signed certificate created for domains: {', '.join(domains)}")
        return cert_file, key_file
    
    def create_mkcert_cert(self, domain="localhost", additional_domains=None):
        """Create locally trusted certificate using mkcert"""
        print(f"🔐 Creating mkcert certificate for {domain}...")
        
        cert_file = self.cert_dir / "cert.pem"
        key_file = self.cert_dir / "key.pem"
        
        domains = [domain] + (additional_domains or [])
        
        # Install CA if not already done
        subprocess.run(["mkcert", "-install"], check=True)
        
        # Generate certificate
        subprocess.run([
            "mkcert", "-cert-file", str(cert_file), "-key-file", str(key_file)
        ] + domains, check=True)
        
        print(f"✅ mkcert certificate created for domains: {', '.join(domains)}")
        return cert_file, key_file
    
    def update_main_app(self, cert_file, key_file, https_port=8443):
        """Update main.py to support HTTPS"""
        main_file = Path("MakerMatrix/main.py")
        
        # Read current main.py
        with open(main_file, "r") as f:
            content = f.read()
        
        # Check if HTTPS code already exists
        if "ssl_keyfile" in content:
            print("⚠️  HTTPS code already exists in main.py")
            return
        
        # Add HTTPS support
        https_code = f'''
# HTTPS Configuration
import ssl

def run_with_https():
    """Run the application with HTTPS support"""
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain("{cert_file}", "{key_file}")
    
    uvicorn.run(
        "MakerMatrix.main:app",
        host="0.0.0.0",
        port={https_port},
        ssl_keyfile="{key_file}",
        ssl_certfile="{cert_file}",
        reload=False  # Disable reload for HTTPS
    )

if __name__ == "__main__":
    import os
    if os.getenv("HTTPS_ENABLED", "false").lower() == "true":
        print(f"🔒 Starting MakerMatrix with HTTPS on port {https_port}")
        run_with_https()
    else:
        print("🌐 Starting MakerMatrix with HTTP on port 8080")
        uvicorn.run("MakerMatrix.main:app", host="0.0.0.0", port=8080, reload=True)
'''
        
        # Add the HTTPS code before the existing uvicorn.run line
        if 'if __name__ == "__main__":' not in content:
            content += https_code
        else:
            # Replace existing main block
            lines = content.split('\n')
            new_lines = []
            skip_main = False
            
            for line in lines:
                if 'if __name__ == "__main__":' in line:
                    skip_main = True
                    new_lines.append(line)
                    new_lines.extend(https_code.split('\n')[1:])  # Skip first empty line
                    break
                else:
                    new_lines.append(line)
            
            content = '\n'.join(new_lines)
        
        # Write updated main.py
        with open(main_file, "w") as f:
            f.write(content)
        
        print(f"✅ Updated {main_file} with HTTPS support")
    
    def create_env_config(self, cert_file, key_file, https_port=8443, http_port=8080):
        """Create environment configuration for HTTPS"""
        env_content = f"""
# HTTPS Configuration for MakerMatrix
HTTPS_ENABLED=true
SSL_CERT_PATH={cert_file}
SSL_KEY_PATH={key_file}
HTTPS_PORT={https_port}

# HTTP Configuration
HTTP_PORT={http_port}
HTTP_REDIRECT_TO_HTTPS=true

# CORS Origins (update for HTTPS)
CORS_ORIGINS=https://localhost:{https_port},https://127.0.0.1:{https_port},http://localhost:{http_port}

# DigiKey OAuth Callback (HTTPS)
DIGIKEY_OAUTH_CALLBACK=https://localhost:{https_port}/digikey_callback
"""
        
        env_path = Path(".env.https")
        with open(env_path, "w") as f:
            f.write(env_content.strip())
        
        return env_path
    
    def create_startup_script(self, https_port=8443):
        """Create startup script for HTTPS"""
        script_content = f'''#!/bin/bash
# MakerMatrix HTTPS Startup Script

echo "🚀 Starting MakerMatrix with HTTPS..."

# Activate virtual environment
if [ -f "venv_test/bin/activate" ]; then
    source venv_test/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ Virtual environment not found at venv_test/bin/activate"
    exit 1
fi

# Set HTTPS environment
export HTTPS_ENABLED=true

# Start the application
python -m MakerMatrix.main

echo "🔒 MakerMatrix is running at https://localhost:{https_port}"
echo "📝 API documentation: https://localhost:{https_port}/docs"
'''
        
        script_path = Path("start_https.sh")
        with open(script_path, "w") as f:
            f.write(script_content)
        
        os.chmod(script_path, 0o755)
        return script_path

def main():
    parser = argparse.ArgumentParser(description="Setup HTTPS for MakerMatrix")
    parser.add_argument("--method", choices=["self-signed", "mkcert"], default="self-signed",
                        help="Certificate generation method")
    parser.add_argument("--domain", default="localhost", help="Primary domain")
    parser.add_argument("--additional-domains", nargs="*", help="Additional domains")
    parser.add_argument("--https-port", type=int, default=8443, help="HTTPS port")
    parser.add_argument("--skip-app-update", action="store_true", help="Skip updating main.py")
    
    args = parser.parse_args()
    
    print("🔒 MakerMatrix HTTPS Setup")
    print("=" * 40)
    
    setup = HTTPSSetup()
    
    # Check dependencies
    deps = setup.check_dependencies()
    print("📋 Checking dependencies...")
    for tool, (available, version) in deps.items():
        status = "✅" if available else "❌"
        print(f"   {status} {tool}: {version}")
    
    # Generate certificate based on method
    if args.method == "mkcert":
        if not deps['mkcert'][0]:
            print("\n❌ mkcert not found. Install with:")
            print("   - macOS: brew install mkcert")
            print("   - Linux: sudo apt install mkcert (or download from GitHub)")
            print("   - Windows: choco install mkcert")
            sys.exit(1)
        
        cert_file, key_file = setup.create_mkcert_cert(args.domain, args.additional_domains)
    else:
        if not deps['openssl'][0]:
            print("\n❌ OpenSSL not found. Please install OpenSSL first.")
            sys.exit(1)
        
        cert_file, key_file = setup.create_self_signed_cert(args.domain, args.additional_domains)
    
    # Update application
    if not args.skip_app_update:
        setup.update_main_app(cert_file, key_file, args.https_port)
    
    # Create configuration files
    env_file = setup.create_env_config(cert_file, key_file, args.https_port)
    startup_script = setup.create_startup_script(args.https_port)
    
    print(f"\n🎉 HTTPS Setup Complete!")
    print("=" * 40)
    print(f"📜 Certificate: {cert_file}")
    print(f"🔑 Private Key: {key_file}")
    print(f"⚙️  Configuration: {env_file}")
    print(f"🚀 Startup Script: {startup_script}")
    print(f"")
    print(f"🔗 URLs:")
    print(f"   - Main App: https://{args.domain}:{args.https_port}")
    print(f"   - API Docs: https://{args.domain}:{args.https_port}/docs")
    print(f"   - DigiKey OAuth: https://{args.domain}:{args.https_port}/digikey_callback")
    print(f"")
    print(f"🚀 Start the application:")
    print(f"   ./start_https.sh")
    print(f"   # OR")
    print(f"   HTTPS_ENABLED=true python -m MakerMatrix.main")
    
    if args.method == "self-signed":
        print(f"")
        print(f"⚠️  Browser Security Warning:")
        print(f"   - Your browser will show a security warning")
        print(f"   - Click 'Advanced' → 'Proceed to {args.domain} (unsafe)'")
        print(f"   - This is safe for local development")
    else:
        print(f"")
        print(f"✅ mkcert certificates are trusted by your system")
        print(f"   - No browser warnings will appear")

if __name__ == "__main__":
    main()