# HTTPS Setup Guide

MakerMatrix supports HTTPS for secure local development and production deployments.

## Quick Setup

```bash
# 1. Enable HTTPS in your environment
echo "HTTPS_ENABLED=true" >> .env

# 2. Generate certificates
python scripts/setup_https.py

# 3. Restart the server
python dev_manager.py
```

Access at: **https://localhost:8443**

## Certificate Generation Options

The `setup_https.py` script offers three methods:

### Option 1: Self-Signed Certificate (Development)

Generates a self-signed certificate using OpenSSL. Your browser will show a security warning that you can bypass.

```bash
python scripts/setup_https.py
# Choose option 1 when prompted
```

### Option 2: mkcert (Recommended for Development)

Uses [mkcert](https://github.com/FiloSottile/mkcert) to generate locally-trusted certificates — no browser warnings.

```bash
# Install mkcert first
# macOS: brew install mkcert
# Windows: choco install mkcert
# Linux: see https://github.com/FiloSottile/mkcert#installation

mkcert -install  # Install local CA (one-time)

python scripts/setup_https.py
# Choose option 2 when prompted
```

### Option 3: Production Certificates

For production, use certificates from a trusted CA (Let's Encrypt, etc.):

1. Place your certificate files in the `certs/` directory:
   - `certs/cert.pem` — Certificate file
   - `certs/key.pem` — Private key file
2. Set `HTTPS_ENABLED=true` in `.env`
3. Start the server

## File Locations

Certificates are stored in the `certs/` directory (gitignored):

```
certs/
  cert.pem    # Certificate
  key.pem     # Private key
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `HTTPS_ENABLED` | `false` | Enable HTTPS mode |

## Docker HTTPS

When using Docker, mount your certificates:

```bash
docker run -d \
  -p 8080:8080 \
  -v makermatrix-data:/data \
  -v ./certs:/data/certs \
  -e HTTPS_ENABLED=true \
  ghcr.io/ril3y/makermatrix:latest
```

## Troubleshooting

### Browser shows "Not Secure"

Self-signed certificates will always trigger browser warnings. Use mkcert (Option 2) for warning-free local development.

### Certificate permission errors

Ensure certificate files have restrictive permissions:

```bash
chmod 600 certs/key.pem
chmod 644 certs/cert.pem
```

### Port already in use

HTTPS mode uses port 8443 by default. Check for conflicts:

```bash
lsof -i :8443  # Linux/macOS
netstat -ano | findstr :8443  # Windows
```
