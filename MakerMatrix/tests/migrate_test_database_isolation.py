"""
Migration Script: Test Database Isolation

This script migrates test files to use isolated test database fixtures
instead of the main application database engine.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Tuple


class TestFileMigrator:
    """Migrates test files to use isolated database fixtures"""
    
    def __init__(self, test_root_dir: str):
        self.test_root_dir = Path(test_root_dir)
        self.migration_report = {
            'files_processed': 0,
            'files_migrated': 0,
            'imports_removed': 0,
            'fixtures_updated': 0,
            'errors': []
        }
    
    def find_problematic_test_files(self) -> List[Path]:
        """Find test files that import main database engine"""
        problematic_files = []
        
        for test_file in self.test_root_dir.rglob("test_*.py"):
            try:
                content = test_file.read_text()
                
                # Check for problematic imports
                if any([
                    "from MakerMatrix.models.models import engine" in content,
                    "from MakerMatrix.models.models import engine," in content,
                    "MakerMatrix.models.models.engine" in content
                ]):
                    problematic_files.append(test_file)
                    
            except Exception as e:
                self.migration_report['errors'].append(f"Error reading {test_file}: {e}")
        
        return problematic_files
    
    def migrate_integration_test_file(self, file_path: Path) -> bool:
        """Migrate an integration test file to use isolated fixtures"""
        try:
            content = file_path.read_text()
            original_content = content
            
            # Remove problematic imports
            content = self._remove_main_engine_imports(content)
            
            # Update database setup fixtures
            content = self._update_database_fixtures(content)
            
            # Update engine usage in test code
            content = self._update_engine_usage(content)
            
            # Add proper imports for test fixtures
            content = self._add_test_fixture_imports(content)
            
            # Only write if content changed
            if content != original_content:
                file_path.write_text(content)
                self.migration_report['files_migrated'] += 1
                return True
            
            return False
            
        except Exception as e:
            self.migration_report['errors'].append(f"Error migrating {file_path}: {e}")
            return False
    
    def _remove_main_engine_imports(self, content: str) -> str:
        """Remove imports of main database engine"""
        patterns = [
            r'from MakerMatrix\.models\.models import engine\n',
            r'from MakerMatrix\.models\.models import engine,',
            r', engine',
            r'engine,'
        ]
        
        for pattern in patterns:
            if re.search(pattern, content):
                content = re.sub(pattern, '', content)
                self.migration_report['imports_removed'] += 1
        
        return content
    
    def _update_database_fixtures(self, content: str) -> str:
        """Update database setup fixtures to use isolated test engine"""
        
        # Replace old database setup fixture
        old_fixture_pattern = r'@pytest\.fixture\(scope="function", autouse=True\)\ndef setup_database\(\):(.*?)yield'
        new_fixture = """@pytest.fixture(scope="function", autouse=True)
def setup_database(isolated_test_engine):
    \"\"\"Set up isolated test database before running tests.\"\"\"
    from MakerMatrix.database.db import create_db_and_tables
    from MakerMatrix.repositories.user_repository import UserRepository
    from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin
    
    # Create user repository with isolated test engine
    user_repo = UserRepository()
    user_repo.engine = isolated_test_engine
    
    # Setup default roles and admin user in test database
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)
    
    yield"""
        
        if re.search(old_fixture_pattern, content, re.DOTALL):
            content = re.sub(old_fixture_pattern, new_fixture, content, flags=re.DOTALL)
            self.migration_report['fixtures_updated'] += 1
        
        return content
    
    def _update_engine_usage(self, content: str) -> str:
        """Update engine usage in test code"""
        
        # Replace direct engine usage with isolated_test_engine parameter
        replacements = [
            (r'SQLModel\.metadata\.drop_all\(engine\)', 'SQLModel.metadata.drop_all(isolated_test_engine)'),
            (r'SQLModel\.metadata\.create_all\(engine\)', 'SQLModel.metadata.create_all(isolated_test_engine)'),
            (r'Session\(engine\)', 'Session(isolated_test_engine)'),
            (r'engine\.dispose\(\)', 'isolated_test_engine.dispose()'),
        ]
        
        for old_pattern, new_pattern in replacements:
            content = re.sub(old_pattern, new_pattern, content)
        
        return content
    
    def _add_test_fixture_imports(self, content: str) -> str:
        """Add necessary imports for test fixtures"""
        
        # Check if we need to add test fixture imports
        if "isolated_test_engine" in content and "from MakerMatrix.tests.test_database_config import" not in content:
            # Find the last import line
            import_lines = []
            other_lines = []
            in_imports = True
            
            for line in content.split('\\n'):
                if in_imports and (line.startswith('import ') or line.startswith('from ') or line.strip() == ''):
                    import_lines.append(line)
                else:
                    in_imports = False
                    other_lines.append(line)
            
            # Add test fixture import
            import_lines.append("from MakerMatrix.tests.test_database_config import setup_test_database_with_admin")
            
            content = '\\n'.join(import_lines) + '\\n' + '\\n'.join(other_lines)
        
        return content
    
    def generate_migration_report(self) -> str:
        """Generate a migration report"""
        report = f"""
Test Database Isolation Migration Report
======================================

Files processed: {self.migration_report['files_processed']}
Files migrated: {self.migration_report['files_migrated']}
Imports removed: {self.migration_report['imports_removed']}
Fixtures updated: {self.migration_report['fixtures_updated']}

"""
        
        if self.migration_report['errors']:
            report += "Errors encountered:\\n"
            for error in self.migration_report['errors']:
                report += f"  - {error}\\n"
        
        return report
    
    def run_migration(self) -> str:
        """Run the complete migration process"""
        print("Starting test database isolation migration...")
        
        # Find problematic files
        problematic_files = self.find_problematic_test_files()
        print(f"Found {len(problematic_files)} files that need migration")
        
        # Migrate each file
        for file_path in problematic_files:
            print(f"Processing {file_path}...")
            self.migration_report['files_processed'] += 1
            
            if self.migrate_integration_test_file(file_path):
                print(f"  ✓ Migrated {file_path}")
            else:
                print(f"  - No changes needed for {file_path}")
        
        return self.generate_migration_report()


def main():
    """Main migration function"""
    test_root = "/home/ril3y/MakerMatrix/MakerMatrix/tests"
    migrator = TestFileMigrator(test_root)
    
    report = migrator.run_migration()
    print(report)
    
    # Save migration report
    with open(f"{test_root}/migration_report.txt", "w") as f:
        f.write(report)


if __name__ == "__main__":
    main()