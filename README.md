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


### Running the Server

1. Start the server:

   ```bash
   uvicorn main:app --reload
   ```

   This will start the server in development mode with automatic reloading.

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
curl -X POST -H "Content-Type: application/json" -d '{"name": "Example Part", "description": "A test part", "quantity": 10}' http://localhost:8000/parts
```

### Retrieving all parts:

```bash
curl http://localhost:8000/parts
```

### Updating a part:

```bash
curl -X PUT -H "Content-Type: application/json" -d '{"name": "Updated Part", "quantity": 5}' http://localhost:8000/parts/1
```

### Deleting a part:

```bash
curl -X DELETE http://localhost:8000/parts/1
```


