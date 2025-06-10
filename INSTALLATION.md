# MakerMatrix Installation Guide

## Table of Contents
- [Quick Start](#quick-start)
- [System Requirements](#system-requirements)
- [Basic Installation](#basic-installation)
- [Optional Features Setup](#optional-features-setup)
- [AI Assistant Setup](#ai-assistant-setup)
- [Printer Configuration](#printer-configuration)
- [Development Setup](#development-setup)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### Basic Installation
```bash
# Clone the repository
git clone https://github.com/your-repo/MakerMatrix.git
cd MakerMatrix

# Install Python dependencies
pip install -r requirements.txt

# Run the application
python -m MakerMatrix.main
```

**Application URL:** `http://localhost:57891`  
**Default Login:** `admin` / `Admin123!`

---

## System Requirements

### Minimum Requirements
- **Python:** 3.10 or higher
- **RAM:** 512MB minimum, 1GB recommended
- **Storage:** 100MB for application, additional space for database
- **OS:** Windows, macOS, Linux

### Recommended for Full Features
- **Python:** 3.11+
- **RAM:** 2GB+ (for AI features)
- **Storage:** 500MB+ (for AI models)
- **Network:** Internet connection for AI APIs and part data enrichment

---

## Basic Installation

### 1. Clone and Setup
```bash
git clone https://github.com/your-repo/MakerMatrix.git
cd MakerMatrix

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. First Run
```bash
python -m MakerMatrix.main
```

The application will:
- Create SQLite database automatically
- Set up default user roles (Admin, Manager, User)
- Create default admin account
- Start web server on port 57891

### 3. Access the Application
- **Web Interface:** `http://localhost:57891`
- **API Documentation:** `http://localhost:57891/docs`
- **Default Login:** `admin` / `Admin123!`

**⚠️ Important:** Change the default password on first login!

---

## Optional Features Setup

### Database Configuration
By default, MakerMatrix uses SQLite. For production, you can use PostgreSQL:

```bash
# Set environment variable
export DATABASE_URL="postgresql://user:password@localhost/makermatrix"

# Or create .env file
echo "DATABASE_URL=postgresql://user:password@localhost/makermatrix" > .env
```

### Security Configuration
```bash
# Generate a secure secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Set environment variable
export SECRET_KEY="your-generated-secret-key"

# Or add to .env file
echo "SECRET_KEY=your-generated-secret-key" >> .env
```

---

## AI Assistant Setup

The AI assistant is **completely optional** and can be enabled/disabled anytime through the Settings page.

### Option 1: Local AI with Ollama (Recommended)

#### Install Ollama
```bash
# Linux/macOS
curl -fsSL https://ollama.ai/install.sh | sh

# Windows - Download from https://ollama.ai
```

#### Install AI Model
```bash
# Install Llama 3.2 (recommended)
ollama pull llama3.2

# Or other models
ollama pull llama3.1
ollama pull codellama
ollama pull mistral
```

#### Enable in MakerMatrix
1. Go to **Settings → AI Assistant**
2. Enable AI: **ON**
3. Provider: **Ollama**
4. API URL: `http://localhost:11434`
5. Model: `llama3.2`
6. Click **Test Connection**
7. **Save Configuration**

### Option 2: OpenAI API

#### Get API Key
1. Visit [OpenAI API Keys](https://platform.openai.com/api-keys)
2. Create new API key
3. Copy the key

#### Configure in MakerMatrix
1. Go to **Settings → AI Assistant**
2. Enable AI: **ON**
3. Provider: **OpenAI**
4. API URL: `https://api.openai.com/v1`
5. API Key: `your-openai-api-key`
6. Model: `gpt-4` or `gpt-3.5-turbo`
7. Click **Test Connection**
8. **Save Configuration**

### Option 3: Anthropic Claude

#### Get API Key
1. Visit [Anthropic Console](https://console.anthropic.com/)
2. Create new API key
3. Copy the key

#### Configure in MakerMatrix
1. Go to **Settings → AI Assistant**
2. Enable AI: **ON**
3. Provider: **Anthropic**
4. API URL: `https://api.anthropic.com/v1`
5. API Key: `your-anthropic-api-key`
6. Model: `claude-3-sonnet-20240229`
7. Click **Test Connection**
8. **Save Configuration**

### AI Features
Once configured, the AI assistant can:
- **Query your database directly** for real-time inventory data
- **Answer questions** about parts, locations, and stock levels
- **Provide recommendations** for parts and organization
- **Generate reports** and analysis
- **Help with inventory optimization**

Example queries:
- "What resistors do I have in stock?"
- "Show me parts that are running low"
- "Where is the Arduino Uno located?"
- "What's in the Electronics category?"

---

## Printer Configuration

MakerMatrix supports **Brother QL** label printers for printing part labels with QR codes.

### Supported Printers
- Brother QL-800
- Brother QL-810W
- Brother QL-820NWB
- Brother QL-1100
- Brother QL-1110NWB

### Setup Process

#### 1. Install Brother QL Library
```bash
pip install brother_ql
```

#### 2. Connect Printer
- **USB:** Connect printer via USB cable
- **Network:** Connect printer to your network and note IP address

#### 3. Configure in MakerMatrix
1. Go to **Settings → Printer Configuration**
2. Configure settings:
   - **Model:** QL-800 (or your model)
   - **Backend:** `network` or `pyusb`
   - **Identifier:** 
     - Network: `tcp://192.168.1.100` (printer IP)
     - USB: `usb://0x04f9:0x209b` (auto-detected)
   - **DPI:** 300 (recommended)
   - **Scaling:** 1.1 (adjust as needed)
3. Click **Test Connection**
4. **Save Configuration**

#### 4. Test Label Printing
1. Go to **Parts** page
2. Select any part
3. Click **Print Label**
4. Label should print with QR code and part information

### Troubleshooting Printer Issues
```bash
# Find connected printers
brother_ql discover

# Test print directly
brother_ql -m QL-800 print -l 62 test.png
```

---

## Development Setup

### Frontend Development
```bash
cd MakerMatrix/frontend

# Install Node.js dependencies
npm install

# Development server (with hot reload)
npm run dev

# Build for production
npm run build
```

### Backend Development
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run with auto-reload
uvicorn MakerMatrix.main:app --reload --port 57891
```

### API Development
- **Interactive API Docs:** `http://localhost:57891/docs`
- **Alternative Docs:** `http://localhost:57891/redoc`

---

## Troubleshooting

### Common Issues

#### Application Won't Start
```bash
# Check Python version
python --version  # Should be 3.10+

# Check dependencies
pip check

# Run with verbose output
python -m MakerMatrix.main --log-level DEBUG
```

#### Database Issues
```bash
# Delete and recreate database
rm makers_matrix.db
python -m MakerMatrix.main
```

#### AI Connection Issues
```bash
# Test Ollama
curl http://localhost:11434/api/tags

# Check model is installed
ollama list

# Pull model if missing
ollama pull llama3.2
```

#### Printer Issues
```bash
# Check printer connection
brother_ql discover

# Test printer directly
brother_ql -m QL-800 -b network -p tcp://192.168.1.100 print -l 62 test.png
```

### Port Conflicts
If port 57891 is in use:
```bash
# Change port
python -m MakerMatrix.main --port 8080
```

### Performance Issues
- **Database:** Consider PostgreSQL for large inventories
- **AI:** Use local Ollama instead of API services for faster responses
- **Memory:** Ensure adequate RAM for AI models

### Getting Help
1. Check the [GitHub Issues](https://github.com/your-repo/MakerMatrix/issues)
2. Review application logs
3. Test with minimal configuration
4. Check network connectivity for external services

---

## Production Deployment

### Using Docker (Coming Soon)
```bash
docker build -t makermatrix .
docker run -p 57891:57891 makermatrix
```

### Using Systemd (Linux)
```ini
# /etc/systemd/system/makermatrix.service
[Unit]
Description=MakerMatrix Inventory Management
After=network.target

[Service]
Type=simple
User=makermatrix
WorkingDirectory=/opt/makermatrix
ExecStart=/opt/makermatrix/venv/bin/python -m MakerMatrix.main
Restart=always

[Install]
WantedBy=multi-user.target
```

### Reverse Proxy (Nginx)
```nginx
server {
    listen 80;
    server_name inventory.yourdomain.com;
    
    location / {
        proxy_pass http://localhost:57891;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Next Steps

After installation:
1. **Change default password**
2. **Set up your locations** (warehouse, shelves, bins)
3. **Create categories** for your parts
4. **Add your first parts**
5. **Configure AI assistant** (optional)
6. **Set up label printer** (optional)
7. **Create additional users** if needed

Enjoy using MakerMatrix for your inventory management! 🎉