# Docker Deployment

MakerMatrix provides Docker images via GitHub Container Registry for easy deployment.

## Quick Start

### Pull from GitHub Container Registry

```bash
# Latest stable release
docker pull ghcr.io/ril3y/makermatrix:latest

# Specific version
docker pull ghcr.io/ril3y/makermatrix:1.1.1

# Run with persistent data
docker run -d \
  -p 8080:8080 \
  -v makermatrix-data:/data \
  --name makermatrix \
  ghcr.io/ril3y/makermatrix:latest
```

Access at: **http://localhost:8080**

### Interactive Quick Start Script

```bash
curl -sL https://raw.githubusercontent.com/ril3y/MakerMatrix/main/scripts/docker-run.sh | bash
```

This interactive script helps you:
- Choose a version (latest, main, or specific tag)
- Configure a JWT secret key
- Set up supplier API keys (optional)
- Create persistent data volumes

## Docker Compose

```bash
git clone https://github.com/ril3y/MakerMatrix.git
cd MakerMatrix
cp .env.example .env
# Edit .env with your settings
docker-compose up -d
```

### docker-compose.yml

The compose file configures:
- **Port**: 8080 (host) → 8080 (container)
- **Volume**: `./data:/data` for persistent storage
- **Environment**: Loaded from `.env` file
- **Network**: Isolated `makermatrix-network`

## Available Tags

| Tag | Description |
|-----|-------------|
| `latest` | Latest stable release from version tags or main |
| `main` | Latest development build from main branch |
| `1.1.1`, `1.1`, `1` | Semantic version tags |
| `sha-abc1234` | Commit-specific builds (main branch only) |

## Container Details

### Build

Multi-stage Docker build:
1. **Stage 1**: Node 18 Alpine — builds the React frontend with Vite
2. **Stage 2**: Python 3.12 slim — runs the FastAPI backend and serves the built frontend

### Runtime

- **User**: `makermatrix` (non-root, UID 1000)
- **Port**: 8080
- **Health check**: `GET /api/utility/get_counts` every 30s

### Data Paths

All persistent data is stored under `/data`:

| Path | Contents |
|------|----------|
| `/data/database` | SQLite database |
| `/data/backups` | Encrypted backup archives |
| `/data/static` | Uploaded images and datasheets |
| `/data/certs` | SSL/TLS certificates (HTTPS mode) |

## Environment Variables

Key variables to set (see [Configuration Guide](docs/CONFIGURATION.md) for full list):

```bash
# Required for production
JWT_SECRET_KEY=your-secure-random-key

# Database (default: SQLite in /data)
DATABASE_URL=sqlite:////data/database/makermatrix.db

# Supplier APIs (optional)
DIGIKEY_CLIENT_ID=your-client-id
DIGIKEY_CLIENT_SECRET=your-client-secret
MOUSER_API_KEY=your-api-key
```

## Default Credentials

- **Username**: `admin`
- **Password**: `Admin123!`
- Change immediately after first login!

## Building Locally

```bash
docker build -t makermatrix:latest .
docker run -d -p 8080:8080 -v makermatrix-data:/data makermatrix:latest
```

## Updating

```bash
docker pull ghcr.io/ril3y/makermatrix:latest
docker stop makermatrix
docker rm makermatrix
docker run -d \
  -p 8080:8080 \
  -v makermatrix-data:/data \
  --name makermatrix \
  ghcr.io/ril3y/makermatrix:latest
```

Your data is preserved in the named volume `makermatrix-data`.
