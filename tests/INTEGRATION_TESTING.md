# Integration Testing Guide

This guide covers the backup/restore integration test suite for MakerMatrix.

## Overview

Integration tests verify that backup and restore operations work correctly with **real databases and files** (not mocks). These tests ensure data integrity and system reliability.

**IMPORTANT**: These tests NEVER touch production data. All tests use isolated test databases in `/tmp/makermatrix_test_dbs/`.

---

## Test Suite Structure

### Test Files

```
tests/
├── test_backup_restore_integration.py  # Main integration test suite (7 tests)
└── fixtures/
    ├── __init__.py                     # Fixture exports
    ├── test_database.py                # Database fixture utilities
    └── test_data_generators.py         # Test data creation helpers
```

### Test Coverage

| Test Class | Tests | Description |
|------------|-------|-------------|
| `TestBackupCreation` | 3 | Backup file creation, datasheet/image inclusion |
| `TestRestoreOperations` | 1 | Database restoration from backup |
| `TestDataIntegrity` | 2 | Data preservation verification |
| `TestErrorHandling` | 1 | Error scenarios and edge cases |
| **Total** | **7** | **Complete backup/restore lifecycle** |

---

## Running Integration Tests

### Local Development

```bash
# Run all integration tests
pytest tests/test_backup_restore_integration.py -v

# Run specific test class
pytest tests/test_backup_restore_integration.py::TestBackupCreation -v

# Run specific test
pytest tests/test_backup_restore_integration.py::TestRestoreOperations::test_restore_database_from_backup -v

# Run with verbose output (see print statements)
pytest tests/test_backup_restore_integration.py -vv -s
```

### CI/CD (GitHub Actions)

Integration tests run automatically on:
- **Push** to `main` or `develop` branches
- **Pull requests** targeting `main` or `develop`

See `.github/workflows/backend-quality.yml` for configuration.

---

## Test Database Isolation

### How Tests Avoid Production Data

1. **Unique Database Files**: Each test creates a unique database file:
   ```
   /tmp/makermatrix_test_dbs/test_backup_20251022_143458_59edb70d.db
   ```

2. **Temporary Static Files**: Test datasheets/images stored separately:
   ```
   /tmp/makermatrix_test_dbs/static_test_backup_20251022_143458_59edb70d/
   ├── datasheets/
   └── images/
   ```

3. **Automatic Cleanup**: Pytest fixtures clean up all test databases after execution

4. **Environment Override**: Tests temporarily override `DATABASE_URL` to point to test database

---

## Test Fixtures

### Database Fixtures

**`test_db_path`** - Generates unique database file path
```python
@pytest.fixture(scope="function")
def test_db_path() -> Generator[Path, None, None]:
    # Creates: /tmp/makermatrix_test_dbs/test_backup_{timestamp}_{uuid}.db
    # Cleanup: Removes database file after test
```

**`test_engine`** - SQLAlchemy engine for test database
```python
@pytest.fixture(scope="function")
def test_engine(test_db_path: Path):
    # Returns configured SQLAlchemy engine
    # Foreign keys enabled
```

**`test_session`** - Database session for queries
```python
@pytest.fixture(scope="function")
def test_session(test_engine) -> Generator[Session, None, None]:
    # Returns SQLModel session
```

**`test_db_with_schema`** - Empty database with full schema
```python
@pytest.fixture(scope="function")
def test_db_with_schema(test_engine, test_db_path: Path):
    # Creates all tables from SQLModel metadata
    # Returns: (engine, db_path)
```

**`test_static_files_dir`** - Temporary directory for static files
```python
@pytest.fixture(scope="function")
def test_static_files_dir(test_db_path: Path) -> Generator[Path, None, None]:
    # Creates: datasheets/ and images/ subdirectories
    # Cleanup: Removes all files and directories
```

### Data Generator Functions

**`populate_test_database(session, static_files_dir)`** - Complete test data setup

