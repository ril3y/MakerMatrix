# MakerMatrix - Electronic Parts Inventory Management System

MakerMatrix is a comprehensive electronic parts inventory management system built with FastAPI backend and React frontend. It provides full CRUD operations for parts, locations, and categories, with advanced features like supplier integration, task management, and real-time updates.

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+ and npm
- SQLite (default) or PostgreSQL/MySQL

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository_url>
   cd MakerMatrix
   ```

2. **Set up Python environment:**
   ```bash
   python3 -m venv venv_test
   source venv_test/bin/activate  # On Linux/macOS
   # or venv_test\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

3. **Set up frontend dependencies:**
   ```bash
   cd MakerMatrix/frontend
   npm install
   cd ../..
   ```

### Development with Rich TUI Manager

**Use the development manager for the best development experience:**

```bash
python dev_manager.py
```

The development manager provides a comprehensive Rich TUI (Terminal User Interface) for all development tasks:

#### 🚀 **Core Features**
- **Rich TUI interface** for managing both backend and frontend simultaneously
- **Auto-restart functionality** with intelligent file watching (5-second debounce)
- **Real-time log monitoring** with color-coded output and filtering
- **HTTPS/HTTP mode switching** with automatic certificate management
- **Process management** and automatic port conflict resolution
- **Health monitoring** with service status indicators

#### 🎮 **Interactive Controls**

**Keyboard Shortcuts:**
- `r` - Restart backend server
- `f` - Restart frontend server
- `b` - Restart both servers
- `h` - Toggle HTTPS/HTTP mode
- `l` - Toggle log filtering
- `c` - Clear log display
- `s` - Show system status
- `q` - Quit development manager

#### 📊 **Real-time Monitoring**

The development manager displays:
```
┌─ MakerMatrix Development Manager ─────────────────────────────┐
│ Backend:  ✅ Running (PID: 12345) - http://localhost:8080    │
│ Frontend: ✅ Running (PID: 12346) - http://localhost:5173    │
│ Mode:     🔒 HTTPS Enabled                                   │
│ Logs:     📝 Auto-scroll ON | Filter: ALL                   │
└───────────────────────────────────────────────────────────────┘
```

#### 🔍 **Debugging Features**

**Log Analysis:**
- **Color-coded logs** for different severity levels (INFO, WARN, ERROR)
- **Service separation** - Backend and frontend logs clearly distinguished
- **Real-time filtering** - Focus on specific log levels or services
- **Automatic error highlighting** with stack trace formatting
- **Search functionality** within log history

**Health Monitoring:**
- **Port conflict detection** and automatic resolution
- **Process health checks** with automatic restart on crashes
- **Memory and CPU usage monitoring** for both services
- **Database connection status** indicators
- **External service connectivity** (supplier APIs, etc.)

#### 🛠️ **Advanced Options**

**Command Line Arguments:**
```bash
# Start with specific configuration
python dev_manager.py --https          # Force HTTPS mode
python dev_manager.py --http           # Force HTTP mode
python dev_manager.py --no-frontend    # Backend only
python dev_manager.py --no-backend     # Frontend only
python dev_manager.py --verbose        # Extra debug logging
python dev_manager.py --port 8081      # Custom backend port
```

**Environment Integration:**
- **Automatic .env loading** and validation
- **Environment variable display** for debugging
- **Configuration file monitoring** with automatic reloads
- **SSL certificate management** and renewal

#### 🐛 **Debugging Workflow**

1. **Start Development Manager:**
   ```bash
   python dev_manager.py
   ```

2. **Monitor Startup Logs** - Watch for any initialization errors

3. **Test Connections** - Both services will show health indicators

4. **Real-time Issue Detection:**
   - SSL/certificate issues highlighted in red
   - Database connection problems clearly marked
   - API failures with detailed error context
   - Port conflicts automatically resolved

5. **Interactive Debugging:**
   - Use `r` to restart backend after code changes
   - Use `f` to restart frontend after dependency updates
   - Use `l` to filter logs by severity level
   - Use `c` to clear logs for focused debugging

