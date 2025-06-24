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


