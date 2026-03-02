# Configuration Guide

MakerMatrix is configured via environment variables, typically set in a `.env` file. Copy `.env.example` to `.env` and customize as needed.

## Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./makermatrix.db` | Database connection string |
| `DEBUG` | `False` | Enable debug mode |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `SERVER_HOST` | `localhost` | Server bind host |

## Security

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET_KEY` | (generated) | **Required for production.** Secret key for JWT tokens |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | Access token lifetime (8 hours) |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |
| `MAKERMATRIX_ENCRYPTION_KEY` | (none) | Encryption key for secure credential storage |

> **Important**: Always set a strong `JWT_SECRET_KEY` in production. The default auto-generated key changes on each restart, invalidating all sessions.

## HTTPS / SSL

| Variable | Default | Description |
|----------|---------|-------------|
| `HTTPS_ENABLED` | `false` | Enable HTTPS mode |

When enabled, MakerMatrix expects certificates in the `certs/` directory. See [HTTPS Setup Guide](../scripts/HTTPS_SETUP.md) for certificate generation.

## Supplier API Keys

All supplier keys are optional. Without them, enrichment for that supplier is disabled.

| Variable | Description |
|----------|-------------|
| `DIGIKEY_CLIENT_ID` | DigiKey API client ID |
| `DIGIKEY_CLIENT_SECRET` | DigiKey API client secret |
| `DIGIKEY_CLIENT_SANDBOX` | Use DigiKey sandbox (default: false) |
| `MOUSER_API_KEY` | Mouser API key |
| `LCSC_API_KEY` | LCSC API key (LCSC also works without a key) |

Suppliers without API keys (Adafruit, Seeed Studio, McMaster-Carr, Bolt Depot) use web scraping with Playwright.

## AI Integration (Optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OPENAI_API_KEY` | (none) | OpenAI API key for AI features |
| `ANTHROPIC_API_KEY` | (none) | Anthropic API key for AI features |

## CORS

| Variable | Default | Description |
|----------|---------|-------------|
| `CORS_ORIGINS` | `http://localhost:5173,...` | Allowed CORS origins (comma-separated) |

## Docker-Specific

When running in Docker, these paths are automatically configured:

| Variable | Docker Default | Description |
|----------|---------------|-------------|
| `DATABASE_URL` | `sqlite:////data/database/makermatrix.db` | Database path |
| `STATIC_FILES_PATH` | `/data/static` | Uploaded files |
| `BACKUPS_PATH` | `/data/backups` | Backup archives |

## Default Credentials

On first startup, MakerMatrix creates a default admin account:

- **Username**: `admin`
- **Password**: `Admin123!`

Change these immediately after first login via Settings > User Management.

## API Keys

MakerMatrix supports API key authentication for programmatic access. Generate keys via Settings > API Keys in the web interface, or use the `/api/api-keys/` endpoint. Each key can be scoped with specific permissions.