#### 📁 **File Watching**

The development manager monitors:
- **Backend Python files** (`MakerMatrix/` directory)
- **Frontend source files** (`frontend/src/` directory)
- **Configuration files** (`.env`, `*.json`, `*.toml`)
- **Template files** and static assets

**Smart Restart Logic:**
- **Backend changes** → Restart backend only
- **Frontend changes** → Restart frontend only
- **Config changes** → Restart both services
- **Database schema changes** → Full application restart

#### 🚨 **Troubleshooting**

**Common Issues and Solutions:**

| Issue | Solution in Dev Manager |
|-------|------------------------|
| Port already in use | Automatic port conflict resolution |
| SSL certificate errors | Press `h` to toggle HTTPS mode |
| Frontend build failures | Press `f` to restart with clean cache |
| Database connection issues | Check logs for detailed connection status |
| Module import errors | Use `b` to restart both services |
| Memory leaks | Built-in memory monitoring with warnings |

**Debug Commands:**
```bash
# Check current status
python dev_manager.py --status

# Validate configuration
python dev_manager.py --check-config

# Test SSL setup
python dev_manager.py --test-ssl

# Clear all cached data
python dev_manager.py --clean
```

### Manual Development Setup

**Backend (Alternative):**
```bash
source venv_test/bin/activate
python -m MakerMatrix.main
```

**Frontend (Alternative):**
```bash
cd MakerMatrix/frontend
npm run dev
```

### Access Points

- **Frontend**: https://localhost:5173 (development)
- **Backend API**: http://localhost:8080
- **API Documentation**: http://localhost:8080/docs (Swagger UI)
- **OpenAPI Schema**: http://localhost:8080/openapi.json

## 🔐 Authentication

### Default Admin User

The system creates a default admin user on first startup:
- **Username**: `admin`
- **Password**: `Admin123!`

**Change this password after first login!**

### API Authentication

The API uses JWT authentication. Include the token in requests:
```
Authorization: Bearer <your_jwt_token>
```

#### Authentication Endpoints

- `POST /api/auth/login` - Web login (form-based)
- `POST /api/auth/mobile-login` - JSON login for APIs/mobile
- `POST /api/auth/refresh` - Refresh expired tokens
- `POST /api/auth/logout` - Logout/invalidate token

#### Example Login
```bash
curl -X POST http://localhost:8080/api/auth/mobile-login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "Admin123!"}'
```

## 🏗️ Architecture

### Core Features

- **Parts Management**: Full CRUD with search, categorization, and location tracking
- **Location Hierarchy**: Multi-level storage organization with parent-child relationships
- **Category System**: Flexible part categorization with counts and associations
- **Task System**: Background processing for long-running operations
- **Supplier Integration**: Automated part enrichment from multiple suppliers
- **File Import**: CSV/XLS import from supplier order files
- **Real-time Updates**: WebSocket integration for live updates
- **Analytics**: Comprehensive reporting and data visualization

### Technology Stack

**Backend:**
- FastAPI with async/await
- SQLAlchemy with SQLite/PostgreSQL
- JWT authentication with role-based access control
- Background task processing
- WebSocket support
- Comprehensive API documentation

**Frontend:**
- React 18 with TypeScript
- Vite for development and building
- Modern responsive UI with real-time updates
- WebSocket integration
- Chart.js for analytics visualization

### Database

- **Auto-creation**: Database and tables created automatically on first run
- **Default data**: Includes default roles, admin user, and sample locations
- **Migrations**: Automatic schema updates
- **Backup system**: Task-based backup with full data export

## 📊 Supplier Integration

MakerMatrix integrates with multiple electronic component suppliers for automated part enrichment, order file imports, and real-time pricing/stock data.

### Supported Suppliers

