"""
Test Server Configuration Module

This module provides configuration for testing against both isolated test databases
and real running servers. It supports multiple testing scenarios:

1. Isolated Unit Tests - In-memory database, no external dependencies
2. Integration Tests - Isolated test database, TestClient
3. Real Server Tests - Against actual running dev server with real data
"""

import os
import requests
import tempfile
from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session
from fastapi.testclient import TestClient
from typing import Dict, Optional, Tuple
from urllib.parse import urljoin
import ssl

from MakerMatrix.main import app


class TestServerConfig:
    """Configuration for different test server scenarios"""
    
    # Real server configuration (matches dev_manager.log)
    REAL_SERVER_BASE_URL = "https://localhost:8443"
    REAL_SERVER_HTTP_URL = "http://localhost:8080"
    
    # Test database configuration
    TEST_DB_PATH = None
    TEST_ENGINE = None
    
    @classmethod
    def create_test_client(cls) -> TestClient:
        """Create TestClient for isolated integration tests"""
        return TestClient(app)
    
    @classmethod
    def create_real_server_session(cls, verify_ssl: bool = False) -> requests.Session:
        """
        Create requests session for real server testing
        
        Args:
            verify_ssl: Whether to verify SSL certificates (False for self-signed)
        """
        session = requests.Session()
        
        if not verify_ssl:
            session.verify = False
            # Disable SSL warnings for self-signed certificates
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        return session
    
    @classmethod
    def get_real_server_url(cls, endpoint: str, use_https: bool = True) -> str:
        """
        Get full URL for real server endpoint
        
        Args:
            endpoint: API endpoint (e.g., "/api/parts/get_all_parts")
            use_https: Whether to use HTTPS (default) or HTTP
        """
        base_url = cls.REAL_SERVER_BASE_URL if use_https else cls.REAL_SERVER_HTTP_URL
        return urljoin(base_url, endpoint)
    
    @classmethod
    def authenticate_real_server(cls, username: str = "admin", password: str = "Admin123!") -> Optional[str]:
        """
        Authenticate against real server and return access token
        
        Args:
            username: Username for authentication
            password: Password for authentication
            
        Returns:
            Access token if successful, None if failed
        """
        session = cls.create_real_server_session()
        
        try:
            # Try HTTPS first
            login_url = cls.get_real_server_url("/auth/login", use_https=True)
            login_data = {"username": username, "password": password}
            
            response = session.post(login_url, json=login_data, timeout=10)
            
            if response.status_code == 200:
                return response.json().get("access_token")
            
            # If HTTPS fails, try HTTP
            login_url = cls.get_real_server_url("/auth/login", use_https=False)
            response = session.post(login_url, json=login_data, timeout=10)
            
            if response.status_code == 200:
                return response.json().get("access_token")
                
        except Exception as e:
            print(f"Authentication failed: {e}")
            return None
        
        return None
    
    @classmethod
    def is_real_server_running(cls) -> Tuple[bool, str]:
        """
        Check if real server is running
        
        Returns:
            Tuple of (is_running, server_url_used)
        """
        session = cls.create_real_server_session()
        
        # Check HTTPS first
        try:
            response = session.get(cls.REAL_SERVER_BASE_URL + "/docs", timeout=5)
            if response.status_code == 200:
                return True, cls.REAL_SERVER_BASE_URL
        except:
            pass
        
        # Check HTTP
        try:
            response = session.get(cls.REAL_SERVER_HTTP_URL + "/docs", timeout=5)
            if response.status_code == 200:
                return True, cls.REAL_SERVER_HTTP_URL
        except:
            pass
        
        return False, ""
    
    @classmethod
    def create_isolated_test_engine(cls, use_memory: bool = True):
        """Create isolated test database engine"""
        if use_memory:
            test_sqlite_url = "sqlite:///:memory:"
        else:
            test_db_fd, cls.TEST_DB_PATH = tempfile.mkstemp(suffix='.db')
            os.close(test_db_fd)
            test_sqlite_url = f"sqlite:///{cls.TEST_DB_PATH}"
        
        cls.TEST_ENGINE = create_engine(
            test_sqlite_url, 
            echo=False,
            connect_args={"check_same_thread": False}
        )
        
        # Import all models to ensure they're registered
        from MakerMatrix.models.models import *
        
        # Create all tables in test database
        SQLModel.metadata.create_all(cls.TEST_ENGINE)
        
        return cls.TEST_ENGINE
    
    @classmethod
    def setup_test_data(cls, engine=None):
        """Setup test data in isolated database"""
        if engine is None:
            engine = cls.TEST_ENGINE
        
        from MakerMatrix.repositories.user_repository import UserRepository
        from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin
        
        # Create user repository with test engine
        user_repo = UserRepository()
        user_repo.engine = engine
        
        # Setup default roles and admin user
        setup_default_roles(user_repo)
        setup_default_admin(user_repo)
    
    @classmethod
    def cleanup_test_resources(cls):
        """Clean up test resources"""
        if cls.TEST_ENGINE:
            cls.TEST_ENGINE.dispose()
        
        if cls.TEST_DB_PATH and os.path.exists(cls.TEST_DB_PATH):
            try:
                os.unlink(cls.TEST_DB_PATH)
            except FileNotFoundError:
                pass


