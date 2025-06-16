# MakerMatrix Scripts

This directory contains utility scripts for MakerMatrix development and administration.

## Core Scripts

### `setup_admin.py`
- **Purpose**: Sets up default roles and admin user
- **Usage**: `python -m MakerMatrix.scripts.setup_admin`
- **Creates**: admin, manager, user roles and default admin user (admin/Admin123!)

### `run_repository_tests.py`  
- **Purpose**: Runs repository-specific tests
- **Usage**: `python MakerMatrix/scripts/run_repository_tests.py`

### `validate_tests.py`
- **Purpose**: Validates test configuration and structure
- **Usage**: `python MakerMatrix/scripts/validate_tests.py`

## Development Scripts (`dev/` directory)

⚠️ **Note**: These are development/testing scripts. Use with caution on production data.

### Database Population Scripts

#### `create_test_data.py`
- **Purpose**: Creates comprehensive test data for development
- **Creates**: 
  - Nested location hierarchy
  - Multiple categories
  - Sample parts with realistic inventory data
- **Usage**: `python MakerMatrix/scripts/dev/create_test_data.py`

#### `create_parts_direct.py`
- **Purpose**: Directly creates parts bypassing API validation
- **Usage**: `python MakerMatrix/scripts/dev/create_parts_direct.py`

#### `create_parts_manual.py`
- **Purpose**: Manual part creation with interactive prompts
- **Usage**: `python MakerMatrix/scripts/dev/create_parts_manual.py`

#### `create_parts_simple.py`
- **Purpose**: Simple batch part creation
- **Usage**: `python MakerMatrix/scripts/dev/create_parts_simple.py`

#### `assign_categories.py`
- **Purpose**: Batch assign categories to existing parts
- **Usage**: `python MakerMatrix/scripts/dev/assign_categories.py`

### Hardware Scripts

#### `find_and_test_printer.py`
- **Purpose**: Discovers and tests Brother QL printer connections
- **Usage**: `python MakerMatrix/scripts/dev/find_and_test_printer.py`

## Quick Database Setup

To set up a fresh development database with sample data:

```bash
# 1. Set up admin user and roles
python -m MakerMatrix.scripts.setup_admin

# 2. Populate with test data
python MakerMatrix/scripts/dev/create_test_data.py
```

## Database Population Order

When setting up a new development environment, run scripts in this order:

1. `setup_admin.py` - Creates roles and admin user
2. `create_test_data.py` - Creates locations, categories, and sample parts
3. `assign_categories.py` - (Optional) Assigns additional categories
4. `find_and_test_printer.py` - (Optional) Sets up printer if available

## Notes

- All scripts assume you're running from the project root directory
- Scripts use the same database configuration as the main application
- Development scripts are prefixed with `dev/` to distinguish from production utilities
- Always backup your database before running population scripts