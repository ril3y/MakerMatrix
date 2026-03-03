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

Suppliers without API keys (Adafruit, Seeed Studio, Bolt Depot) use web scraping to extract part details from product pages.

## McMaster-Carr API Setup

McMaster-Carr uses a private API with **client certificate authentication** (mutual TLS). This is not a public API — you must be approved by McMaster-Carr.

### Step 1: Request API Access

1. Email **eCommerce@mcmaster.com** from your company email
2. Explain your use case (inventory management, automated purchasing, etc.)
3. McMaster-Carr will review and, if approved, provide:
   - A **client certificate** file (`.pfx` or `.p12` format)
   - A **certificate password**
   - API documentation (Postman collection)

> **Note**: Approval is not guaranteed. McMaster-Carr typically approves businesses with established purchasing accounts.

### Step 2: Configure in MakerMatrix

1. Go to **Settings > Suppliers** in the MakerMatrix web UI
2. Find **McMaster-Carr** in the supplier list and click **Configure**
3. Fill in the required fields:

| Field | Description |
|-------|-------------|
| **Client Certificate (.pfx)** | Upload the `.pfx` or `.p12` certificate file provided by McMaster-Carr |
| **Certificate Password** | The password for the certificate file |
| **Username** | Your McMaster-Carr website login username |
| **Password** | Your McMaster-Carr website login password |
| **API Base URL** | `https://api.mcmaster.com` (default, typically no change needed) |

4. Click **Test Connection** to verify your credentials
5. If successful, you'll see "Successfully authenticated with McMaster-Carr API!"

### Step 3: Using McMaster-Carr Enrichment

Once configured, McMaster-Carr enrichment works automatically:

- **When adding a part**: Paste a McMaster-Carr URL (e.g., `https://www.mcmaster.com/92196A077`) into the Supplier URL field. The part number is auto-extracted and part details are fetched.
- **Enriched data includes**: Part name, description, specifications (material, dimensions, threading, etc.), category, product images, and pricing links.
- **Images**: McMaster-Carr API images require authentication, so MakerMatrix downloads them server-side and serves them locally.

### Docker Certificate Mounting

When running in Docker, mount your certificate file into the container:

```yaml
# docker-compose.yml
volumes:
  - ./certs/mcmaster-cert.pfx:/data/certs/mcmaster-cert.pfx:ro
```

Then in the MakerMatrix UI, set the certificate path to `/data/certs/mcmaster-cert.pfx`.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| "Certificate file not found" | Verify the file path and that the certificate is mounted in Docker |
| "Failed to load certificate" | Check that the certificate password is correct |
| "Authentication failed" | Verify your McMaster-Carr website username and password |
| Images not loading | This is normal for first load — MakerMatrix downloads them server-side on enrichment |
| "Rate limit exceeded" | Increase the request delay in supplier configuration |

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
