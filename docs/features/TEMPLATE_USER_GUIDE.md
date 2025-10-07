# 🏷️ Enhanced Label Template System - User Guide

## 📍 **Where to Find Template Features**

### **Method 1: Templates Page (Main Interface)**

1. **Open the application**: Navigate to `https://localhost:5173`
2. **Login**: Use your credentials
3. **Look at the LEFT SIDEBAR** - You should see these menu items in order:
   - 🏠 Dashboard
   - 🔌 Parts
   - 📍 Locations
   - 🏷️ Categories
   - **📄 Templates** ← **CLICK HERE!**
   - 📈 Analytics
   - ⚡ Tasks
   - ⚙️ Settings

4. **Click "Templates"** in the sidebar
5. **You'll see**:
   - "Create Template" button (top right)
   - Filter buttons: All Templates / System / My Templates
   - Grid of template cards showing all available templates

### **Method 2: Direct URL**

Simply navigate directly to: `https://localhost:5173/templates`

### **Method 3: From Print Dialog**

1. Go to **Parts** page
2. Click on any part
3. Click **Print Label** button
4. In the print dialog, you'll see a **Template Selector** dropdown
5. This shows all available templates for quick selection

---

## 🎨 **How to Create a Template**

### **Step-by-Step Template Creation**

1. **Navigate to Templates page** (see above)

2. **Click "Create Template"** button (blue, top right corner)

3. **Fill in the form**:

   **Basic Information**:
   - **Template Name**: `my_12mm_label` (unique ID, no spaces)
   - **Display Name**: `My 12mm Label` (what users see)
   - **Description**: `Custom 12mm label for small components`
   - **Category**: Choose from dropdown (COMPONENT, LOCATION, etc.)

   **Label Size**:
   - **Width**: `39.0` mm
   - **Height**: `12.0` mm
   - (Common: 12mm = 12×39mm, 29mm = 29×90mm, 62mm = 62×100mm)

   **Text Configuration**:
   - **Text Template**:
     ```
     {part_name}
     {part_number}
     ```
   - Use `\n` for line breaks
   - Available variables: `{part_name}`, `{part_number}`, `{location}`, `{category}`, `{quantity}`, `{description}`
   - **Text Rotation**: Select 0°, 90°, 180°, or 270°
   - **Text Alignment**: Left, Center, or Right
   - **Enable multi-line**: ✓ (checked)
   - **Auto-size text**: ✓ (checked)

   **QR Code**:
   - **Include QR Code**: ✓ (checked)
   - **QR Position**: Left, Right, Top, Bottom, Center, or Corners
   - **QR Scale**: 0.95 (95% of available space)

4. **Click "Create Template"**

5. **Done!** Your template is saved and ready to use

---

## ✏️ **How to Edit a Template**

1. Navigate to **Templates page**
2. Find your custom template (user templates, not system templates)
3. Click **"Edit"** button on the template card
4. Modify any settings
5. Click **"Update Template"**

---

## 📋 **How to Use a Template for Printing**

### **Option A: From Print Dialog**

1. Go to **Parts** → Click a part → **Print Label**
2. In the print dialog, you'll see **Template Selector** dropdown
3. Click the dropdown to see:
   - **💡 Suggested for your part** (smart recommendations)
   - **⭐ System Templates** (7 pre-designed)
   - **👤 My Templates** (your custom templates)
4. Select a template
5. Click **Preview** to see how it looks
6. Click **Print Label** to print

### **Option B: Use Custom Template**

1. In the print dialog, select **"Custom Template"** from dropdown
2. Enter your own text with variables manually
3. Configure QR code and options
4. Preview and print

---

## 🎯 **Pre-Designed System Templates**

The system includes 7 ready-to-use templates:

### **1. MakerMatrix 12mm Box Label** ⭐ **← Your 12mm Template!**
- **Size**: 39mm × 12mm
- **Layout**: QR code on left + Part name
- **Best for**: Small bins, drawers, component storage
- **QR Position**: Left
- **Text**: `{part_name}`

### **2. Component Vertical Label**
- **Size**: 12mm × 62mm (tall/narrow)
- **Layout**: 90° rotated text + QR at bottom
- **Best for**: Narrow vertical spaces, tape reels

