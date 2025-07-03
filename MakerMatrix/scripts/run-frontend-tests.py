#!/usr/bin/env python3
"""
MakerMatrix Frontend Test Runner

This script provides a comprehensive way to run all frontend tests
including unit tests, integration tests, and end-to-end tests.
"""

import os
import sys
import subprocess
import time
import signal
import argparse
import json
from pathlib import Path
from typing import Optional, List
import requests
from contextlib import contextmanager

class TestRunner:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.frontend_path = project_root / "MakerMatrix" / "frontend"
        self.backend_process: Optional[subprocess.Popen] = None
        self.frontend_process: Optional[subprocess.Popen] = None
        
    def setup_environment(self):
        """Setup the testing environment"""
        print("🔧 Setting up testing environment...")
        
        # Check if we're in the right directory
        if not self.frontend_path.exists():
            raise FileNotFoundError(f"Frontend directory not found: {self.frontend_path}")
        
        # Check if node_modules exists
        if not (self.frontend_path / "node_modules").exists():
            print("📦 Installing frontend dependencies...")
            self.run_command(["npm", "install"], cwd=self.frontend_path)
        
        # Check if Python virtual environment exists
        venv_path = self.project_root / "venv_test"
        if not venv_path.exists():
            print("🐍 Creating Python virtual environment...")
            subprocess.run([sys.executable, "-m", "venv", "venv_test"], 
                         cwd=self.project_root, check=True)
            
            # Install Python dependencies
            pip_path = venv_path / "bin" / "pip"
            subprocess.run([str(pip_path), "install", "--upgrade", "pip"], check=True)
            subprocess.run([str(pip_path), "install", "-r", "requirements.txt"], 
                         cwd=self.project_root, check=True)
        
        print("✅ Environment setup complete")
    
    def run_command(self, cmd: List[str], cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
        """Run a command with proper error handling"""
        print(f"🏃 Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, cwd=cwd, check=check, capture_output=True, text=True)
            if result.stdout:
                print(result.stdout)
            return result
        except subprocess.CalledProcessError as e:
            print(f"❌ Command failed: {e}")
            if e.stdout:
                print(f"STDOUT: {e.stdout}")
            if e.stderr:
                print(f"STDERR: {e.stderr}")
            if check:
                raise
            return e
    
    def start_backend(self, timeout: int = 30) -> bool:
        """Start the backend server"""
        print("🚀 Starting backend server...")
        
        venv_python = self.project_root / "venv_test" / "bin" / "python"
        
        self.backend_process = subprocess.Popen([
            str(venv_python), "-m", "uvicorn",
            "MakerMatrix.main:app",
            "--host", "0.0.0.0",
            "--port", "57891"
        ], cwd=self.project_root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        
        # Wait for backend to be ready
        for i in range(timeout):
            try:
                response = requests.get("http://localhost:57891/docs", timeout=1)
                if response.status_code == 200:
                    print("✅ Backend server is ready")
                    return True
            except requests.RequestException:
                time.sleep(1)
        
        print("❌ Backend server failed to start")
        return False
    
    def start_frontend(self, mode: str = "dev", timeout: int = 30) -> bool:
        """Start the frontend server"""
        print(f"🚀 Starting frontend server in {mode} mode...")
        
        if mode == "dev":
            cmd = ["npm", "run", "dev"]
            expected_url = "http://localhost:5173"
        else:  # build mode
            # First build the application
            self.run_command(["npm", "run", "build"], cwd=self.frontend_path)
            cmd = ["npm", "run", "preview"]
            expected_url = "http://localhost:4173"
        
        self.frontend_process = subprocess.Popen(
            cmd, cwd=self.frontend_path, 
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        
        # Wait for frontend to be ready
        for i in range(timeout):
            try:
                response = requests.get(expected_url, timeout=1)
                if response.status_code == 200:
                    print("✅ Frontend server is ready")
                    return True
            except requests.RequestException:
                time.sleep(1)
        
        print("❌ Frontend server failed to start")
        return False
    
    def stop_servers(self):
        """Stop all running servers"""
        print("🛑 Stopping servers...")
        
        if self.backend_process:
            self.backend_process.terminate()
            try:
                self.backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.backend_process.kill()
            self.backend_process = None
        
        if self.frontend_process:
            self.frontend_process.terminate()
            try:
                self.frontend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.frontend_process.kill()
            self.frontend_process = None
        
        print("✅ Servers stopped")
    
    @contextmanager
    def servers_running(self, frontend_mode: str = "dev"):
        """Context manager for running servers during tests"""
        try:
            if not self.start_backend():
                raise RuntimeError("Failed to start backend")
            
            if not self.start_frontend(frontend_mode):
                raise RuntimeError("Failed to start frontend")
            
            yield
        finally:
            self.stop_servers()
    
    def run_unit_tests(self) -> bool:
        """Run unit and integration tests"""
        print("🧪 Running unit and integration tests...")
        
        try:
            # Run linting first
            print("📝 Running linter...")
            self.run_command(["npm", "run", "lint"], cwd=self.frontend_path)
            
            # Run type checking
            print("🔍 Running type checking...")
            self.run_command(["npx", "tsc", "--noEmit"], cwd=self.frontend_path)
            
            # Run tests with coverage
            print("🧪 Running tests with coverage...")
            self.run_command(["npm", "run", "test:coverage"], cwd=self.frontend_path)
            
            print("✅ Unit tests completed successfully")
            return True
            
        except subprocess.CalledProcessError:
            print("❌ Unit tests failed")
            return False
    
    def run_e2e_tests(self) -> bool:
        """Run end-to-end tests"""
        print("🌐 Running end-to-end tests...")
        
        try:
            # Install Playwright browsers if needed
            print("📥 Installing Playwright browsers...")
            self.run_command(["npx", "playwright", "install"], cwd=self.frontend_path)
            
            # Run E2E tests with servers
            with self.servers_running(frontend_mode="build"):
                print("🧪 Running Playwright E2E tests...")
                self.run_command(["npm", "run", "test:e2e"], cwd=self.frontend_path)
            
            print("✅ E2E tests completed successfully")
            return True
            
        except subprocess.CalledProcessError:
            print("❌ E2E tests failed")
            return False
        except RuntimeError as e:
            print(f"❌ Server setup failed: {e}")
            return False
    
    def run_visual_tests(self) -> bool:
        """Run visual regression tests"""
        print("👀 Running visual regression tests...")
        
        try:
            with self.servers_running():
                print("🧪 Running visual tests...")
                self.run_command(["npm", "run", "test:visual"], cwd=self.frontend_path)
            
            print("✅ Visual tests completed successfully")
            return True
            
        except subprocess.CalledProcessError:
            print("❌ Visual tests failed")
            return False
        except RuntimeError as e:
            print(f"❌ Server setup failed: {e}")
            return False
    
    def run_accessibility_tests(self) -> bool:
        """Run accessibility tests"""
        print("♿ Running accessibility tests...")
        
        try:
            with self.servers_running():
                print("🧪 Running accessibility tests...")
                # Run accessibility-focused Playwright tests
                self.run_command([
                    "npx", "playwright", "test", 
                    "--grep", "accessibility"
                ], cwd=self.frontend_path)
            
            print("✅ Accessibility tests completed successfully")
            return True
            
        except subprocess.CalledProcessError:
            print("❌ Accessibility tests failed")
            return False
        except RuntimeError as e:
            print(f"❌ Server setup failed: {e}")
            return False
    
    def generate_report(self, results: dict):
        """Generate a test report"""
        print("\n📊 Test Results Summary:")
        print("=" * 50)
        
        total_suites = len(results)
        passed_suites = sum(1 for result in results.values() if result)
        
        for test_type, passed in results.items():
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"{test_type.replace('_', ' ').title()}: {status}")
        
        print("=" * 50)
        print(f"Total: {passed_suites}/{total_suites} test suites passed")
        
        if passed_suites == total_suites:
            print("🎉 All tests passed!")
            return True
        else:
            print("⚠️  Some tests failed")
            return False
    
    def cleanup(self):
        """Cleanup resources"""
        self.stop_servers()

def main():
    parser = argparse.ArgumentParser(description="Run MakerMatrix frontend tests")
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--e2e", action="store_true", help="Run only E2E tests")
    parser.add_argument("--visual", action="store_true", help="Run only visual tests")
    parser.add_argument("--accessibility", action="store_true", help="Run only accessibility tests")
    parser.add_argument("--all", action="store_true", help="Run all tests (default)")
    parser.add_argument("--setup-only", action="store_true", help="Only setup environment")
    
    args = parser.parse_args()
    
    # Determine which tests to run
    if not any([args.unit, args.e2e, args.visual, args.accessibility]):
        args.all = True
    
    # Get project root
    project_root = Path(__file__).parent
    
    # Initialize test runner
    runner = TestRunner(project_root)
    
    # Setup signal handlers for cleanup
    def signal_handler(sig, _):
        print("\n🛑 Received interrupt signal, cleaning up...")
        runner.cleanup()
        sys.exit(1)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Setup environment
        runner.setup_environment()
        
        if args.setup_only:
            print("✅ Environment setup complete")
            return
        
        # Run tests
        results = {}
        
        if args.unit or args.all:
            results["unit_tests"] = runner.run_unit_tests()
        
        if args.e2e or args.all:
            results["e2e_tests"] = runner.run_e2e_tests()
        
        if args.visual or args.all:
            results["visual_tests"] = runner.run_visual_tests()
        
        if args.accessibility or args.all:
            results["accessibility_tests"] = runner.run_accessibility_tests()
        
        # Generate report
        success = runner.generate_report(results)
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
    finally:
        runner.cleanup()

if __name__ == "__main__":
    main()