# 🔒 HTTPS Setup for MakerMatrix

This guide provides multiple options for enabling HTTPS in MakerMatrix, which is required for DigiKey OAuth and improves overall security.

## 🎯 Quick Start (Recommended)

### Option 1: Self-Signed Certificate (Simplest)
```bash
# Generate self-signed certificate and configure app
python scripts/setup_https.py

# Start with HTTPS
./start_https.sh
```
**Access**: https://localhost:8443 (accept browser warning)

### Option 2: mkcert (No Browser Warnings)
```bash
# Install mkcert first (if not installed)
# macOS: brew install mkcert
# Linux: sudo apt install mkcert
# Windows: choco install mkcert

# Generate trusted certificate
python scripts/setup_https.py --method mkcert

# Start with HTTPS
./start_https.sh
```
**Access**: https://localhost:8443 (no warnings!)

## 📋 Detailed Options

### Certificate Methods

| Method | Pros | Cons | Best For |
|--------|------|------|----------|
| **Self-Signed** | ✅ Quick setup<br>✅ Works offline<br>✅ No extra tools | ❌ Browser warnings<br>❌ Need to accept each time | Development, testing |
| **mkcert** | ✅ Trusted by browser<br>✅ No warnings<br>✅ Easy to use | ❌ Requires installation<br>❌ Local machine only | Local development |
| **Let's Encrypt** | ✅ Real certificates<br>✅ Public trust | ❌ Requires public domain<br>❌ Complex setup | Production |

### Advanced Usage

```bash
# Custom domain and port
python scripts/setup_https.py --domain myapp.local --https-port 9443

# Multiple domains
python scripts/setup_https.py --additional-domains 127.0.0.1 myapp.local

# Skip app modification (manual setup)
python scripts/setup_https.py --skip-app-update
```

## 🔧 Manual Configuration

### 1. Update DigiKey OAuth URL
In your DigiKey developer app settings:
- **Redirect URI**: `https://localhost:8443/digikey_callback`

### 2. Environment Variables
Add to your `.env` file:
```bash
HTTPS_ENABLED=true
SSL_CERT_PATH=certs/cert.pem
SSL_KEY_PATH=certs/key.pem
HTTPS_PORT=8443
```

### 3. Start Application
```bash
# With HTTPS
HTTPS_ENABLED=true python -m MakerMatrix.main

# Or use the generated script
./start_https.sh
```

## 🌐 URL Updates

After enabling HTTPS, update all references:

| Service | HTTP URL | HTTPS URL |
|---------|----------|-----------|
| **Main App** | http://localhost:8080 | https://localhost:8443 |
| **API Docs** | http://localhost:8080/docs | https://localhost:8443/docs |
| **DigiKey OAuth** | http://localhost:8080/digikey_callback | https://localhost:8443/digikey_callback |
| **Frontend Dev** | http://localhost:5173 | Keep HTTP (proxy to HTTPS) |

## 🛠️ Troubleshooting

### Certificate Issues
```bash
# Regenerate certificates
rm -rf certs/
python scripts/setup_https.py

# Check certificate details
openssl x509 -in certs/cert.pem -text -noout
```

### Browser Issues
- **Chrome**: Type `thisisunsafe` on warning page
- **Firefox**: Click "Advanced" → "Accept Risk"
- **Safari**: Click "Show Details" → "visit this website"

### Port Conflicts
```bash
# Check what's using the port
lsof -i :8443
netstat -tulpn | grep 8443

# Use different port
python scripts/setup_https.py --https-port 9443
```

### CORS Issues
Update your `.env`:
```bash
CORS_ORIGINS=https://localhost:8443,https://127.0.0.1:8443,http://localhost:5173
```

## 🔄 Switching Between HTTP/HTTPS

### Enable HTTPS
```bash
export HTTPS_ENABLED=true
python -m MakerMatrix.main
```

### Disable HTTPS (back to HTTP)
```bash
unset HTTPS_ENABLED
# OR
export HTTPS_ENABLED=false
python -m MakerMatrix.main
```

## 🏗️ Production Considerations

For production deployment:

1. **Use real certificates** (Let's Encrypt, commercial CA)
2. **Configure reverse proxy** (nginx, Apache)
3. **Set proper security headers**
4. **Use standard HTTPS port** (443)
5. **Configure auto-renewal**

### Production Example (nginx)
```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 📚 Resources

- [mkcert Documentation](https://github.com/FiloSottile/mkcert)
- [Let's Encrypt](https://letsencrypt.org/)
- [FastAPI HTTPS Documentation](https://fastapi.tiangolo.com/deployment/https/)
- [DigiKey OAuth Documentation](https://developer.digikey.com/documentation/oauth)