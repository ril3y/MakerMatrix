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

The development manager provides:
- **Rich TUI interface** for managing both backend and frontend
- **Auto-restart functionality** with file watching
- **Real-time log monitoring** and health checks
- **HTTPS/HTTP mode switching**
- **Process management** and port conflict resolution

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

MakerMatrix integrates with multiple electronic component suppliers:

### Supported Suppliers

- **LCSC Electronics**: Part enrichment, pricing, datasheets
- **DigiKey**: Part details, pricing, stock information
- **Mouser Electronics**: Order file import, part enrichment
- **McMaster-Carr**: Industrial parts integration
- **Bolt Depot**: Fasteners and hardware

### Configuration

Add supplier credentials to your `.env` file:

```bash
# DigiKey
DIGIKEY_CLIENT_ID=your_client_id
DIGIKEY_CLIENT_SECRET=your_client_secret

# Mouser
MOUSER_API_KEY=your_api_key

# LCSC
LCSC_API_KEY=your_api_key

# McMaster-Carr (requires approval)
MCMASTER_CARR_USERNAME=your_username
MCMASTER_CARR_PASSWORD=your_password
```

### File Import

Import parts from supplier order files:

```bash
# Via API
curl -X POST http://localhost:8080/api/import/file \
  -H "Authorization: Bearer <token>" \
  -F "supplier_name=lcsc" \
  -F "file=@order.csv" \
  -F "enable_enrichment=true"
```

Supported formats:
- **CSV**: LCSC, DigiKey, and other CSV formats
- **XLS**: Mouser Electronics order files

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