### **3. Multi-line Location Label**
- **Size**: 62mm × 29mm
- **Layout**: QR on right + 3 lines of text
- **Best for**: Location markers, storage areas

### **4. Inventory Tag Label**
- **Size**: 50mm × 25mm
- **Layout**: QR top-right + Quantity/Description
- **Best for**: Inventory management

### **5. Cable Identification Label**
- **Size**: 102mm × 12mm (long/narrow)
- **Layout**: Horizontal text for cable ends
- **Best for**: Cable labeling, wire identification

### **6. Storage Box Label**
- **Size**: 102mm × 51mm (extra large)
- **Layout**: QR right + Large text area
- **Best for**: Storage containers, large boxes

### **7. Small Parts Label**
- **Size**: 19mm × 6mm (tiny)
- **Layout**: Text only, no QR (too small)
- **Best for**: Very small components

---

## 💡 **Quick Actions**

### **Duplicate a Template**
1. Find any template (system or custom)
2. Click **"Duplicate"** button
3. A copy is created as YOUR custom template
4. Edit the copy to customize it

### **Delete a Template**
1. Find YOUR custom template
2. Click **"Delete"** button
3. Confirm deletion
4. Template is removed

**Note**: System templates cannot be deleted or edited directly. Duplicate them first!

---

## 🐛 **Troubleshooting**

### **"I don't see the Templates link in the sidebar"**

**Solutions**:
1. **Hard refresh the browser**: Press `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)
2. **Clear browser cache**:
   - Chrome: Settings → Privacy → Clear browsing data
   - Firefox: Settings → Privacy → Clear Data
3. **Check you're logged in**: Templates require authentication
4. **Try direct URL**: Go directly to `https://localhost:5173/templates`
5. **Restart frontend**: Backend developer can restart with dev manager API

### **"Templates dropdown is empty in print dialog"**

**Cause**: Not logged in or templates failed to load

**Solutions**:
1. **Ensure you're logged in** with valid credentials
2. **Check browser console** for errors (F12 → Console tab)
3. **Navigate to Templates page** to verify templates exist
4. **Try selecting "Custom Template"** as fallback

### **"Create Template button doesn't work"**

**Solutions**:
1. Ensure you're on the Templates page (`/templates`)
2. Check browser console for JavaScript errors
3. Hard refresh the page
4. Try logging out and back in

### **"Template selector shows no templates"**

This is expected if:
- Not logged in (authentication required)
- No templates created yet
- API connection issue

**Solution**: Use "Custom Template" option to enter text manually

---

## 📊 **Template Variables Reference**

Use these variables in your text templates:

| Variable | Description | Example |
|----------|-------------|---------|
| `{part_name}` | Part name | "Arduino Uno" |
| `{part_number}` | Part/SKU number | "ARD-UNO-R3" |
| `{location}` | Storage location | "Bin A3" |
| `{category}` | Part category | "Microcontrollers" |
| `{quantity}` | Current quantity | "10" |
| `{description}` | Part description | "Dev board 5V" |
| `{manufacturer}` | Manufacturer | "Arduino" |
| `{supplier}` | Supplier name | "DigiKey" |
| `{additional_properties.*}` | Custom fields | Any custom data |

**Example Template**:
```
{part_name}
P/N: {part_number}
Loc: {location}
Qty: {quantity}
```

**Result**:
```
Arduino Uno
P/N: ARD-UNO-R3
Loc: Bin A3
Qty: 10
```

---

## 🎓 **Best Practices**

1. **Start with system templates**: They're professionally designed
2. **Duplicate before customizing**: Safer than creating from scratch
3. **Use descriptive names**: `small_component_with_qr` not `template1`
4. **Test with preview**: Always preview before printing batch
5. **Keep QR codes enabled**: Makes parts scannable with phone
6. **Match template to label size**: Use 12mm templates for 12mm tape
7. **Use multi-line for readability**: Split information across lines
8. **Enable auto-sizing**: Ensures text fits the label

---

## 📞 **Need Help?**

- **View this guide**: `TEMPLATE_USER_GUIDE.md`
- **Technical docs**: `printertodo.md` and `TEMPLATE_SYSTEM_PRODUCTION_READY.md`
- **API reference**: `api.md` (for developers)

---

**The Enhanced Label Template System is ready to use! Happy labeling! 🎉**