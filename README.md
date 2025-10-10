# MakerMatrix

**A powerful, modern electronic parts inventory management system designed for makers, engineers, and electronics enthusiasts.**

MakerMatrix helps you organize your electronic components, track inventory across multiple storage locations, manage projects, and automate part data enrichment from supplier APIs. Built with a modern tech stack (FastAPI + React + TypeScript), it provides a beautiful, responsive interface with real-time updates and powerful search capabilities.

<div align="center">

![Dashboard](docs/screenshots/dashboard.png)
*Modern dashboard with real-time inventory statistics and analytics*

</div>

---

## ✨ Key Features

### 📦 Parts Management
Comprehensive part tracking with rich metadata, automatic supplier enrichment, and advanced search capabilities.

![Part Details](docs/screenshots/part-details.png)
*Detailed part view with specifications, datasheets, images, and multi-location allocation tracking*

**Features:**
- **Rich Part Data**: Part numbers, descriptions, categories, specifications, datasheets, images
- **Multi-Location Allocation**: Track quantity across multiple storage locations with primary storage designation
- **Supplier Integration**: Automatic enrichment from LCSC, DigiKey, Mouser with real-time pricing and stock data
- **Advanced Search**: Field-specific search (name, description, part number) with support for additional properties (`prop:package 0603`)
- **QR Code Support**: Generate and print QR codes for quick part lookup
- **Project Association**: Link parts to projects with hashtag-style organization
- **Price Tracking**: Historical pricing data with analytics and trend visualization
- **Order History**: Complete order tracking with supplier information

### 📍 Location Management
Hierarchical storage organization with visual identification and container slot management.

<div align="center">

![Locations](docs/screenshots/locations.png)
*Tree view of hierarchical storage locations with visual emojis*

![Container Management](docs/screenshots/location-containers.png)
*Advanced container slot management for organized storage*

</div>

**Features:**
- **Hierarchical Organization**: Multi-level location tree (e.g., Workshop → Shelf 1 → Drawer A → Bin 3)
- **Visual Identification**: Custom emojis or images for quick location recognition
- **Container Types**: Standard containers, cassette reels, single-part slots with auto-generation
- **Drag-and-Drop**: Reorganize locations with intuitive drag-and-drop (coming soon)
- **Path Tracking**: Full breadcrumb path from root to leaf locations
- **Deletion Safety**: Preview impact before deleting locations with orphaned part warnings

### 🗂️ Categories & Organization

![Categories](docs/screenshots/categories.png)
*Flexible category system with part counts and quick filtering*

**Features:**
- **Flexible Categorization**: Organize parts by type (resistors, capacitors, ICs, etc.)
- **Part Counts**: Real-time counts of parts in each category
- **Multiple Categories**: Parts can belong to multiple categories
- **Quick Filtering**: One-click category-based part filtering

### 🔬 Projects Management

![Projects](docs/screenshots/projects.png)
*Project tracking with status management and part associations*

**Features:**
- **Project Organization**: Group parts by project with status tracking (Planning, Active, Completed, Archived)
- **Many-to-Many**: Parts can belong to multiple projects
- **Visual Cards**: Project cards with images, descriptions, and custom links
- **Part Tracking**: See all parts associated with each project
- **Inline Assignment**: Add/remove project associations directly from part details

### 🔍 Advanced Search

![Advanced Search](docs/screenshots/advsearch.png)
*Powerful search with field-specific syntax and JSON property searching*

