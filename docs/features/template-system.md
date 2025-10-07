# 🏷️ Label Template System Documentation

The MakerMatrix Label Template System provides a flexible, user-friendly way to design and manage label templates for printing.

## 📚 Documentation

**[Template System User Guide →](TEMPLATE_USER_GUIDE.md)**

Complete guide for users including:
- Where to find template features
- How to create and edit templates
- How to use templates for printing
- Pre-designed system templates
- Troubleshooting common issues
- Template variables reference
- Best practices

## 🎯 Quick Start

1. Navigate to the Templates page (`/templates`)
2. Browse pre-designed system templates or create your own
3. Customize text, QR codes, and layout
4. Use templates when printing labels for parts

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
- **API reference**: See [API Documentation](../../api.md)

---

**The Enhanced Label Template System is ready for production use! 🎉**
