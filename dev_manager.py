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
        self.backend_logs = deque(maxlen=500)  # Increased for CSV imports with downloads
        self.frontend_logs = deque(maxlen=500)
        self.running = True
        self.backend_status = "Stopped"
        self.frontend_status = "Stopped"
        self.selected_view = "backend"  # backend, frontend, both
        self.log_scroll = 0
        
        # Screen update tracking for better performance
        self.force_redraw = True
        self.last_header_content = ""
        self.last_logs_count = (0, 0)
        
        # URLs
        self.backend_url = "http://192.168.1.57:57891"
        self.frontend_url = "http://localhost:5173"  # Vite's default dev port
        
        # Paths
        self.project_root = Path(__file__).parent
        self.frontend_path = self.project_root / "MakerMatrix" / "frontend"
        self.log_file_path = self.project_root / "server.log"
        
        # Dashboard stats
        self.stats = {
            "parts_count": 0,
            "locations_count": 0,
            "categories_count": 0,
            "users_count": 0,
            "last_updated": None
        }
        self.stats_error = None
        
        # Initialize log file
        self._init_log_file()
    
    def _init_log_file(self):
        """Initialize the log file with a session header"""
        try:
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"MakerMatrix Development Session Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'='*80}\n\n")
        except Exception as e:
            print(f"Warning: Could not initialize log file: {e}")
    
    def _write_to_log_file(self, log_entry: str):
        """Write a log entry to the file"""
        try:
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(f"{log_entry}\n")
                f.flush()  # Ensure immediate write
        except Exception as e:
            # Silently fail to avoid disrupting the terminal UI
            pass
        
    def log_message(self, service: str, message: str, level: str = "INFO"):
        """Add a log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create log entry for display (with emojis)
        if level == "CHANGE":
            display_entry = f"[{timestamp}] [🔄 CHANGE] {message}"
            file_entry = f"[{full_timestamp}] [{service.upper()}] [CHANGE] {message}"
        elif level == "ERROR":
            display_entry = f"[{timestamp}] [❌ ERROR] {message}"
            file_entry = f"[{full_timestamp}] [{service.upper()}] [ERROR] {message}"
        elif level == "WARN":
            display_entry = f"[{timestamp}] [⚠️  WARN] {message}"
            file_entry = f"[{full_timestamp}] [{service.upper()}] [WARN] {message}"
        elif level == "SUCCESS":
            display_entry = f"[{timestamp}] [✅ SUCCESS] {message}"
            file_entry = f"[{full_timestamp}] [{service.upper()}] [SUCCESS] {message}"
        else:
            display_entry = f"[{timestamp}] [{level}] {message}"
            file_entry = f"[{full_timestamp}] [{service.upper()}] [{level}] {message}"
        
        # Write to log file immediately
        self._write_to_log_file(file_entry)
        
        # Add to display logs
        if service == "backend":
            self.backend_logs.append(display_entry)
        elif service == "frontend":
            self.frontend_logs.append(display_entry)
        else:
            # System messages go to both display and file
            system_display = f"[{timestamp}] [SYSTEM] {message}"
            system_file = f"[{full_timestamp}] [SYSTEM] {message}"
            self.backend_logs.append(system_display)
            self.frontend_logs.append(system_display)
            self._write_to_log_file(system_file)
    
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
                    # Update status based on log content - IMPROVED ERROR DETECTION
                    if service == "backend":
                        if "Application startup complete" in line or "Uvicorn running on" in line:
                            self.backend_status = "Running"
                            self.log_message("backend", "Backend started successfully!", "SUCCESS")
                        elif any(critical_error in line.upper() for critical_error in [
                            "CRITICAL", "FATAL", "TRACEBACK", "EXCEPTION"
                        ]) and not any(ignore in line.lower() for ignore in [
                            "printer_config", "printer configuration", "optional"
                        ]):
                            self.backend_status = "Error"
                            self.log_message("backend", f"Critical error detected: {line}", "ERROR")
                        # Don't mark as error for common warnings
                        elif "ERROR" in line.upper() and not any(ignore in line.lower() for ignore in [
                            "printer_config.json", "printer configuration", "loading configuration",
                            "optional", "warning", "not found", "missing config"
                        ]):
                            # Only mark as error if it's a real error, not config warnings
                            if any(real_error in line.lower() for real_error in [
                                "connection", "database", "auth", "permission", "failed to"
                            ]):
                                self.backend_status = "Error"
                    elif service == "frontend":
                        if "Local:" in line and "http://localhost:" in line:
                            self.frontend_status = "Running"
                            self.log_message("frontend", "Frontend started successfully!", "SUCCESS")
                            # Extract the actual URL
                            try:
                                port_match = re.search(r'http://localhost:(\d+)', line)
                                if port_match:
                                    port = port_match.group(1)
                                    self.frontend_url = f"http://localhost:{port}"
                            except:
                                pass
                        elif any(error_indicator in line for error_indicator in [
                            "Failed to compile", "Module not found", "SyntaxError", "TypeError"
                        ]):
                            self.frontend_status = "Error"
                        # Detect file changes and HMR events
                        elif any(keyword in line.lower() for keyword in [
                            "hmr update", "page reload", "file changed", "rebuilding", 
                            "reloading", "full reload", "hot updated", "[vite] hot update",
                            "src updated", "hmr", "hot reloaded"
                        ]):
                            self.log_message("frontend", f"🔄 HMR: {line}", "CHANGE")
                            continue  # Don't log HMR messages twice
                    
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
            for line in iter(build_process.stdout.readline, ''):
                if not line:
                    break
                line = line.strip()
                if line:
                    self.log_message("frontend", f"BUILD: {line}")
            
            # Wait for build to complete
            return_code = build_process.wait()
            
            if return_code == 0:
                self.log_message("frontend", "✅ Frontend build completed successfully!", "SUCCESS")
                self.log_message("frontend", "📦 Production build is ready in MakerMatrix/frontend/dist/", "INFO")
            else:
                self.log_message("frontend", f"❌ Frontend build failed with code {return_code}", "ERROR")
                
        except Exception as e:
            self.log_message("frontend", f"Failed to build frontend: {e}", "ERROR")
    
    def get_status_color(self, status: str):
        """Get color for status display"""
        colors = {
            "Running": self.term.bright_green,
            "Starting": self.term.bright_yellow,
            "Stopped": self.term.bright_red,
            "Failed": self.term.bright_red,
            "Error": self.term.bright_red
        }
        return colors.get(status, self.term.white)
    
    def get_status_symbol(self, status: str):
        """Get symbol for status display"""
        symbols = {
            "Running": "🟢",
            "Starting": "🟡", 
            "Stopped": "🔴",
            "Failed": "❌",
            "Error": "⚠️"
        }
        return symbols.get(status, "⚪")
    
    def fetch_dashboard_stats(self):
        """Fetch dashboard statistics from the backend API"""
        if self.backend_status != "Running":
            return
            
        try:
            # Use the utility endpoint to get all counts in one call
            response = requests.get(f"{self.backend_url}/utility/get_counts", timeout=3)
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
                    except Exception:
                        stats["users_count"] = "N/A"
                    
                    # Update stats
                    self.stats.update(stats)
                    self.stats_error = None
                else:
                    self.stats_error = "Invalid API response"
            else:
                self.stats_error = f"API Error {response.status_code}"
                
        except requests.exceptions.ConnectionError:
            self.stats_error = "Backend not reachable"
        except requests.exceptions.Timeout:
            self.stats_error = "API timeout"
        except Exception as e:
            self.stats_error = f"API Error: {str(e)[:25]}..."
    
    def get_header_content(self):
        """Generate header content for comparison"""
        backend_color = self.get_status_color(self.backend_status)
        frontend_color = self.get_status_color(self.frontend_status)
        backend_symbol = self.get_status_symbol(self.backend_status)
        frontend_symbol = self.get_status_symbol(self.frontend_status)
        
        status_line = (f"{backend_symbol} Backend: {backend_color}{self.backend_status}{self.term.normal} "
                      f"({self.backend_url}) | "
                      f"{frontend_symbol} Frontend: {frontend_color}{self.frontend_status}{self.term.normal} "
                      f"({self.frontend_url})")
        
        if self.stats_error:
            stats_line = f"📊 Dashboard: {self.term.red}{self.stats_error}{self.term.normal}"
        elif self.stats["last_updated"]:
            stats_line = (f"📊 Parts: {self.term.cyan}{self.stats['parts_count']}{self.term.normal} | "
                         f"Locations: {self.term.cyan}{self.stats['locations_count']}{self.term.normal} | "
                         f"Categories: {self.term.cyan}{self.stats['categories_count']}{self.term.normal} | "
                         f"Users: {self.term.cyan}{self.stats['users_count']}{self.term.normal} | "
                         f"Updated: {self.term.yellow}{self.stats['last_updated']}{self.term.normal}")
        else:
            stats_line = f"📊 Dashboard: {self.term.yellow}Waiting for backend...{self.term.normal}"
        
        return status_line + "\n" + stats_line
    
    def draw_header(self):
        """Draw the header section only if changed"""
        new_header_content = self.get_header_content()
        if new_header_content != self.last_header_content or self.force_redraw:
            with self.term.location(0, 0):
                print(self.term.clear_eol + self.term.bold + self.term.bright_blue + 
                      "🚀 MakerMatrix Development Manager" + self.term.normal)
            
            with self.term.location(0, 1):
                print(self.term.clear_eol + "─" * min(self.term.width, 100))
            
            # Status and stats lines
            lines = new_header_content.split('\n')
            for i, line in enumerate(lines):
                with self.term.location(0, 2 + i):
                    print(self.term.clear_eol + line)
            
            self.last_header_content = new_header_content
    
    def draw_controls(self):
        """Draw the controls section"""
        if not self.force_redraw:
            return
            
        y = 5
        with self.term.location(0, y):
            print(self.term.clear_eol + self.term.bold + self.term.bright_cyan + "Controls:" + self.term.normal)
        
        controls = [
            f"{self.term.green}1{self.term.normal}: Start Backend  {self.term.green}2{self.term.normal}: Stop Backend   {self.term.green}3{self.term.normal}: Start Frontend  {self.term.green}4{self.term.normal}: Stop Frontend",
            f"{self.term.green}5{self.term.normal}: Start Both     {self.term.green}6{self.term.normal}: Stop Both      {self.term.green}7{self.term.normal}: Restart Backend {self.term.green}8{self.term.normal}: Restart Frontend", 
            f"{self.term.green}9{self.term.normal}: Build Frontend  {self.term.green}v{self.term.normal}: Switch View    {self.term.green}r{self.term.normal}: Refresh Stats   {self.term.green}↑↓{self.term.normal}: Scroll  {self.term.green}PgUp/PgDn{self.term.normal}: Fast Scroll  {self.term.green}q{self.term.normal}: Quit"
        ]
        
        for i, control in enumerate(controls):
            with self.term.location(0, y + 1 + i):
                print(self.term.clear_eol + control)
    
    def draw_logs(self):
        """Draw the logs section only if changed"""
        log_start_y = 10
        available_height = max(5, self.term.height - log_start_y - 2)
        
        # Check if logs changed - always update if scroll position changed
        current_logs_count = (len(self.backend_logs), len(self.frontend_logs))
        if current_logs_count == self.last_logs_count and not self.force_redraw:
            return
        
        with self.term.location(0, log_start_y - 1):
            view_indicator = f"📋 View: {self.term.bright_magenta}{self.selected_view.title()}{self.term.normal}"
            
            # Add scroll indicator
            if self.selected_view == "backend":
                total_logs = len(self.backend_logs)
            elif self.selected_view == "frontend":
                total_logs = len(self.frontend_logs)
            else:
                total_logs = len(self.backend_logs) + len(self.frontend_logs)
            
            if total_logs > available_height:
                scroll_indicator = f" {self.term.yellow}[{self.log_scroll}/{max(0, total_logs - available_height)}]{self.term.normal}"
            else:
                scroll_indicator = ""
            
            separator_len = max(0, (min(self.term.width, 100) - len(view_indicator) - len(scroll_indicator.replace(self.term.yellow, '').replace(self.term.normal, ''))) // 2 - 2)
            separator = "─" * separator_len
            print(self.term.clear_eol + separator + f" {view_indicator}{scroll_indicator} " + separator)
        
        # Get logs based on selected view
        if self.selected_view == "backend":
            logs = list(self.backend_logs)
        elif self.selected_view == "frontend":
            logs = list(self.frontend_logs)
        else:  # both
            # Interleave logs by timestamp
            backend_logs = [(log, "B") for log in self.backend_logs]
            frontend_logs = [(log, "F") for log in self.frontend_logs]
            all_logs = backend_logs + frontend_logs
            all_logs.sort(key=lambda x: x[0][:8] if len(x[0]) > 8 else x[0])
            logs = [f"[{self.term.blue if source == 'B' else self.term.green}{source}{self.term.normal}] {log}" 
                   for log, source in all_logs]
        
        # Apply scroll offset
        start_idx = max(0, len(logs) - available_height + self.log_scroll)
        visible_logs = logs[start_idx:start_idx + available_height]
        
        # Clear log area and draw logs
        for i in range(available_height):
            with self.term.location(0, log_start_y + i):
                if i < len(visible_logs):
                    log_line = visible_logs[i]
                    # Don't truncate - show full error messages
                    print(self.term.clear_eol + log_line)
                else:
                    print(self.term.clear_eol)
        
        self.last_logs_count = current_logs_count
    
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
            self.force_redraw = True
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
            
            available_height = max(5, self.term.height - 10 - 2)
            max_scroll = max(0, log_count - available_height)
            self.log_scroll = min(self.log_scroll + 1, max_scroll)
        elif key.name == 'KEY_DOWN':
            self.log_scroll = max(self.log_scroll - 1, 0)
        elif key.name == 'KEY_PGUP':
            # Page up - scroll up by half screen
            if self.selected_view == "backend":
                log_count = len(self.backend_logs)
            elif self.selected_view == "frontend":
                log_count = len(self.frontend_logs)
            else:
                log_count = len(self.backend_logs) + len(self.frontend_logs)
            
            available_height = max(5, self.term.height - 10 - 2)
            max_scroll = max(0, log_count - available_height)
            page_size = max(1, available_height // 2)
            self.log_scroll = min(self.log_scroll + page_size, max_scroll)
        elif key.name == 'KEY_PGDN':
            # Page down - scroll down by half screen
            available_height = max(5, self.term.height - 10 - 2)
            page_size = max(1, available_height // 2)
            self.log_scroll = max(self.log_scroll - page_size, 0)
    
    def cleanup(self):
        """Clean up processes before exit"""
        self.log_message("system", "Shutting down development manager...")
        self.stop_all()
    
    def run(self):
        """Main application loop with improved input handling"""
        with self.term.fullscreen(), self.term.cbreak(), self.term.hidden_cursor():
            self.log_message("system", "Development manager started")
            
            # Initial draw
            self.force_redraw = True
            self.draw_header()
            self.draw_controls()
            self.draw_logs()
            self.force_redraw = False
            
            try:
                stats_timer = 0
                
                while self.running:
                    # Update display components
                    self.draw_header()
                    self.draw_logs()
                    
                    # Fetch stats every 10 seconds if backend is running
                    stats_timer += 1
                    if stats_timer >= 40 and self.backend_status == "Running":  # 40 * 0.25s = 10s
                        threading.Thread(target=self.fetch_dashboard_stats, daemon=True).start()
                        stats_timer = 0
                    
                    # IMPROVED INPUT HANDLING - much more responsive
                    key = self.term.inkey(timeout=0.25)  # Reduced timeout for better responsiveness
                    if key:
                        self.handle_input(key)
                        
            except KeyboardInterrupt:
                pass
            finally:
                self.cleanup()
                print("\n🔧 Development manager stopped.")


def main():
    """Entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("""
🚀 MakerMatrix Development Server Manager

A TUI application to manage both backend (FastAPI) and frontend (React) servers.

Usage: python dev_manager.py

Controls:
  1-8: Start/stop/restart servers
  v: Switch log view (Backend/Frontend/Both)  
  ↑↓: Scroll through logs
  r: Refresh dashboard stats
  q: Quit

Features:
  • Real-time server status monitoring
  • Dashboard statistics display
  • Color-coded log messages
  • Responsive keyboard input
  • Production build support

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
        print("❌ Error: 'blessed' package not found.")
        print("📦 Install with: pip install blessed")
        print("📦 Or install dev dependencies: pip install -r requirements-dev.txt")
        sys.exit(1)
    
    manager = ServerManager()
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        manager.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        manager.run()
    except Exception as e:
        print(f"❌ Error: {e}")
        manager.cleanup()


if __name__ == "__main__":
    main()