class RealServerTestHelper:
    """Helper class for real server testing"""
    
    def __init__(self):
        self.session = TestServerConfig.create_real_server_session()
        self.token = None
        self.base_url = None
        self.authenticated = False
    
    def setup(self) -> bool:
        """Setup real server testing environment"""
        # Check if server is running
        is_running, server_url = TestServerConfig.is_real_server_running()
        if not is_running:
            print("❌ Real server is not running. Start dev_manager.py first.")
            return False
        
        self.base_url = server_url
        print(f"✅ Real server detected at: {server_url}")
        
        # Authenticate
        self.token = TestServerConfig.authenticate_real_server()
        if not self.token:
            print("❌ Authentication failed against real server")
            return False
        
        self.authenticated = True
        print("✅ Authentication successful")
        return True
    
    def get_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        if not self.authenticated:
            raise RuntimeError("Not authenticated. Call setup() first.")
        return {"Authorization": f"Bearer {self.token}"}
    
    def get_url(self, endpoint: str) -> str:
        """Get full URL for endpoint"""
        return urljoin(self.base_url, endpoint)
    
    def get(self, endpoint: str, **kwargs) -> requests.Response:
        """GET request to real server"""
        url = self.get_url(endpoint)
        headers = self.get_headers()
        return self.session.get(url, headers=headers, **kwargs)
    
    def post(self, endpoint: str, **kwargs) -> requests.Response:
        """POST request to real server"""
        url = self.get_url(endpoint)
        headers = self.get_headers()
        return self.session.post(url, headers=headers, **kwargs)
    
    def put(self, endpoint: str, **kwargs) -> requests.Response:
        """PUT request to real server"""
        url = self.get_url(endpoint)
        headers = self.get_headers()
        return self.session.put(url, headers=headers, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """DELETE request to real server"""
        url = self.get_url(endpoint)
        headers = self.get_headers()
        return self.session.delete(url, headers=headers, **kwargs)
    
    def upload_file(self, endpoint: str, file_path: str, **kwargs) -> requests.Response:
        """Upload file to real server"""
        url = self.get_url(endpoint)
        headers = self.get_headers()
        
        with open(file_path, 'rb') as f:
            files = {"file": f}
            return self.session.post(url, headers=headers, files=files, **kwargs)
    
    def test_csv_import(self, csv_file_path: str, supplier_name: str = "lcsc") -> requests.Response:
        """Test CSV import against real server"""
        url = self.get_url("/api/import/file")
        headers = self.get_headers()
        
        with open(csv_file_path, 'rb') as f:
            files = {"file": f}
            data = {"supplier_name": supplier_name}
            return self.session.post(url, headers=headers, files=files, data=data)
    
    def get_system_counts(self) -> requests.Response:
        """Get system counts from real server"""
        return self.get("/api/utility/get_counts")
    
    def get_all_parts(self, page: int = 1, page_size: int = 10) -> requests.Response:
        """Get all parts from real server"""
        params = {"page": page, "page_size": page_size}
        return self.get("/api/parts/get_all_parts", params=params)
    
    def create_part(self, part_data: Dict) -> requests.Response:
        """Create part on real server"""
        return self.post("/api/parts/add_part", json=part_data)
    
    def cleanup_test_data(self):
        """Clean up test data from real server (use with caution)"""
        print("⚠️  Cleanup of real server data not implemented for safety")
        print("⚠️  Use dev_manager.py to restart server if needed")