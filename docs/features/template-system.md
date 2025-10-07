# 🏷️ Label Template System Documentation

The MakerMatrix Label Template System provides a flexible, user-friendly way to design and manage label templates for printing.

## 📚 Documentation Overview

This comprehensive documentation is split into multiple files:

### 👤 For Users

**[Template System User Guide →](TEMPLATE_USER_GUIDE.md)**

Complete guide for end users including:
- Where to find template features
- How to create templates
- How to edit templates
- How to use templates for printing
- Pre-designed system templates
- Troubleshooting common issues
- Template variables reference
- Best practices

### 🔧 For Developers

**[Production Ready Status →](TEMPLATE_SYSTEM_PRODUCTION_READY.md)**

Technical implementation details:
- System architecture
- Database models and schemas
- API endpoints
- Processing engine
- System templates
- Implementation checklist

**[Implementation Status →](TEMPLATE_SYSTEM_STATUS.md)**

Detailed phase-by-phase implementation progress:
- Phase 1: Database & Backend Foundation
- Phase 2: API Endpoints
- Phase 3: Enhanced Processing Engine
- Phase 5: Pre-designed Template Library
- Remaining phases

**[Final Status Report →](TEMPLATE_SYSTEM_FINAL_STATUS.md)**

Summary of accomplishments:
- Major milestones completed
- Quantified results
- Backend implementation status
- Next steps

## 🎯 Quick Start

### For Users
Start with the **[User Guide](TEMPLATE_USER_GUIDE.md)** to learn how to:
1. Navigate to the Templates page
2. Create your first template
3. Print labels using templates

### For Developers
Review the **[Production Ready Status](TEMPLATE_SYSTEM_PRODUCTION_READY.md)** for:
1. System architecture overview
2. API endpoint documentation
3. Database schema details
4. Integration points

## 🏗️ System Overview

The Template System includes:

### Frontend
- Templates management page (`/templates`)
- Template selector in print dialog
- Template creation/editing forms
- Smart template suggestions

### Backend
- 11 REST API endpoints
- Database models with 15+ fields
- Enhanced processing engine
- 7 pre-designed system templates

### Features
- **Text Configuration**: Multi-line, auto-sizing, rotation (0°, 90°, 180°, 270°)
- **QR Codes**: 8 positioning options, scalable
- **Template Categories**: Component, Location, Cable, Storage, General
- **User Templates**: Create custom templates with full control
- **System Templates**: Production-ready templates for common use cases
- **Variable Substitution**: Dynamic content with `{part_name}`, `{quantity}`, etc.

## 📊 Template Variables

All templates support these dynamic variables:

| Variable | Description |
|----------|-------------|
| `{part_name}` | Part name |
| `{part_number}` | Part/SKU number |
| `{location}` | Storage location |
| `{category}` | Part category |
| `{quantity}` | Current quantity |
| `{description}` | Part description |
| `{manufacturer}` | Manufacturer name |
| `{supplier}` | Supplier name |

See the [User Guide](TEMPLATE_USER_GUIDE.md#-template-variables-reference) for complete variable documentation.

## 🎨 Pre-designed Templates

7 system templates included:

1. **MakerMatrix 12mm Box Label** - Small components (39×12mm)
2. **Component Vertical Label** - Narrow spaces (12×62mm)
3. **Multi-line Location Label** - Location markers (62×29mm)
4. **Inventory Tag Label** - Inventory management (50×25mm)
5. **Cable Identification Label** - Cable ends (102×12mm)
6. **Storage Box Label** - Large containers (102×51mm)
7. **Small Parts Label** - Tiny components (19×6mm)

See the [User Guide](TEMPLATE_USER_GUIDE.md#-pre-designed-system-templates) for detailed template descriptions.

## 🔍 API Endpoints

### Template Management
- `GET /api/label_templates` - List all templates
- `POST /api/label_templates` - Create template
- `GET /api/label_templates/{id}` - Get template
- `PUT /api/label_templates/{id}` - Update template
- `DELETE /api/label_templates/{id}` - Delete template

### System Templates
- `GET /api/label_templates/system` - List system templates
- `POST /api/label_templates/{id}/duplicate` - Duplicate template

### Printing
- `POST /api/label_templates/{id}/render` - Render template with data
- `POST /api/label_templates/{id}/preview` - Generate preview
- `GET /api/label_templates/suggest` - Get template suggestions

See the [API Documentation](../../api.md) for complete endpoint details.

## 🚀 Getting Started

1. **Read** the [User Guide](TEMPLATE_USER_GUIDE.md)
2. **Explore** the pre-designed system templates
3. **Create** your first custom template
4. **Print** labels using your templates

## 📞 Need Help?

- **User questions**: See [User Guide](TEMPLATE_USER_GUIDE.md#-troubleshooting)
- **Technical questions**: Review [Production Ready Status](TEMPLATE_SYSTEM_PRODUCTION_READY.md)
- **Implementation details**: Check [Implementation Status](TEMPLATE_SYSTEM_STATUS.md)
- **API reference**: See [API Documentation](../../api.md)

---

**The Enhanced Label Template System is ready for production use! 🎉**