Creates:
- 2 roles (admin, user)
- 2 users (admin, regular)
- 2 API keys
- 8 categories (hierarchical)
- 10 locations (hierarchical, including mobile cassettes)
- 5 parts (resistors, capacitors, screws, ICs, LEDs)
- 4 part allocations (parts distributed across locations)
- Test datasheet files (minimal valid PDFs)
- Test image files (minimal valid PNGs)

Returns dictionary with references to all created objects.

---

## Test Scenarios

### Backup Creation Tests

**test_create_backup_from_populated_database**
- Creates populated database
- Executes backup task
- Verifies backup file exists
- Validates ZIP structure
- Checks metadata content

**test_backup_includes_datasheets**
- Creates datasheets in test directory
- Executes backup with `include_datasheets=True`
- Verifies datasheet files in backup ZIP

**test_backup_includes_images**
- Creates images in test directory
- Executes backup with `include_images=True`
- Verifies image files in backup ZIP

### Restore Tests

**test_restore_database_from_backup**
- Creates populated database
- Creates backup
- Simulates data corruption (keeps existing file for overwrite)
- Executes restore
- Verifies database file restored
- Verifies record counts match original
- Validates data integrity

### Data Integrity Tests

**test_part_data_matches_after_restore**
- Creates specific part with known data
- Backup and restore
- Queries restored part
- Verifies all fields match exactly

**test_allocation_relationships_preserved**
- Creates part-location allocations
- Backup and restore
- Verifies allocation relationships intact
- Validates foreign key integrity

### Error Handling Tests

**test_restore_from_nonexistent_backup**
- Attempts restore from missing file
- Verifies appropriate error raised
- Checks error message clarity

---

## Common Issues and Solutions

### Issue: Tests fail with "no such table"

**Cause**: Test database schema not created

**Solution**: Ensure `test_db_with_schema` fixture is used (not just `test_engine`)

```python
# ✅ Correct
def test_something(test_db_with_schema, test_static_files_dir):
    engine, db_path = test_db_with_schema

# ❌ Wrong
def test_something(test_engine, test_db_path):
    # Tables not created!
```

### Issue: Tests fail with "database is locked"

**Cause**: Engine not disposed before file operations

**Solution**: Call `engine.dispose()` before manipulating database file

```python
# ✅ Correct
engine.dispose()  # Close all connections
db_path.unlink()  # Safe to delete

# ❌ Wrong
db_path.unlink()  # Database is locked!
```

### Issue: Backup/restore uses wrong database path

**Cause**: `DATABASE_URL` environment variable not overridden

**Solution**: Set environment variable before executing tasks

```python
original_db_url = os.environ.get('DATABASE_URL')
os.environ['DATABASE_URL'] = f"sqlite:///{db_path}"

try:
    # Execute backup/restore
    pass
finally:
    # Restore original
    if original_db_url:
        os.environ['DATABASE_URL'] = original_db_url
    else:
        os.environ.pop('DATABASE_URL', None)
```

### Issue: Static files not found

**Cause**: `STATIC_FILES_PATH` not overridden for datasheets/images

**Solution**: Override environment variable to test directory

```python
os.environ['STATIC_FILES_PATH'] = str(test_static_files_dir)
```

---

## Adding New Integration Tests

### Step 1: Use Appropriate Fixtures

```python
@pytest.mark.asyncio
async def test_my_new_test(
    test_db_with_schema,      # Database with schema
    test_static_files_dir     # Static files directory
):
    engine, db_path = test_db_with_schema
    # Test implementation
```

### Step 2: Populate Test Data

```python
with Session(engine) as session:
    test_data = populate_test_database(session, test_static_files_dir)

    # Access created objects
    admin_user = test_data['users'][0]
    parts = test_data['parts']
    locations = test_data['locations']
```

### Step 3: Override Environment Variables

```python
original_db_url = os.environ.get('DATABASE_URL')
original_static_path = os.environ.get('STATIC_FILES_PATH')

os.environ['DATABASE_URL'] = f"sqlite:///{db_path}"
os.environ['STATIC_FILES_PATH'] = str(test_static_files_dir)

try:
    # Test logic here
    pass
finally:
    # Restore environment
    if original_db_url:
        os.environ['DATABASE_URL'] = original_db_url
    else:
        os.environ.pop('DATABASE_URL', None)

    if original_static_path:
        os.environ['STATIC_FILES_PATH'] = original_static_path
    else:
        os.environ.pop('STATIC_FILES_PATH', None)
```

