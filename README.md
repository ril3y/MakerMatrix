# Part Inventory Server

This server provides a RESTful API for managing an inventory of parts.  It allows you to create, read, update, and delete part records.

## Getting Started

### Prerequisites

* Python 3.7+
* A database supported by SQLAlchemy (e.g., PostgreSQL, MySQL, SQLite)

### Installation

1. Clone the repository:

   ```bash
   git clone <repository_url>
   ```

2. Create a virtual environment:

   ```bash
   python3 -m venv .venv
   ```

3. Activate the virtual environment:

   ```bash
   source .venv/bin/activate  # On Linux/macOS
   .venv\Scripts\activate  # On Windows
   ```

4. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Configure the database connection:

   * Create a `.env` file in the root directory of the project.
   * Add the following environment variables, replacing the placeholders with your database credentials:

     ```
     DATABASE_URL=dialect+driver://username:password@host:port/database
     ```

     For example, for a PostgreSQL database:

     ```
     DATABASE_URL=postgresql://user:password@localhost:5432/part_inventory
     ```

     Or for an SQLite database:

     ```
     DATABASE_URL=sqlite:///part_inventory.db
     ```

6. (Optional) Configure supplier API credentials:

   Supplier API keys and credentials can be configured using environment variables. Add them to your `.env` file or set them in your shell environment.

   **Environment Variable Naming Convention:**
   ```
   {SUPPLIER_NAME}_{CREDENTIAL_TYPE}
   ```

   **Supported Suppliers and Credentials:**

   **McMaster-Carr (Official API):**
   ```bash
   MCMASTER_CARR_USERNAME=your_api_username
   MCMASTER_CARR_PASSWORD=your_api_password
   MCMASTER_CARR_CLIENT_CERT_PATH=/path/to/your/certificate.p12
   MCMASTER_CARR_CLIENT_CERT_PASSWORD=certificate_password
   ```
   *Note: McMaster-Carr API access requires approval. Contact eCommerce@mcmaster.com*

   **Mouser Electronics:**
   ```bash
   MOUSER_API_KEY=your_mouser_api_key
   ```

   **DigiKey:**
   ```bash
   DIGIKEY_CLIENT_ID=your_digikey_client_id
   DIGIKEY_CLIENT_SECRET=your_digikey_client_secret
   ```

   **LCSC:**
   ```bash
   LCSC_API_KEY=your_lcsc_api_key
   ```

   If no credentials are provided, suppliers will operate in limited mode (search only, no enrichment).

## Supplier Architecture

MakerMatrix uses a unified supplier abstraction layer that provides consistent interfaces for all supplier integrations. This architecture eliminates code duplication and provides standardized patterns for adding new suppliers.

### Core Components

#### 1. SupplierHTTPClient (`suppliers/http_client.py`)
Unified HTTP client that handles all supplier API communications:

- **Defensive null safety**: Automatically handles `response.json() or {}` patterns
- **Retry logic**: Exponential backoff with configurable retry policies
- **Rate limiting**: Integrated with the rate limiting service
- **Session management**: Automatic connection pooling and cleanup
- **Error handling**: Consistent error patterns across all suppliers

**Usage Example:**
```python
from MakerMatrix.suppliers.http_client import SupplierHTTPClient, RetryConfig

# Create client with supplier-specific configuration
client = SupplierHTTPClient(
    supplier_name="lcsc",
    default_timeout=30,
    retry_config=RetryConfig(max_retries=3, base_delay=1.0)
)

# Make requests with automatic error handling
response = await client.get("https://api.example.com/parts", endpoint_type="search")
if response.success:
    data = response.data  # Already parsed JSON with null safety
```

#### 2. Authentication Framework (`suppliers/auth_framework.py`)
Standardized authentication patterns for all supplier types:

- **OAuth2 client credentials**: Automatic token management and refresh
- **API key authentication**: Simple header-based authentication
- **Bearer token authentication**: JWT and similar token patterns
- **Token lifecycle management**: Automatic expiry handling and refresh

**Usage Example:**
```python
from MakerMatrix.suppliers.auth_framework import AuthenticationManager

# Set up authentication
auth_manager = AuthenticationManager("digikey", http_client)
auth_manager.register_oauth2_client_credentials("https://api.digikey.com/token")

# Authenticate and make requests
result = await auth_manager.authenticate("oauth2_client_credentials", {
    "client_id": "your_client_id",
    "client_secret": "your_client_secret"
})

# Authentication headers are automatically added to requests
headers = auth_manager.get_auth_headers()
```

#### 3. Data Extraction Utilities (`suppliers/data_extraction.py`)
Standardized data parsing and normalization:

- **Safe data access**: Defensive nested dictionary access
- **Pricing extraction**: Standardized pricing break parsing
- **URL validation**: Image and datasheet URL validation
- **Specification parsing**: Consistent specification normalization
- **Type conversion**: Safe type casting with fallbacks

**Usage Example:**
```python
from MakerMatrix.suppliers.data_extraction import DataExtractor

extractor = DataExtractor("lcsc")

# Safe nested data access
price = extractor.safe_get(api_data, ["pricing", "breaks", 0, "price"], 0.0)

# Extract pricing with multiple fallback paths
pricing_result = extractor.extract_pricing(
    api_data, 
    pricing_paths=["pricing.breaks", "price_breaks", "standard_pricing"]
)

# Validate and extract URLs
datasheet_result = extractor.extract_datasheet_url(
    api_data, 
    datasheet_paths=["datasheet.url", "documents.datasheet"]
)
```

