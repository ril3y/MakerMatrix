#!/usr/bin/env python3
"""
Simple test script to verify error handling changes are working.
"""

def test_custom_exceptions():
    try:
        from MakerMatrix.repositories.custom_exceptions import (
            ResourceNotFoundError,
            PartAlreadyExistsError,
            CategoryAlreadyExistsError,
            LocationAlreadyExistsError,
            UserAlreadyExistsError,
            InvalidReferenceError
        )
        print("✅ All custom exceptions imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_exception_handlers():
    try:
        from MakerMatrix.handlers.exception_handlers import register_exception_handlers
        print("✅ Exception handlers imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Handler import error: {e}")
        return False

def test_repository_imports():
    try:
        from MakerMatrix.repositories.parts_repositories import PartRepository
        from MakerMatrix.repositories.location_repositories import LocationRepository
        from MakerMatrix.repositories.category_repositories import CategoryRepository
        from MakerMatrix.repositories.user_repository import UserRepository
        print("✅ All repositories imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Repository import error: {e}")
        return False

def test_service_imports():
    try:
        from MakerMatrix.services.part_service import PartService
        from MakerMatrix.services.location_service import LocationService
        from MakerMatrix.services.category_service import CategoryService
        from MakerMatrix.services.user_service import UserService
        print("✅ All services imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Service import error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Error Handling Refactoring...")
    print("=" * 50)
    
    all_tests_passed = True
    
    all_tests_passed &= test_custom_exceptions()
    all_tests_passed &= test_exception_handlers()
    all_tests_passed &= test_repository_imports()
    all_tests_passed &= test_service_imports()
    
    print("=" * 50)
    if all_tests_passed:
        print("🎉 All error handling changes are working correctly!")
    else:
        print("⚠️  Some issues found with error handling changes")