**Search Syntax:**
- `"exact match"` - Find exact phrase (e.g., "5mm" won't match "1.5mm")
- `desc:capacitor` - Search description field only
- `pn:100k` - Search part number only
- `name:resistor` - Search part name only
- `prop:package 0603` - Search additional properties (also: `add:`)
- `resistor` - Search all standard fields

### 👥 User & Access Management

![User Management](docs/screenshots/users.png)
*Role-based access control with comprehensive user management*

**Features:**
- **Role-Based Access Control**: Admin, User, and custom roles
- **Permission System**: Granular permissions for parts, locations, categories, tasks
- **JWT Authentication**: Secure token-based authentication with refresh tokens
- **API Key Management**: Generate and manage API keys for programmatic access
- **Audit Logging**: Track user actions and changes

### 🏷️ Label Printing
Template-based label printing with QR codes for Brother QL printers.

![Label Printer](docs/screenshots/labelprinter.png)
*Template-based label printing with QR code support and real-time preview*

**Features:**
- **7 Pre-designed Templates**: Ready-to-use templates for common scenarios
- **Custom Templates**: Create and save your own label layouts
- **QR Code Generation**: Automatic QR codes with 8 positioning options
- **Variable Substitution**: Dynamic fields (part name, number, location, category, etc.)
- **Text Rotation**: 0°, 90°, 180°, 270° rotation support
- **Real-time Preview**: See your label before printing
- **Brother QL Support**: QL-800, QL-700, QL-570 printers (12mm, 29mm, 62mm, 102mm labels)

### 🔄 Real-Time Updates
WebSocket-based real-time updates keep your interface synchronized.

**Features:**
- **Task Progress**: Live updates during bulk operations and enrichment
- **Inventory Changes**: Real-time quantity updates across all views
- **System Notifications**: Instant alerts for errors and important events
- **Multi-User Support**: Changes from other users appear automatically

### 🤖 Task System
Background processing for long-running operations with progress tracking.

**Task Types:**
- **Part Enrichment**: Fetch details, datasheets, images from supplier APIs
- **Bulk Enrichment**: Process multiple parts in batch
- **File Import**: Import CSV/XLS order files from suppliers
- **Database Backup**: Comprehensive backup with datasheets and images
- **Price Updates**: Refresh pricing data from suppliers

### 📊 Analytics & Reporting
Built-in analytics with charts and data visualization.

**Features:**
- **Inventory Statistics**: Total parts, locations, categories with trends
- **Price Tracking**: Historical price data with line charts
- **Stock Levels**: Low stock alerts and inventory health metrics
- **Usage Patterns**: Most accessed parts and popular categories

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.12+** (with pip)
- **Node.js 18+** (with npm)
- **SQLite** (included) or PostgreSQL/MySQL

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ril3y/MakerMatrix.git
   cd MakerMatrix
   ```

2. **Set up Python environment:**
   ```bash
   python3 -m venv venv_test
   source venv_test/bin/activate  # Linux/macOS
   # or: venv_test\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

3. **Set up frontend:**
   ```bash
   cd MakerMatrix/frontend
   npm install
   cd ../..
   ```

### Development with the Dev Manager

**The easiest way to run MakerMatrix is with the integrated development manager:**

```bash
python dev_manager.py
```

**Features:**
- 🎨 Rich TUI interface for managing backend and frontend
- 🔄 Auto-restart on file changes (5-second debounce)
- 📊 Real-time log monitoring with color-coded output
- 🔒 HTTPS/HTTP mode switching
- 🔍 Process management and health monitoring
- 🌐 REST API on port 8765 for programmatic control

**Keyboard Shortcuts:**
- `r` - Restart backend
- `f` - Restart frontend
- `b` - Restart both
- `h` - Toggle HTTPS/HTTP
- `l` - Toggle log filtering
- `c` - Clear logs
- `q` - Quit

**Dev Manager API:**
```bash
# Check status
curl http://localhost:8765/status

# Restart backend
curl -X POST http://localhost:8765/backend/restart

# Get logs
curl "http://localhost:8765/logs?service=all&limit=100"
```

### Manual Development

**Backend:**
```bash
source venv_test/bin/activate
python -m MakerMatrix.main
```

**Frontend:**
```bash
cd MakerMatrix/frontend
npm run dev
```

### Access the Application

- **Frontend UI**: https://localhost:5173
- **Backend API**: http://localhost:8080
- **API Docs**: http://localhost:8080/docs
- **Dev Manager API**: http://localhost:8765/docs

### Default Credentials

**First-time login:**
- **Username**: `admin`
- **Password**: `Admin123!`

**⚠️ Change this password immediately after first login!**

---

## 🛠️ Technology Stack

### Backend
- **FastAPI** - Modern, fast Python web framework with automatic OpenAPI docs
- **SQLAlchemy** - Powerful ORM with SQLite/PostgreSQL/MySQL support
- **SQLModel** - Combines SQLAlchemy and Pydantic for type-safe database models
- **Pydantic** - Data validation with Python type hints
- **JWT** - Secure authentication with refresh token pattern
- **WebSockets** - Real-time bidirectional communication
- **Async/Await** - High-performance async request handling
- **Background Tasks** - Queue-based task processing with progress tracking

### Frontend
- **React 18** - Modern UI library with hooks and concurrent rendering
- **TypeScript** - Type-safe JavaScript with excellent IDE support
- **Vite** - Lightning-fast build tool and dev server
- **TailwindCSS** - Utility-first CSS framework
- **Chart.js** - Beautiful, responsive charts
- **Framer Motion** - Smooth animations and transitions
- **React Router** - Client-side routing
- **WebSocket Client** - Real-time updates integration

### Database
- **SQLite** (default) - Zero-configuration embedded database
- **PostgreSQL** (optional) - Production-grade relational database
- **MySQL** (optional) - Alternative RDBMS option
- **Auto-migrations** - Automatic schema updates
- **Soft deletes** - Safe data deletion with recovery options

### Development Tools
- **dev_manager.py** - Rich TUI for integrated development
- **pytest** - Backend testing framework
- **Playwright** - Frontend E2E testing
- **ESLint** - JavaScript/TypeScript linting
- **Prettier** - Code formatting

---

## 📊 Supplier Integration

MakerMatrix integrates with major electronics suppliers for automated part enrichment.

### Supported Suppliers

| Supplier | Features | Status |
|----------|----------|--------|
| **LCSC Electronics** | Part details, pricing, datasheets, order import | ✅ Active |
| **DigiKey** | Part enrichment, OAuth2, pricing, stock | ✅ Active |
| **Mouser Electronics** | Order import, part enrichment, search | ✅ Active |
| **Seeed Studio** | Part details, specifications, datasheets | ✅ Active |

### Configuration

Add supplier credentials to `.env`:

```bash
# DigiKey OAuth2
DIGIKEY_CLIENT_ID=your_client_id
DIGIKEY_CLIENT_SECRET=your_secret
DIGIKEY_CLIENT_SANDBOX=False

# Mouser
MOUSER_API_KEY=your_api_key

# LCSC
LCSC_API_KEY=your_api_key
```

### Getting API Keys

**DigiKey:** Register at [DigiKey Developer Portal](https://developer.digikey.com/)
**Mouser:** Request access at [Mouser API Portal](https://www.mouser.com/api-signup/)
**LCSC:** Contact LCSC support for API access

---

## 📁 Project Structure

```
MakerMatrix/
├── dev_manager.py              # Development manager TUI
├── CLAUDE.md                   # Claude Code development guide
├── api.md                      # Complete API documentation
├── MakerMatrix/
│   ├── main.py                 # FastAPI application
│   ├── models/                 # Database models
│   │   ├── part_models.py
│   │   ├── location_models.py
│   │   ├── user_models.py
│   │   └── task_models.py
│   ├── repositories/           # Data access layer
│   ├── services/               # Business logic
│   │   ├── data/              # CRUD services
│   │   ├── system/            # System services
│   │   └── printer/           # Printer integration
│   ├── routers/                # API endpoints
│   ├── suppliers/              # Supplier integrations
│   │   ├── lcsc.py
│   │   ├── digikey.py
│   │   ├── mouser.py
│   │   └── seeed_studio.py
│   ├── tasks/                  # Background tasks
│   ├── frontend/               # React application
│   │   ├── src/
│   │   │   ├── components/    # React components
│   │   │   ├── pages/         # Page components
│   │   │   ├── services/      # API client
│   │   │   └── store/         # State management
│   │   └── public/
│   └── scripts/                # Utility scripts
├── tests/                      # Test suites
│   ├── unit_tests/
│   └── integration_tests/
├── docs/                       # Documentation
│   ├── guides/                # User guides
│   └── screenshots/           # UI screenshots
└── venv_test/                  # Python virtual env
```

---

## 🧪 Testing

### Backend Tests
```bash
# Run all tests
pytest

# With coverage
pytest --cov=MakerMatrix

# Specific categories
pytest -m integration
pytest -m "not integration"
```

### Frontend Tests
```bash
cd MakerMatrix/frontend

# Unit tests
npm test

# E2E tests
npm run test:e2e

# All tests
npm run test:ci
```

---

## 📚 API Documentation

### Authentication
```bash
# Login
POST /api/auth/login
POST /api/auth/mobile-login

# Token management
POST /api/auth/refresh
POST /api/auth/logout
```

### Parts
```bash
# CRUD operations
GET    /api/parts/get_all_parts
POST   /api/parts/add_part
PUT    /api/parts/update_part/{id}
DELETE /api/parts/delete_part

# Search
POST   /api/parts/search
GET    /api/parts/search_text?query=resistor
GET    /api/parts/suggestions?query=res
```

### Locations
```bash
# Hierarchy management
GET    /api/locations/get_all_locations
POST   /api/locations/add_location
PUT    /api/locations/update_location/{id}
DELETE /api/locations/delete_location/{id}

# Navigation
GET    /api/locations/get_location_path/{id}
GET    /api/locations/get_location_details/{id}

# Container slots
POST   /api/locations/generate-container-slots
```

### Part Allocations
```bash
# Multi-location inventory
GET    /api/parts/{id}/allocations
POST   /api/parts/{id}/allocations
POST   /api/parts/{id}/transfer
POST   /api/parts/{id}/allocations/{id}/return_to_primary
```

### Tasks
```bash
# Quick task creation
POST   /api/tasks/quick/part_enrichment
POST   /api/tasks/quick/bulk_enrichment
POST   /api/tasks/quick/database_backup

# Task monitoring
GET    /api/tasks/
GET    /api/tasks/{id}
WS     /ws/tasks?token={jwt}
```

**Full API documentation:** http://localhost:8080/docs

---

## 🔧 Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=sqlite:///makermatrix.db

# Server
PORT=8080
HOST=0.0.0.0

# Security
SECRET_KEY=your-secret-key-change-this
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Development
DEBUG=true
LOG_LEVEL=INFO

# Supplier APIs (optional)
DIGIKEY_CLIENT_ID=
DIGIKEY_CLIENT_SECRET=
MOUSER_API_KEY=
LCSC_API_KEY=
```

### HTTPS Setup

For production or DigiKey OAuth:

```bash
# Quick setup (self-signed)
python scripts/setup_https.py

# Better setup (no browser warnings)
python scripts/setup_https.py --method mkcert
```

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Follow the architecture patterns**:
   - Use repositories for data access
   - Use services for business logic
   - Use routers for API endpoints
4. **Add tests** for new features
5. **Update documentation** (CLAUDE.md, api.md)
6. **Commit changes**: `git commit -m 'Add amazing feature'`
7. **Push to branch**: `git push origin feature/amazing-feature`
8. **Open a Pull Request**

### Development Guidelines

- **Use the dev manager** for consistent development experience
- **Follow TypeScript/Python type hints** for better IDE support
- **Write tests** for all new features
- **Update API docs** when adding endpoints
- **Never commit secrets** to the repository

---

## 📖 Additional Documentation

- **[Developer Guide](docs/guides/Developer.md)** - Technical insights and patterns
- **[API Reference](api.md)** - Complete API documentation
- **[CLAUDE.md](CLAUDE.md)** - Development guide for Claude Code
- **[HTTPS Setup](scripts/HTTPS_SETUP.md)** - SSL/TLS configuration
- **[Supplier Status](suppliers.md)** - Supplier integration details

---

## 📄 License

This project is for electronic parts inventory management. See LICENSE file for details.

---

## 🌟 Star History

If you find MakerMatrix useful, please consider giving it a star! ⭐

---

<div align="center">

**Built with ❤️ for makers and electronics enthusiasts**

[Report Bug](https://github.com/ril3y/MakerMatrix/issues) · [Request Feature](https://github.com/ril3y/MakerMatrix/issues) · [Documentation](https://github.com/ril3y/MakerMatrix/wiki)

</div>
