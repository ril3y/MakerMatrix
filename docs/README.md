# 📚 MakerMatrix Documentation

Welcome to the MakerMatrix documentation! This directory contains all project documentation organized by category.

## 📖 Quick Links

- [Main README](../README.md) - Project overview and getting started
- [API Documentation](../api.md) - Complete API reference
- [Claude Instructions](../CLAUDE.md) - Development guidelines for Claude Code

## 📂 Documentation Structure

### 🎨 Features
User-facing feature documentation and guides.

- **[📄 Label Template System](features/template-system.md)** - ⭐ **Complete template system documentation**
  - [User Guide](features/TEMPLATE_USER_GUIDE.md) - How to use templates
  - [Production Ready](features/TEMPLATE_SYSTEM_PRODUCTION_READY.md) - Technical implementation
  - [Implementation Status](features/TEMPLATE_SYSTEM_STATUS.md) - Development progress
  - [Final Status](features/TEMPLATE_SYSTEM_FINAL_STATUS.md) - Completion report

### 🏗️ Architecture
Technical architecture and design documentation.

- **[Location Refactor](architecture/locationrefactor.md)** - Location hierarchy redesign
- **[Router Report](architecture/router_report.md)** - API router architecture
- **[Printer TODO](architecture/printertodo.md)** - Printer system technical notes

### 📋 Guides
Developer and user guides.

- **[Developer Guide](guides/Developer.md)** - Development workflow and setup
- **[HTTPS Setup Guide](guides/HTTPS_SETUP.md)** - Configure HTTPS for local development
- **[Suppliers Guide](guides/suppliers.md)** - Supplier integration documentation
- **[AI Agents Guide](guides/AGENTS.md)** - AI agent configuration

### 📊 Status Reports
Project status, migrations, and progress tracking.

- **[Project Status](status/project_status.md)** - Overall project progress
- **[User Management Status](status/USER_MANAGEMENT_STATUS.md)** - User system implementation
- **[Allocation Migration Strategy](status/ALLOCATION_MIGRATION_STRATEGY.md)** - Part allocation system migration
- **[Frontend Template Checklist](status/FRONTEND_TEMPLATE_CHECKLIST.md)** - Frontend template completion status
- **[Cleanup Report](status/CLEANUP_REPORT.md)** - Code cleanup initiative

## 🔧 Development Setup

See the [main README](../README.md#development-setup) for development environment setup instructions.

### Quick Commands

```bash
# Run tests
make test

# Run quality checks (linting + dead code analysis)
make quality

# Run dead code analysis
make vulture
```

## 🎯 Key Documentation by Role

### For Users
- [Template System User Guide](features/TEMPLATE_USER_GUIDE.md) - Using label templates
- [Main README](../README.md) - Getting started

### For Developers
- [API Documentation](../api.md) - Complete API reference
- [Claude Instructions](../CLAUDE.md) - Development guidelines
- [Developer Guide](guides/Developer.md) - Development workflow
- [Architecture Docs](architecture/) - System design

### For Contributors
- [Developer Guide](guides/Developer.md) - Contributing guidelines
- [Status Reports](status/) - Current project status
- [API Documentation](../api.md) - API endpoints

## 📝 Documentation Standards

When adding new documentation:

1. **Location**: Choose the appropriate subfolder:
   - `features/` - User-facing features and how-to guides
   - `architecture/` - Technical design and architecture
   - `guides/` - Developer and user guides
   - `status/` - Progress reports and status updates

2. **Format**: Use markdown with clear headings and structure

3. **Linking**: Use relative links to reference other docs

4. **Updates**: Keep documentation up-to-date with code changes

## 🔍 Finding Information

**Can't find what you're looking for?**

1. Search this documentation directory: `grep -r "search term" docs/`
2. Check the [API documentation](../api.md)
3. Review the [main README](../README.md)
4. Look in [CLAUDE.md](../CLAUDE.md) for development guidelines

## 📞 Getting Help

- **Issues**: Open an issue on GitHub
- **Development**: See [CLAUDE.md](../CLAUDE.md) for Claude Code guidelines
- **API Questions**: Reference [api.md](../api.md)

---

**Last Updated**: 2025-10-07