| Supplier | Capabilities | Authentication | Status |
|----------|-------------|----------------|--------|
| **LCSC Electronics** | Part details, pricing, datasheets, order import | API Key | ✅ Active |
| **DigiKey** | Part enrichment, pricing, stock, OAuth flow | OAuth2 Client ID/Secret | ✅ Active |
| **Mouser Electronics** | Order file import, part enrichment, search | API Key | ✅ Active |
| **McMaster-Carr** | Industrial parts, client certificates | Username/Password + Cert | 🔧 Planned |
| **Bolt Depot** | Fasteners and hardware | API Key | 🔧 Planned |

### How Suppliers Work

1. **Credential Storage**: All supplier credentials are stored as environment variables in `.env` file for security
2. **Automatic Loading**: Credentials are loaded automatically on application startup
3. **Fallback System**: The system includes fallback loading for standalone scripts and edge cases
4. **Configuration Management**: Each supplier has a database configuration with capabilities and settings
5. **Connection Testing**: Built-in connection testing validates credentials and API accessibility

### Credential Configuration

Add supplier credentials to your `.env` file:

```bash
# DigiKey OAuth2 (Production)
DIGIKEY_CLIENT_ID=your_client_id_here
DIGIKEY_CLIENT_SECRET=your_client_secret_here
DIGIKEY_CLIENT_SANDBOX=False

# Mouser Electronics
MOUSER_API_KEY=your_mouser_api_key_here

# LCSC Electronics
LCSC_API_KEY=your_lcsc_api_key_here

# McMaster-Carr (Requires Approved Customer Status)
MCMASTER_CARR_USERNAME=your_username_here
MCMASTER_CARR_PASSWORD=your_password_here
MCMASTER_CARR_CLIENT_CERT_PATH=path/to/client-cert.p12
MCMASTER_CARR_CLIENT_CERT_PASSWORD=cert_password_here
```

### Getting API Keys

