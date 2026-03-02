# Installation Guide

## Requirements

- **Python** 3.12+
- **Node.js** 18+
- **Git**

## Option 1: Docker (Recommended)

See [Docker Deployment](DOCKER.md) for complete Docker instructions.

```bash
docker pull ghcr.io/ril3y/makermatrix:latest
docker run -d -p 8080:8080 -v makermatrix-data:/data ghcr.io/ril3y/makermatrix:latest
```

Access at: **http://localhost:8080**

## Option 2: Local Development

### 1. Clone the Repository

```bash
git clone https://github.com/ril3y/MakerMatrix.git
cd MakerMatrix
```

### 2. Set Up Python Environment

```bash
python3 -m venv venv_test
source venv_test/bin/activate  # Windows: venv_test\Scripts\activate
pip install -r requirements.txt
```

### 3. Set Up Frontend

```bash
cd MakerMatrix/frontend
npm ci
cd ../..
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env if needed — defaults work for development
# HTTPS_ENABLED=false by default (no certificates required)
```

See [Configuration Guide](CONFIGURATION.md) for all environment variables.

### 5. Start the Development Server

```bash
# Recommended: TUI development manager (manages both backend and frontend)
python dev_manager.py
```

Or start services manually:

```bash
# Terminal 1 — Backend
uvicorn MakerMatrix.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 — Frontend
cd MakerMatrix/frontend && npm run dev
```

### 6. Access the Application

- **HTTP mode** (default): http://localhost:5173
- **HTTPS mode**: https://localhost:8443 (requires certificate setup)

## Default Credentials

- **Username**: `admin`
- **Password**: `Admin123!`
- Change immediately after first login!

## HTTPS Setup (Optional)

To enable HTTPS for local development:

1. Set `HTTPS_ENABLED=true` in `.env`
2. Generate certificates: `python scripts/setup_https.py`
3. Restart the server

See [HTTPS Setup Guide](../scripts/HTTPS_SETUP.md) for details.

## Supplier API Keys (Optional)

To enable automatic part enrichment, configure supplier API keys in `.env`:

- **DigiKey**: Register at [DigiKey API](https://developer.digikey.com/) for `DIGIKEY_CLIENT_ID` and `DIGIKEY_CLIENT_SECRET`
- **Mouser**: Register at [Mouser API](https://www.mouser.com/api-hub/) for `MOUSER_API_KEY`
- **LCSC**: Works without a key; optionally set `LCSC_API_KEY`

Suppliers using web scraping (Adafruit, Seeed Studio) require no configuration.

## Troubleshooting

### Port conflicts

If port 8000 or 5173 is in use, check for other running services:

```bash
# Linux/macOS
lsof -i :8000
lsof -i :5173

# Windows
netstat -ano | findstr :8000
```

### Database reset

To start with a fresh database, delete the SQLite file:

```bash
rm makermatrix.db
# Restart the server — tables and default admin are recreated automatically
```

### Frontend build issues

```bash
cd MakerMatrix/frontend
rm -rf node_modules
npm ci
```
