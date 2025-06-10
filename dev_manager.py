#!/usr/bin/env python3
"""
MakerMatrix Development Server Manager
A TUI application to manage both backend and frontend development servers
"""

import asyncio
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

import requests
from blessed import Terminal


class ServerManager:
    def __init__(self):
        self.term = Terminal()
        self.backend_process: Optional[subprocess.Popen] = None
        self.frontend_process: Optional[subprocess.Popen] = None
        self.backend_logs = deque(maxlen=100)
        self.frontend_logs = deque(maxlen=100)
        self.running = True
        self.backend_status = "Stopped"
        self.frontend_status = "Stopped"
        self.selected_view = "backend"  # backend, frontend, both
        self.log_scroll = 0
        
        # URLs
        self.backend_url = "http://localhost:57891"
        self.frontend_url = "http://localhost:5173"  # Vite's default dev port
        
        # Paths
        self.project_root = Path(__file__).parent
        self.frontend_path = self.project_root / "MakerMatrix" / "frontend"
        
        # Dashboard stats
        self.stats = {
            "parts_count": 0,
            "locations_count": 0,
            "categories_count": 0,
            "users_count": 0,
            "last_updated": None
        }
        self.stats_error = None
        
    def log_message(self, service: str, message: str, level: str = "INFO"):
        """Add a log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Color code special log levels
        if level == "CHANGE":
            log_entry = f"[{timestamp}] [🔄 CHANGE] {message}"
        elif level == "ERROR":
            log_entry = f"[{timestamp}] [❌ ERROR] {message}"
        elif level == "WARN":
            log_entry = f"[{timestamp}] [⚠️  WARN] {message}"
        else:
            log_entry = f"[{timestamp}] [{level}] {message}"
        
        if service == "backend":
            self.backend_logs.append(log_entry)
        elif service == "frontend":
            self.frontend_logs.append(log_entry)
        else:
            # System messages go to both
            self.backend_logs.append(f"[{timestamp}] [SYSTEM] {message}")
            self.frontend_logs.append(f"[{timestamp}] [SYSTEM] {message}")
    
    def start_backend(self):
        """Start the FastAPI backend server"""
        try:
            if self.backend_process and self.backend_process.poll() is None:
                self.log_message("backend", "Backend already running", "WARN")
                return
            
            self.log_message("backend", "Starting FastAPI backend server...")
            # Use the venv_test Python if available
            venv_python = self.project_root / "venv_test" / "bin" / "python"
            if venv_python.exists():
                python_exe = str(venv_python)
            else:
                python_exe = sys.executable
                
            self.backend_process = subprocess.Popen(
                [python_exe, "-m", "MakerMatrix.main"],
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Start log monitoring thread
            threading.Thread(
                target=self._monitor_process_output,
                args=(self.backend_process, "backend"),
                daemon=True
            ).start()
            
            self.backend_status = "Starting"
            self.log_message("backend", f"Backend PID: {self.backend_process.pid}")
            
        except Exception as e:
            self.log_message("backend", f"Failed to start backend: {e}", "ERROR")
            self.backend_status = "Failed"
    
    def start_frontend(self):
        """Start the React frontend development server"""
        try:
            if self.frontend_process and self.frontend_process.poll() is None:
                self.log_message("frontend", "Frontend already running", "WARN")
                return
            
            if not self.frontend_path.exists():
                self.log_message("frontend", f"Frontend path not found: {self.frontend_path}", "ERROR")
                return
                
            self.log_message("frontend", "Starting React development server...")
            self.frontend_process = subprocess.Popen(
                ["npm", "run", "dev"],
                cwd=self.frontend_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Start log monitoring thread
            threading.Thread(
                target=self._monitor_process_output,
                args=(self.frontend_process, "frontend"),
                daemon=True
            ).start()
            
            self.frontend_status = "Starting"
            self.log_message("frontend", f"Frontend PID: {self.frontend_process.pid}")
            
        except Exception as e:
            self.log_message("frontend", f"Failed to start frontend: {e}", "ERROR")
            self.frontend_status = "Failed"
    
    def _monitor_process_output(self, process: subprocess.Popen, service: str):
        """Monitor process output and update logs"""
        try:
            for line in iter(process.stdout.readline, ''):
                if not line:
                    break
                    
                line = line.strip()
                if line:
                    # Update status based on log content
                    if service == "backend":
                        if "Application startup complete" in line or "Uvicorn running on" in line:
                            self.backend_status = "Running"
                        elif "CRITICAL" in line.upper() or ("ERROR" in line.upper() and 
                              not any(ignore in line for ignore in [
                                  "Error loading configuration from printer_config.json",
                                  "printer configuration",
                                  "printer_config.json"
                              ])):
                            self.backend_status = "Error"
                    elif service == "frontend":
                        if "Local:" in line and "http://" in line:
                            self.frontend_status = "Running"
                            # Extract the actual URL - handle different formats
                            if "http://localhost:" in line:
                                try:
                                    # Look for the port in the line
                                    port_match = re.search(r'http://localhost:(\d+)', line)
                                    if port_match:
                                        port = port_match.group(1)
                                        self.frontend_url = f"http://localhost:{port}"
                                        self.log_message("frontend", f"Frontend URL updated to: {self.frontend_url}")
                                except:
                                    pass
                        elif "ERROR" in line.upper() or "Failed to compile" in line:
                            self.frontend_status = "Error"
                        # Detect file changes and HMR events (Vite patterns)
                        elif any(keyword in line.lower() for keyword in [
                            "hmr update", "page reload", "file changed", "rebuilding", 
                            "reloading", "full reload", "hot updated", "[vite] hot update",
                            "src updated", "hmr", "hot reloaded"
                        ]):
                            self.log_message("frontend", f"🔄 HMR: {line}", "CHANGE")
                        # Detect specific file changes  
                        elif ("src/" in line and any(ext in line for ext in [".tsx", ".ts", ".jsx", ".js", ".css", ".scss"])) or \
                             (any(pattern in line.lower() for pattern in ["updated", "changed", "modified"]) and 
                              any(ext in line for ext in [".tsx", ".ts", ".jsx", ".js", ".css"])):
                            self.log_message("frontend", f"📝 File Changed: {line}", "CHANGE")
                        # Generic Vite update patterns
                        elif "[vite]" in line.lower() and any(keyword in line.lower() for keyword in ["update", "reload", "change"]):
                            self.log_message("frontend", f"🔄 Vite: {line}", "CHANGE")
                    
                    self.log_message(service, line)
                    
        except Exception as e:
            self.log_message(service, f"Log monitoring error: {e}", "ERROR")
        finally:
            # Process ended
            if service == "backend":
                self.backend_status = "Stopped"
                self.stats_error = "Backend offline"
            else:
                self.frontend_status = "Stopped"
    
    def stop_backend(self):
        """Stop the backend server"""
        if self.backend_process and self.backend_process.poll() is None:
            self.log_message("backend", "Stopping backend server...")
            self.backend_process.terminate()
            try:
                self.backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.backend_process.kill()
            self.backend_status = "Stopped"
        else:
            self.log_message("backend", "Backend not running", "WARN")
    
    def stop_frontend(self):
        """Stop the frontend server"""
        if self.frontend_process and self.frontend_process.poll() is None:
            self.log_message("frontend", "Stopping frontend server...")
            self.frontend_process.terminate()
            try:
                self.frontend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.frontend_process.kill()
            self.frontend_status = "Stopped"
        else:
            self.log_message("frontend", "Frontend not running", "WARN")
    
    def stop_all(self):
        """Stop both servers"""
        self.stop_backend()
        self.stop_frontend()
    
    def build_frontend(self):
        """Build the frontend for production"""
        try:
            if not self.frontend_path.exists():
                self.log_message("frontend", f"Frontend path not found: {self.frontend_path}", "ERROR")
                return
            
            self.log_message("frontend", "Building frontend for production...")
            
            # Stop frontend dev server if running
            if self.frontend_process and self.frontend_process.poll() is None:
                self.log_message("frontend", "Stopping dev server before build...")
                self.stop_frontend()
                time.sleep(2)
            
            # Run the build command
            build_process = subprocess.Popen(
                ["npm", "run", "build"],
                cwd=self.frontend_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            # Monitor build output
            output_lines = []
            for line in iter(build_process.stdout.readline, ''):
                if not line:
                    break
                line = line.strip()
                if line:
                    output_lines.append(line)
                    self.log_message("frontend", f"BUILD: {line}")
            
            # Wait for build to complete
            return_code = build_process.wait()
            
            if return_code == 0:
                self.log_message("frontend", "✅ Frontend build completed successfully!", "INFO")
                self.log_message("frontend", "📦 Production build is ready in MakerMatrix/frontend/dist/", "INFO")
            else:
                self.log_message("frontend", f"❌ Frontend build failed with code {return_code}", "ERROR")
                
        except Exception as e:
            self.log_message("frontend", f"Failed to build frontend: {e}", "ERROR")
    
    def get_status_color(self, status: str):
        """Get color for status display"""
        colors = {
            "Running": self.term.green,
            "Starting": self.term.yellow,
            "Stopped": self.term.red,
            "Failed": self.term.red,
            "Error": self.term.red
        }
        return colors.get(status, self.term.white)
    
    def fetch_dashboard_stats(self):
        """Fetch dashboard statistics from the backend API"""
        if self.backend_status != "Running":
            return
            
        try:
            # Use the utility endpoint to get all counts in one call
            response = requests.get(f"{self.backend_url}/utility/get_counts", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success" and "data" in data:
                    counts_data = data["data"]
                    stats = {
                        "parts_count": counts_data.get("parts", 0),
                        "locations_count": counts_data.get("locations", 0), 
                        "categories_count": counts_data.get("categories", 0),
                        "last_updated": datetime.now().strftime("%H:%M:%S")
                    }
                    
                    # Get users count from the API
                    try:
                        users_response = requests.get(f"{self.backend_url}/users/all", timeout=2)
                        if users_response.status_code == 200:
                            users_data = users_response.json()
                            if users_data.get("status") == "success" and "data" in users_data:
                                stats["users_count"] = len(users_data["data"])
                            else:
                                stats["users_count"] = "N/A"
                        else:
                            stats["users_count"] = "N/A"
                    except Exception as e:
                        stats["users_count"] = "N/A"
                    
                    # Update stats
                    self.stats.update(stats)
                    self.stats_error = None
                else:
                    self.stats_error = "Invalid API response format"
            else:
                self.stats_error = f"API returned {response.status_code}"
                
        except requests.exceptions.ConnectionError:
            self.stats_error = "Cannot connect to backend"
        except requests.exceptions.Timeout:
            self.stats_error = "API request timeout"
        except Exception as e:
            self.stats_error = f"API Error: {str(e)[:30]}..."
    
    def draw_header(self):
        """Draw the header section"""
        with self.term.location(0, 0):
            print(self.term.clear_eol + self.term.bold + self.term.blue + "🚀 MakerMatrix Development Manager" + self.term.normal)
        
        with self.term.location(0, 1):
            print(self.term.clear_eol + "─" * self.term.width)
        
        # Status line
        with self.term.location(0, 2):
            backend_color = self.get_status_color(self.backend_status)
            frontend_color = self.get_status_color(self.frontend_status)
            
            print(self.term.clear_eol + f"Backend: {backend_color}{self.backend_status}{self.term.normal} ({self.backend_url}) | "
                  f"Frontend: {frontend_color}{self.frontend_status}{self.term.normal} ({self.frontend_url})")
        
        # Dashboard stats line
        with self.term.location(0, 3):
            if self.stats_error:
                print(self.term.clear_eol + f"📊 Dashboard: {self.term.red}{self.stats_error}{self.term.normal}")
            elif self.stats["last_updated"]:
                stats_text = (f"📊 Parts: {self.stats['parts_count']} | "
                             f"Locations: {self.stats['locations_count']} | "
                             f"Categories: {self.stats['categories_count']} | "
                             f"Users: {self.stats['users_count']} | "
                             f"Updated: {self.stats['last_updated']}")
                print(self.term.clear_eol + self.term.cyan + stats_text + self.term.normal)
            else:
                print(self.term.clear_eol + f"📊 Dashboard: {self.term.yellow}Waiting for backend...{self.term.normal}")
    
    def draw_controls(self):
        """Draw the controls section"""
        y = 5
        with self.term.location(0, y):
            print(self.term.clear_eol + self.term.bold + "Controls:" + self.term.normal)
        
        controls = [
            "1: Start Backend  2: Stop Backend   3: Start Frontend  4: Stop Frontend",
            "5: Start Both     6: Stop Both      7: Restart Backend 8: Restart Frontend", 
            "9: Build Frontend (Production)  v: Switch View  r: Refresh Stats  ↑↓: Scroll  q: Quit"
        ]
        
        for i, control in enumerate(controls):
            with self.term.location(0, y + 1 + i):
                print(self.term.clear_eol + control)
    
    def draw_logs(self):
        """Draw the logs section"""
        log_start_y = 10
        available_height = self.term.height - log_start_y - 2
        
        with self.term.location(0, log_start_y - 1):
            view_indicator = f"View: {self.selected_view.title()}"
            print(self.term.clear_eol + "─" * (self.term.width // 2) + f" {view_indicator} " + "─" * (self.term.width // 2))
        
        # Get logs based on selected view
        if self.selected_view == "backend":
            logs = list(self.backend_logs)
        elif self.selected_view == "frontend":
            logs = list(self.frontend_logs)
        else:  # both
            # Interleave logs by timestamp (simplified)
            backend_logs = [(log, "B") for log in self.backend_logs]
            frontend_logs = [(log, "F") for log in self.frontend_logs]
            all_logs = backend_logs + frontend_logs
            all_logs.sort(key=lambda x: x[0][:8] if len(x[0]) > 8 else x[0])  # Sort by timestamp
            logs = [f"[{source}] {log}" for log, source in all_logs]
        
        # Apply scroll offset
        start_idx = max(0, len(logs) - available_height + self.log_scroll)
        visible_logs = logs[start_idx:start_idx + available_height]
        
        # Clear log area and draw logs
        for i in range(available_height):
            with self.term.location(0, log_start_y + i):
                if i < len(visible_logs):
                    log_line = visible_logs[i]
                    # Truncate if too long
                    if len(log_line) > self.term.width - 1:
                        log_line = log_line[:self.term.width - 4] + "..."
                    print(self.term.clear_eol + log_line)
                else:
                    print(self.term.clear_eol)
    
    def handle_input(self, key):
        """Handle keyboard input"""
        if key == 'q':
            self.running = False
        elif key == '1':
            self.start_backend()
        elif key == '2':
            self.stop_backend()
        elif key == '3':
            self.start_frontend()
        elif key == '4':
            self.stop_frontend()
        elif key == '5':
            self.start_backend()
            self.start_frontend()
        elif key == '6':
            self.stop_all()
        elif key == '7':
            self.stop_backend()
            time.sleep(1)
            self.start_backend()
        elif key == '8':
            self.stop_frontend()
            time.sleep(1)
            self.start_frontend()
        elif key == '9':
            threading.Thread(target=self.build_frontend, daemon=True).start()
        elif key == 'v':
            views = ["backend", "frontend", "both"]
            current_idx = views.index(self.selected_view)
            self.selected_view = views[(current_idx + 1) % len(views)]
            self.log_scroll = 0
        elif key == 'r':
            threading.Thread(target=self.fetch_dashboard_stats, daemon=True).start()
        elif key.name == 'KEY_UP':
            # Get current log count
            if self.selected_view == "backend":
                log_count = len(self.backend_logs)
            elif self.selected_view == "frontend":
                log_count = len(self.frontend_logs)
            else:
                log_count = len(self.backend_logs) + len(self.frontend_logs)
            
            available_height = self.term.height - 10 - 2
            max_scroll = max(0, log_count - available_height)
            self.log_scroll = min(self.log_scroll + 1, max_scroll)
        elif key.name == 'KEY_DOWN':
            self.log_scroll = max(self.log_scroll - 1, 0)
    
    def cleanup(self):
        """Clean up processes before exit"""
        self.log_message("system", "Shutting down development manager...")
        self.stop_all()
    
    def run(self):
        """Main application loop"""
        with self.term.fullscreen(), self.term.cbreak(), self.term.hidden_cursor():
            self.log_message("system", "Development manager started")
            
            # Initial draw
            self.draw_header()
            self.draw_controls()
            self.draw_logs()
            
            try:
                stats_timer = 0
                last_logs_count = (len(self.backend_logs), len(self.frontend_logs))
                
                while self.running:
                    # Only redraw what has changed
                    self.draw_header()  # Always update header for status changes
                    
                    # Check if logs have changed
                    current_logs_count = (len(self.backend_logs), len(self.frontend_logs))
                    if current_logs_count != last_logs_count or self.log_scroll != 0:
                        self.draw_logs()
                        last_logs_count = current_logs_count
                    
                    # Fetch stats every 10 seconds if backend is running
                    stats_timer += 1
                    if stats_timer >= 20 and self.backend_status == "Running":  # 20 * 0.5s = 10s
                        threading.Thread(target=self.fetch_dashboard_stats, daemon=True).start()
                        stats_timer = 0
                    
                    # Handle input with timeout
                    key = self.term.inkey(timeout=0.5)
                    if key:
                        self.handle_input(key)
                        # Redraw after input handling
                        if key in ['v', '7', '8']:  # View change or restart
                            self.draw_controls()
                            self.draw_logs()
                        
            except KeyboardInterrupt:
                pass
            finally:
                self.cleanup()
                # Terminal context manager will handle cleanup
                print("\nDevelopment manager stopped.")


def main():
    """Entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("""
MakerMatrix Development Server Manager

A TUI application to manage both backend (FastAPI) and frontend (React) servers.

Usage: python dev_manager.py

Controls:
  1-8: Start/stop/restart servers
  v: Switch log view (Backend/Frontend/Both)  
  ↑↓: Scroll through logs
  q: Quit

Requirements:
  - blessed package: pip install blessed
  - Node.js and npm for frontend
  - Python environment with MakerMatrix dependencies
        """)
        return
    
    # Check if blessed is available
    try:
        import blessed
    except ImportError:
        print("Error: 'blessed' package not found.")
        print("Install with: pip install blessed")
        print("Or install dev dependencies: pip install -r requirements-dev.txt")
        sys.exit(1)
    
    manager = ServerManager()
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        manager.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        manager.run()
    except Exception as e:
        print(f"Error: {e}")
        manager.cleanup()


if __name__ == "__main__":
    main()