### Creating New Suppliers

To add a new supplier, follow these steps:

1. **Create supplier class** inheriting from `BaseSupplier`
2. **Use unified components** (HTTP client, auth, data extraction)
3. **Implement required methods** following the established patterns
4. **Register with the supplier registry**

**Example supplier implementation:**
```python
from .base import BaseSupplier
from .registry import register_supplier
from .http_client import SupplierHTTPClient
from .data_extraction import DataExtractor

@register_supplier("example")
class ExampleSupplier(BaseSupplier):
    def __init__(self):
        super().__init__()
        self._http_client = None
        self._data_extractor = None
    
    def _get_http_client(self) -> SupplierHTTPClient:
        if not self._http_client:
            self._http_client = SupplierHTTPClient(
                supplier_name="example",
                default_timeout=30,
                default_headers={"User-Agent": "MakerMatrix/1.0"}
            )
        return self._http_client
    
    def _get_data_extractor(self) -> DataExtractor:
        if not self._data_extractor:
            self._data_extractor = DataExtractor("example")
        return self._data_extractor
    
    async def get_part_details(self, part_number: str):
        http_client = self._get_http_client()
        extractor = self._get_data_extractor()
        
        # Make API request with unified client
        response = await http_client.get(
            f"https://api.example.com/parts/{part_number}",
            endpoint_type="get_part_details"
        )
        
        if response.success:
            # Extract data with unified utilities
            description = extractor.safe_get(response.data, ["description"], "")
            pricing = extractor.extract_pricing(response.data, ["pricing"])
            
            return PartSearchResult(
                supplier_part_number=part_number,
                description=description,
                pricing=pricing.value if pricing.success else None
            )
        
        return None
```

### Benefits of the Unified Architecture

1. **Code Reduction**: Eliminates 450+ lines of duplicate code per supplier
2. **Consistency**: All suppliers follow the same patterns and behaviors
3. **Maintainability**: Common issues are fixed once in the shared components
4. **Reliability**: Defensive programming patterns prevent common errors
5. **Testability**: Shared components have comprehensive test coverage

### Migration from Legacy Suppliers

Existing suppliers are being migrated to use the unified architecture:

- **LCSC**: ✅ Migrated (reduced from 800+ to 400 lines)
- **DigiKey**: 🔄 In progress  
- **Mouser**: 🔄 Planned

The migration process maintains backward compatibility while providing the benefits of the unified architecture.

### Running the Server

1. Start the server:

   ```bash
   python -m MakerMatrix.main
   ```

   This will start the server on port 57891.

## Authentication

The API uses JWT (JSON Web Token) authentication. Most endpoints require authentication.

### Default Admin User

When the application starts for the first time, a default admin user is created with the following credentials:

- **Username**: admin
- **Password**: Admin123!

You should change this password after the first login.

### Using the Swagger UI

1. Go to the Swagger UI at `http://localhost:57891/docs`
2. Click the "Authorize" button at the top right
3. Enter the admin credentials (or your user credentials)
4. Click "Authorize" to log in
5. Now you can use all the authenticated endpoints

### Authentication Endpoints

- **POST /auth/login**: Log in with username and password to get an access token (form-based, used by Swagger UI)
- **POST /auth/mobile-login**: Log in with username and password to get an access token (JSON-based, ideal for mobile apps)
- **POST /auth/refresh**: Refresh an expired access token
- **POST /auth/logout**: Log out (invalidate the current token)
- **POST /users/register**: Register a new user (admin only)

### Mobile Application Integration

For mobile applications (like an iPhone app), use the `/auth/mobile-login` endpoint:

```json
POST /auth/mobile-login
Content-Type: application/json

{
  "username": "admin",
  "password": "Admin123!"
}
```

Response:

```json
{
  "status": "success",
  "message": "Login successful",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
}
```

Then use the token in subsequent requests:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Role-Based Access Control

The API uses role-based access control with the following default roles:

- **admin**: Full access to all endpoints
- **manager**: Read, write, and update access
- **user**: Read-only access

## API Endpoints

The following endpoints are available:

* **GET /parts**: Retrieve all parts.
* **GET /parts/{part_id}**: Retrieve a specific part by ID.
* **POST /parts**: Create a new part.
* **PUT /parts/{part_id}**: Update an existing part.
* **DELETE /parts/{part_id}**: Delete a part.


## Data Model

The part data model includes the following fields:

* **id (int)**: Unique identifier for the part.
* **name (str)**: Name of the part.
* **description (str, optional)**: Description of the part.
* **quantity (int)**: Quantity of the part in stock.

## Example Usage

### Creating a new part:

```bash
curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_TOKEN" -d '{"name": "Example Part", "description": "A test part", "quantity": 10}' http://localhost:57891/parts
```

### Retrieving all parts:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:57891/parts
```

### Updating a part:

```bash
curl -X PUT -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_TOKEN" -d '{"name": "Updated Part", "quantity": 5}' http://localhost:57891/parts/1
```

### Deleting a part:

```bash
curl -X DELETE -H "Authorization: Bearer YOUR_TOKEN" http://localhost:57891/parts/1
```