### Step 4: Verify and Clean Up

```python
# Verify results
assert result['database_restored'] is True
assert db_path.exists()

# Cleanup (if needed beyond fixture cleanup)
if backup_path.exists():
    backup_path.unlink()
```

---

## Best Practices

### DO:
✅ Use `test_db_with_schema` fixture for tests requiring database schema
✅ Call `engine.dispose()` before file operations on database
✅ Override `DATABASE_URL` to point to test database
✅ Use `populate_test_database()` for consistent test data
✅ Clean up temporary files in fixture teardown
✅ Use descriptive test names that explain what's being tested

### DON'T:
❌ Touch production database (`makermatrix.db`)
❌ Hardcode file paths
❌ Skip environment variable restoration in `finally` blocks
❌ Leave test databases in `/tmp` (fixtures clean up automatically)
❌ Mock backup/restore operations (these are integration tests)
❌ Skip assertions on data integrity

---

## Performance Considerations

### Test Execution Time

- **Single test**: 2-4 seconds
- **Full suite (7 tests)**: ~20-25 seconds
- **CI/CD timeout**: 10 minutes (configured in workflow)

### Optimization Tips

1. **Parallel execution**: Tests are isolated and can run in parallel
   ```bash
   pytest tests/test_backup_restore_integration.py -n auto
   ```

2. **Test selection**: Run only affected tests during development
   ```bash
   pytest tests/test_backup_restore_integration.py::TestBackupCreation -v
   ```

3. **Cleanup efficiency**: Fixtures use automatic cleanup (no manual intervention)

---

## CI/CD Integration

### GitHub Actions Workflow

**File**: `.github/workflows/backend-quality.yml`

**Job**: `integration-tests`

**Triggers**:
- Push to `main` or `develop`
- Pull requests to `main` or `develop`

**Steps**:
1. Checkout code
2. Setup Python 3.11
3. Install dependencies
4. Run integration tests (10-minute timeout)
5. Upload test databases on failure (for debugging)
6. Upload test results XML
7. Comment on PR if tests fail

### Artifacts

On test failure, CI uploads:
- **Test databases**: `/tmp/makermatrix_test_dbs/` (retained 7 days)
- **Test results**: JUnit XML format (retained 30 days)

---

## Troubleshooting CI/CD

### Tests pass locally but fail in CI

**Possible causes**:
1. **Different Python version**: CI uses Python 3.11
2. **Missing dependencies**: Check `requirements.txt`
3. **Path differences**: CI uses different file paths
4. **Permissions**: CI may have different file permissions

**Solution**: Run tests in Docker container locally to match CI environment

### Test timeout in CI

**Cause**: Tests exceed 10-minute timeout

**Solution**: Optimize test data size or increase timeout in workflow:
```yaml
timeout-minutes: 15  # Increase if needed
```

---

## Maintenance

### When to Update Tests

- **Database schema changes**: Update test data generators
- **Backup format changes**: Add new test cases
- **New backup options**: Test new features
- **Bug fixes**: Add regression tests

### Keeping Fixtures Updated

If models change, update `test_data_generators.py`:
- New fields: Add to test data creation
- New relationships: Update allocation logic
- New models: Create generator functions

---

## References

- **Test File**: `tests/test_backup_restore_integration.py`
- **Fixtures**: `tests/fixtures/test_database.py`, `tests/fixtures/test_data_generators.py`
- **Workflow**: `.github/workflows/backend-quality.yml`
- **Backup Task**: `MakerMatrix/tasks/database_backup_task.py`
- **Restore Task**: `MakerMatrix/tasks/database_restore_task.py`

---

**Last Updated**: October 22, 2025
**Test Suite Version**: 1.0
**Total Tests**: 7
**Pass Rate**: 100%