**DigiKey:**
1. Register at [DigiKey Developer Portal](https://developer.digikey.com/)
2. Create a production application
3. Get Client ID and Client Secret
4. Uses OAuth2 with automatic token management

**Mouser:**
1. Sign up at [Mouser API Portal](https://www.mouser.com/api-signup/)
2. Request API access from Mouser support
3. Receive API key via email
4. Rate limits: 30 calls/minute, 1000 calls/day

**LCSC:**
1. Contact LCSC support for API access
2. Provide business details and use case
3. Receive API key after approval

### Supplier Management UI

Access supplier configuration through the web interface:

1. Navigate to **Settings** → **Suppliers**
2. View all configured suppliers and their status
3. Test connections and view credential requirements
4. Enable/disable specific suppliers
5. View capabilities and rate limits

### File Import System

Import parts from supplier order files with automatic enrichment:

```bash
# Import with enrichment
curl -X POST http://localhost:8080/api/import/file \
  -H "Authorization: Bearer <token>" \
  -F "supplier_name=mouser" \
  -F "file=@mouser_order.csv" \
  -F "enable_enrichment=true" \
  -F "enrichment_capabilities=get_part_details,fetch_datasheet"
```

**Supported File Formats:**
- **CSV**: LCSC, DigiKey, and generic CSV formats
- **XLS/XLSX**: Mouser Electronics order files
- **Auto-detection**: System automatically detects supplier format

**Enrichment Capabilities:**
- `get_part_details` - Complete part information, images, specifications
- `fetch_datasheet` - Datasheet URL retrieval and download
- `fetch_pricing_stock` - Real-time pricing and stock information

### API Integration

**Test Supplier Connection:**
```bash
curl -X GET http://localhost:8080/api/suppliers/mouser/credentials/status \
  -H "Authorization: Bearer <token>"
```

**Get Supplier Capabilities:**
```bash
curl -X GET http://localhost:8080/api/tasks/capabilities/suppliers/mouser \
  -H "Authorization: Bearer <token>"
```

**Create Enrichment Task:**
```bash
curl -X POST http://localhost:8080/api/tasks/quick/part_enrichment \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "part_id": "uuid-here",
    "supplier": "mouser",
    "capabilities": ["get_part_details", "fetch_datasheet"]
  }'
```

## 🔧 Task Management

Background tasks handle long-running operations:

### Quick Task Creation

```bash
# Enrich a part with supplier data
POST /api/tasks/quick/part_enrichment

# Fetch datasheet for a part
POST /api/tasks/quick/datasheet_fetch

# Bulk enrich multiple parts
POST /api/tasks/quick/bulk_enrichment

# Create database backup
POST /api/tasks/quick/database_backup
```

### Task Monitoring

- **WebSocket**: Real-time task updates via `/ws/tasks`
- **REST API**: Query task status via `/api/tasks/`
- **Dashboard**: Built-in task monitoring in the web interface

## 🧪 Testing

### Backend Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=MakerMatrix

# Run specific test categories
pytest -m integration          # Integration tests
pytest -m "not integration"    # Unit tests only
```

### Frontend Testing
```bash
cd MakerMatrix/frontend

# Unit tests
npm test

# E2E tests with Playwright
npm run test:e2e

# All test suites
npm run test:ci
```

## 🔧 Configuration

### Environment Files
- `.env` - Main configuration
- `.env.https` - HTTPS-specific settings

### Key Configuration Options

```bash
# Database
DATABASE_URL=sqlite:///makermatrix.db

# Server
PORT=8080
HOST=0.0.0.0

# Security
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Development
DEBUG=true
LOG_LEVEL=INFO
```

### HTTPS Setup

For production or DigiKey OAuth integration:

```bash
# Quick setup with self-signed certificates
python scripts/setup_https.py

# Better setup with mkcert (no browser warnings)
python scripts/setup_https.py --method mkcert
```

## 📚 API Documentation

### Core Endpoints

**Parts Management:**
- `GET /api/parts/get_all_parts` - List all parts with pagination
- `POST /api/parts/add_part` - Create new part
- `PUT /api/parts/update_part/{part_id}` - Update part
- `DELETE /api/parts/delete_part` - Delete part
- `POST /api/parts/search` - Advanced search with filters

**Locations:**
- `GET /api/locations/get_all_locations` - List all locations
- `POST /api/locations/add_location` - Create location
- `PUT /api/locations/update_location/{location_id}` - Update location

**Categories:**
- `GET /api/categories/get_all_categories` - List all categories
- `POST /api/categories/add_category` - Create category

**Full API documentation available at `/docs` when running the server.**

## 🔄 WebSocket Endpoints

- `/ws/general` - General application updates
- `/ws/tasks` - Task progress and completion notifications
- `/ws/admin` - Administrative monitoring (admin only)

## 📁 Project Structure

```
MakerMatrix/
├── dev_manager.py              # Rich TUI development manager
├── CLAUDE.md                   # Claude Code instructions
├── api.md                      # Complete API documentation
├── MakerMatrix/
│   ├── main.py                 # FastAPI application entry point
│   ├── models/                 # SQLAlchemy database models
│   ├── repositories/           # Data access layer
│   ├── services/               # Business logic layer
│   ├── routers/                # FastAPI route handlers
│   ├── suppliers/              # Supplier integration
│   ├── tasks/                  # Background task handlers
│   ├── frontend/               # React frontend application
│   └── scripts/                # Utility scripts
├── scripts/                    # Development and setup scripts
└── venv_test/                  # Python virtual environment
```

## 🤝 Contributing

1. **Follow the architecture patterns**: Use repositories for data access, services for business logic
2. **Use the development manager**: `python dev_manager.py` for consistent development experience
3. **Update documentation**: Keep `CLAUDE.md` and `api.md` current with code changes
4. **Test thoroughly**: Both unit and integration tests for new features
5. **Follow security practices**: Never commit secrets, use proper authentication

## 📄 License

This project is for electronic parts inventory management. See the project documentation for more details.

## 🔗 Additional Documentation

- **[CLAUDE.md](CLAUDE.md)** - Comprehensive development guide and instructions
- **[api.md](api.md)** - Complete API reference documentation
- **[scripts/HTTPS_SETUP.md](scripts/HTTPS_SETUP.md)** - HTTPS configuration guide
- **[suppliers.md](suppliers.md)** - Current supplier integration status
- **[project_status.md](project_status.md)** - Recent project milestones and updates