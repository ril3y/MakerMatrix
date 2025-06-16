#!/usr/bin/env python3
"""
MakerMatrix Development Server Manager - Enhanced Version
A responsive TUI application to manage both backend and frontend development servers
"""

import asyncio
import json
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

import requests
from blessed import Terminal


class LogEntry:
    """Enhanced log entry with metadata"""
    def __init__(self, service: str, message: str, level: str = "INFO", timestamp: datetime = None):
        self.service = service
        self.message = message
        self.level = level
        self.timestamp = timestamp or datetime.now()
        self.full_timestamp = self.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        self.display_timestamp = self.timestamp.strftime("%H:%M:%S")
        
    def get_display_line(self, show_service=False):
        """Get formatted line for display"""
        level_symbols = {
            "CHANGE": "🔄",
            "ERROR": "❌", 
            "WARN": "⚠️",
            "SUCCESS": "✅",
            "INFO": "ℹ️",
            "DEBUG": "🔍"
        }
        
        symbol = level_symbols.get(self.level, "📝")
        service_prefix = f"[{self.service.upper()}] " if show_service else ""
        return f"[{self.display_timestamp}] {symbol} {service_prefix}{self.message}"
    
    def get_file_line(self):
        """Get formatted line for file logging"""
        return f"[{self.full_timestamp}] [{self.service.upper()}] [{self.level}] {self.message}"


class EnhancedServerManager:
    def __init__(self):
        self.term = Terminal()
        self.backend_process: Optional[subprocess.Popen] = None
        self.frontend_process: Optional[subprocess.Popen] = None
        
        # Enhanced log storage - much larger buffers
        self.backend_logs = deque(maxlen=2000)
        self.frontend_logs = deque(maxlen=2000)
        self.all_logs = deque(maxlen=5000)  # Combined chronological log
        
        self.running = True
        self.backend_status = "Stopped"
        self.frontend_status = "Stopped"
        self.selected_view = "all"  # backend, frontend, all, errors
        
        # Enhanced scrolling
        self.scroll_position = 0
        self.search_term = ""
        self.search_mode = False
        self.filtered_logs = []
        
        # Performance tracking
        self.force_redraw = True
        self.last_display_hash = ""
        self.last_logs_count = 0
        
        # URLs and paths - updated for network access
        self.local_ip = self._get_local_ip()
        self.backend_url = f"http://{self.local_ip}:57891"
        self.frontend_url = f"http://{self.local_ip}:5173"
        self.project_root = Path(__file__).parent
        self.frontend_path = self.project_root / "MakerMatrix" / "frontend"
        self.log_file_path = self.project_root / "dev_manager.log"
        
        # Dashboard stats - removed user authentication
        self.stats = {
            "parts_count": 0,
            "locations_count": 0,
            "categories_count": 0,
            "last_updated": None
        }
        self.stats_error = None
        
        # Threading locks
        self.log_lock = threading.RLock()
        
        # Initialize enhanced logging
        self._init_log_file()
        self.log_message("system", f"Enhanced Development Manager initialized on {self.local_ip}", "SUCCESS")
    
    def _get_local_ip(self):
        """Get the local IP address for network access"""
        try:
            # Connect to a remote address to determine the local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "localhost"
    
    def _init_log_file(self):
        """Initialize the log file with session header"""
        try:
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"MakerMatrix Development Session Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'='*80}\n\n")
        except Exception as e:
            print(f"Warning: Could not initialize log file: {e}")
    
    def _write_to_log_file(self, log_entry: LogEntry):
        """Write a log entry to the file"""
        try:
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(f"{log_entry.get_file_line()}\n")
                f.flush()
        except Exception:
            pass  # Silently fail to avoid disrupting UI
    
    def log_message(self, service: str, message: str, level: str = "INFO"):
        """Enhanced log message handling"""
        with self.log_lock:
            log_entry = LogEntry(service, message, level)
            
            # Write to file immediately
            self._write_to_log_file(log_entry)
            
            # Add to appropriate log buffers
            if service == "backend":
                self.backend_logs.append(log_entry)
            elif service == "frontend":
                self.frontend_logs.append(log_entry)
            elif service == "system":
                self.backend_logs.append(log_entry)
                self.frontend_logs.append(log_entry)
            
            # Add to combined chronological log
            self.all_logs.append(log_entry)
            
            # Update filtered logs if search is active
            if self.search_term:
                self._update_filtered_logs()
    
    def _update_filtered_logs(self):
        """Update filtered logs based on current search term"""
        if not self.search_term:
            self.filtered_logs = []
            return
            
        search_lower = self.search_term.lower()
        self.filtered_logs = []
        
        for log_entry in self.all_logs:
            if (search_lower in log_entry.message.lower() or 
                search_lower in log_entry.service.lower() or
                search_lower in log_entry.level.lower()):
                self.filtered_logs.append(log_entry)
    
    def start_backend(self):
        """Start the FastAPI backend server"""
        try:
            if self.backend_process and self.backend_process.poll() is None:
                self.log_message("backend", "Backend already running", "WARN")
                return
            
            self.log_message("backend", "Starting FastAPI backend server...", "INFO")
            
            # Use venv_test Python if available
            venv_python = self.project_root / "venv_test" / "bin" / "python"
            python_exe = str(venv_python) if venv_python.exists() else sys.executable
            
            self.backend_process = subprocess.Popen(
                [python_exe, "-m", "uvicorn", "MakerMatrix.main:app", "--host", "0.0.0.0", "--port", "57891", "--reload"],
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=0  # Unbuffered for real-time logs
            )
            
            # Start enhanced log monitoring
            threading.Thread(
                target=self._monitor_process_output,
                args=(self.backend_process, "backend"),
                daemon=True,
                name="Backend-Monitor"
            ).start()
            
            self.backend_status = "Starting"
            self.log_message("backend", f"Backend PID: {self.backend_process.pid}", "INFO")
            
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
            
            self.log_message("frontend", "Starting React development server...", "INFO")
            
            self.frontend_process = subprocess.Popen(
                ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"],
                cwd=self.frontend_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=0  # Unbuffered for real-time logs
            )
            
            # Start enhanced log monitoring
            threading.Thread(
                target=self._monitor_process_output,
                args=(self.frontend_process, "frontend"),
                daemon=True,
                name="Frontend-Monitor"
            ).start()
            
            self.frontend_status = "Starting"
            self.log_message("frontend", f"Frontend PID: {self.frontend_process.pid}", "INFO")
            
        except Exception as e:
            self.log_message("frontend", f"Failed to start frontend: {e}", "ERROR")
            self.frontend_status = "Failed"
    
    def _monitor_process_output(self, process: subprocess.Popen, service: str):
        """Enhanced process output monitoring with better error detection"""
        try:
            while process.poll() is None:
                line = process.stdout.readline()
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                # Enhanced status detection
                if service == "backend":
                    if "Application startup complete" in line or "Uvicorn running on" in line:
                        self.backend_status = "Running"
                        self.log_message("backend", "Backend started successfully!", "SUCCESS")
                    elif any(error in line.upper() for error in ["CRITICAL", "FATAL", "TRACEBACK"]):
                        if not any(ignore in line.lower() for ignore in ["printer_config", "optional"]):
                            self.backend_status = "Error"
                            self.log_message("backend", f"Critical error: {line}", "ERROR")
                            continue
                    elif "ERROR" in line.upper():
                        if any(real_error in line.lower() for real_error in ["connection", "database", "auth", "failed to"]):
                            if not any(ignore in line.lower() for ignore in ["printer_config", "optional", "not found"]):
                                self.backend_status = "Error"
                
                elif service == "frontend":
                    if "Local:" in line and "http://" in line:
                        self.frontend_status = "Running"
                        self.log_message("frontend", "Frontend started successfully!", "SUCCESS")
                        # Extract URL and find network URL
                        try:
                            if "Network:" in line:
                                network_match = re.search(r'http://([0-9.]+):(\d+)', line)
                                if network_match:
                                    self.frontend_url = f"http://{network_match.group(1)}:{network_match.group(2)}"
                            else:
                                port_match = re.search(r'http://[^:]+:(\d+)', line)
                                if port_match:
                                    self.frontend_url = f"http://0.0.0.0:{port_match.group(1)}"
                        except:
                            pass
                    elif any(error in line for error in ["Failed to compile", "Module not found", "SyntaxError"]):
                        self.frontend_status = "Error"
                    elif any(keyword in line.lower() for keyword in ["hmr update", "file changed", "rebuilding", "hot update"]):
                        self.log_message("frontend", f"🔄 HMR: {line}", "CHANGE")
                        continue
                
                # Determine log level with enhanced error detection
                level = "INFO"
                line_upper = line.upper()
                line_lower = line.lower()
                
                # Check for success patterns first (these override error detection)
                if any(success in line_lower for success in ["success", "completed", "started", "ready", "connected"]):
                    level = "SUCCESS"
                # Check for specific success patterns that mention "failed" but are actually success messages
                elif "import completed" in line_lower and ("success" in line_lower or "failed" in line_lower):
                    level = "SUCCESS"
                elif any(error in line_upper for error in ["ERROR", "FAILED", "EXCEPTION", "CRITICAL", "FATAL", "TRACEBACK"]):
                    level = "ERROR"
                elif any(warn in line_upper for warn in ["WARN", "WARNING", "DEPRECATED"]):
                    level = "WARN"
                
                self.log_message(service, line, level)
                
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
            self.log_message("backend", "Stopping backend server...", "INFO")
            self.backend_process.terminate()
            try:
                self.backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.backend_process.kill()
                self.log_message("backend", "Backend force killed", "WARN")
            self.backend_status = "Stopped"
        else:
            self.log_message("backend", "Backend not running", "WARN")
    
    def stop_frontend(self):
        """Stop the frontend server"""
        if self.frontend_process and self.frontend_process.poll() is None:
            self.log_message("frontend", "Stopping frontend server...", "INFO")
            self.frontend_process.terminate()
            try:
                self.frontend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.frontend_process.kill()
                self.log_message("frontend", "Frontend force killed", "WARN")
            self.frontend_status = "Stopped"
        else:
            self.log_message("frontend", "Frontend not running", "WARN")
    
    def stop_all(self):
        """Stop both servers"""
        self.stop_backend()
        self.stop_frontend()
    
    def restart_backend(self):
        """Restart backend server"""
        self.stop_backend()
        time.sleep(1)
        self.start_backend()
    
    def restart_frontend(self):
        """Restart frontend server"""
        self.stop_frontend()
        time.sleep(1)
        self.start_frontend()
    
    def build_frontend(self):
        """Build frontend for production"""
        try:
            if not self.frontend_path.exists():
                self.log_message("frontend", f"Frontend path not found: {self.frontend_path}", "ERROR")
                return
            
            self.log_message("frontend", "Building frontend for production...", "INFO")
            
            # Stop dev server if running
            if self.frontend_process and self.frontend_process.poll() is None:
                self.log_message("frontend", "Stopping dev server before build...", "INFO")
                self.stop_frontend()
                time.sleep(2)
            
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
                    level = "ERROR" if "error" in line.lower() else "INFO"
                    self.log_message("frontend", f"BUILD: {line}", level)
            
            return_code = build_process.wait()
            
            if return_code == 0:
                self.log_message("frontend", "✅ Frontend build completed successfully!", "SUCCESS")
                self.log_message("frontend", "📦 Production build ready in MakerMatrix/frontend/dist/", "INFO")
            else:
                self.log_message("frontend", f"❌ Frontend build failed with code {return_code}", "ERROR")
                
        except Exception as e:
            self.log_message("frontend", f"Failed to build frontend: {e}", "ERROR")
    
    def fetch_dashboard_stats(self):
        """Fetch dashboard statistics (removed user authentication)"""
        if self.backend_status != "Running":
            return
            
        try:
            # Get basic counts - use localhost for internal API calls
            api_url = "http://localhost:57891/utility/get_counts"
            response = requests.get(api_url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success" and "data" in data:
                    counts_data = data["data"]
                    self.stats.update({
                        "parts_count": counts_data.get("parts", 0),
                        "locations_count": counts_data.get("locations", 0),
                        "categories_count": counts_data.get("categories", 0),
                        "last_updated": datetime.now().strftime("%H:%M:%S")
                    })
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
    
    def get_current_logs(self) -> List[LogEntry]:
        """Get current logs based on view and search"""
        if self.search_term and self.filtered_logs:
            return self.filtered_logs
        
        if self.selected_view == "backend":
            return list(self.backend_logs)
        elif self.selected_view == "frontend":
            return list(self.frontend_logs)
        elif self.selected_view == "errors":
            # Filter all logs to show only errors and warnings
            error_logs = []
            for log_entry in self.all_logs:
                if log_entry.level in ["ERROR", "WARN", "CRITICAL", "FATAL"]:
                    error_logs.append(log_entry)
            return error_logs
        else:  # all
            return list(self.all_logs)
    
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
    
    def draw_header(self):
        """Draw enhanced header"""
        with self.term.location(0, 0):
            print(self.term.clear_eol + self.term.bold + self.term.bright_blue + 
                  "🚀 MakerMatrix Development Manager [ENHANCED]" + self.term.normal)
        
        with self.term.location(0, 1):
            print(self.term.clear_eol + "─" * min(self.term.width, 120))
        
        # Status line
        backend_color = self.get_status_color(self.backend_status)
        frontend_color = self.get_status_color(self.frontend_status)
        backend_symbol = self.get_status_symbol(self.backend_status)
        frontend_symbol = self.get_status_symbol(self.frontend_status)
        
        status_line = (f"{backend_symbol} Backend: {backend_color}{self.backend_status}{self.term.normal} "
                      f"({self.backend_url}) | "
                      f"{frontend_symbol} Frontend: {frontend_color}{self.frontend_status}{self.term.normal} "
                      f"({self.frontend_url})")
        
        with self.term.location(0, 2):
            print(self.term.clear_eol + status_line)
        
        # Stats line
        if self.stats_error:
            stats_line = f"📊 Dashboard: {self.term.red}{self.stats_error}{self.term.normal}"
        elif self.stats["last_updated"]:
            stats_line = (f"📊 Parts: {self.term.cyan}{self.stats['parts_count']}{self.term.normal} | "
                         f"Locations: {self.term.cyan}{self.stats['locations_count']}{self.term.normal} | "
                         f"Categories: {self.term.cyan}{self.stats['categories_count']}{self.term.normal} | "
                         f"Updated: {self.term.yellow}{self.stats['last_updated']}{self.term.normal}")
        else:
            stats_line = f"📊 Dashboard: {self.term.yellow}Waiting for backend...{self.term.normal}"
        
        with self.term.location(0, 3):
            print(self.term.clear_eol + stats_line)
    
    def draw_controls(self):
        """Draw enhanced controls"""
        y = 5
        with self.term.location(0, y):
            print(self.term.clear_eol + self.term.bold + self.term.bright_cyan + "Controls:" + self.term.normal)
        
        controls = [
            f"{self.term.green}1{self.term.normal}:Start Backend  {self.term.green}2{self.term.normal}:Stop Backend   {self.term.green}3{self.term.normal}:Start Frontend  {self.term.green}4{self.term.normal}:Stop Frontend  {self.term.green}5{self.term.normal}:Both",
            f"{self.term.green}6{self.term.normal}:Stop All      {self.term.green}7{self.term.normal}:Restart BE     {self.term.green}8{self.term.normal}:Restart FE      {self.term.green}9{self.term.normal}:Build Frontend",
            f"{self.term.green}v{self.term.normal}:Switch View   {self.term.green}e{self.term.normal}:Errors Only    {self.term.green}r{self.term.normal}:Refresh Stats  {self.term.green}c{self.term.normal}:Clear Logs     {self.term.green}s{self.term.normal}:Search",
            f"{self.term.green}↑↓/jk{self.term.normal}:Scroll     {self.term.green}PgUp/PgDn{self.term.normal}:Fast     {self.term.green}Home/End{self.term.normal}:Top/Bottom  {self.term.green}Esc{self.term.normal}:Exit Search {self.term.green}q{self.term.normal}:Quit"
        ]
        
        for i, control in enumerate(controls):
            with self.term.location(0, y + 1 + i):
                print(self.term.clear_eol + control)
    
    def draw_logs(self):
        """Draw enhanced logs with better scrolling"""
        log_start_y = 11
        available_height = max(5, self.term.height - log_start_y - 2)
        
        # View and search indicators
        with self.term.location(0, log_start_y - 1):
            view_color = self.term.bright_magenta
            if self.selected_view == "errors":
                view_indicator = f"⚠️ View: {self.term.bright_red}{self.selected_view.title()}{self.term.normal}"
            else:
                view_indicator = f"📋 View: {view_color}{self.selected_view.title()}{self.term.normal}"
            
            if self.search_mode:
                search_indicator = f" | 🔍 Search: {self.term.bright_yellow}{self.search_term}_{self.term.normal}"
            elif self.search_term:
                search_indicator = f" | 🔍 Filter: {self.term.bright_yellow}{self.search_term}{self.term.normal} ({len(self.filtered_logs)} results)"
            else:
                search_indicator = ""
            
            logs = self.get_current_logs()
            if logs and available_height > 0:
                max_scroll = max(0, len(logs) - available_height)
                scroll_indicator = f" | Scroll: {self.term.yellow}{self.scroll_position}/{max_scroll}{self.term.normal}"
            else:
                scroll_indicator = ""
            
            separator_len = max(0, min(self.term.width, 120) - len(view_indicator) - 30) // 2
            separator = "─" * separator_len
            print(self.term.clear_eol + separator + f" {view_indicator}{search_indicator}{scroll_indicator} " + separator)
        
        # Display logs
        logs = self.get_current_logs()
        if not logs:
            with self.term.location(0, log_start_y):
                print(self.term.clear_eol + self.term.dim + "No logs available..." + self.term.normal)
            return
        
        # Calculate visible range - fixed scrolling logic
        # scroll_position = 0 means show newest logs (bottom)
        # scroll_position > 0 means scroll up to see older logs
        total_logs = len(logs)
        if total_logs <= available_height:
            # All logs fit on screen
            visible_logs = logs
        else:
            # Calculate start index based on scroll position
            # When scroll_position = 0, show the newest logs (end of list)
            # When scroll_position increases, show older logs (earlier in list)
            start_idx = max(0, total_logs - available_height - self.scroll_position)
            end_idx = start_idx + available_height
            visible_logs = logs[start_idx:end_idx]
        
        # Display logs
        for i in range(available_height):
            with self.term.location(0, log_start_y + i):
                if i < len(visible_logs):
                    log_entry = visible_logs[i]
                    show_service = self.selected_view == "all"
                    display_line = log_entry.get_display_line(show_service)
                    
                    # Highlight search terms
                    if self.search_term and self.search_term.lower() in display_line.lower():
                        display_line = display_line.replace(
                            self.search_term, 
                            f"{self.term.black_on_yellow}{self.search_term}{self.term.normal}"
                        )
                    
                    # Truncate if too long
                    if len(display_line) > self.term.width:
                        display_line = display_line[:self.term.width-3] + "..."
                    
                    print(self.term.clear_eol + display_line)
                else:
                    print(self.term.clear_eol)
    
    def clear_logs(self):
        """Clear all logs"""
        with self.log_lock:
            self.backend_logs.clear()
            self.frontend_logs.clear()
            self.all_logs.clear()
            self.filtered_logs.clear()
            self.scroll_position = 0
        self.log_message("system", "Logs cleared", "INFO")
    
    def handle_input(self, key):
        """Enhanced input handling"""
        if self.search_mode:
            # Search mode input handling
            if key.name == 'KEY_ESCAPE':
                self.search_mode = False
            elif key.name == 'KEY_ENTER':
                self.search_mode = False
                self._update_filtered_logs()
                self.scroll_position = 0
            elif key.name == 'KEY_BACKSPACE':
                self.search_term = self.search_term[:-1]
            elif key and len(key) == 1 and key.isprintable():
                self.search_term += key
            return
        
        # Normal mode input handling
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
            threading.Thread(target=self.restart_backend, daemon=True).start()
        elif key == '8':
            threading.Thread(target=self.restart_frontend, daemon=True).start()
        elif key == '9':
            threading.Thread(target=self.build_frontend, daemon=True).start()
        elif key == 'v':
            views = ["all", "backend", "frontend", "errors"]
            current_idx = views.index(self.selected_view)
            self.selected_view = views[(current_idx + 1) % len(views)]
            self.scroll_position = 0
            self.search_term = ""
            self.filtered_logs = []
        elif key == 'e':
            # Quick shortcut to errors view
            self.selected_view = "errors"
            self.scroll_position = 0
            self.search_term = ""
            self.filtered_logs = []
        elif key == 'r':
            threading.Thread(target=self.fetch_dashboard_stats, daemon=True).start()
        elif key == 'c':
            self.clear_logs()
        elif key == 's':
            self.search_mode = True
            self.search_term = ""
        elif key.name == 'KEY_ESCAPE':
            self.search_term = ""
            self.filtered_logs = []
            self.scroll_position = 0
        elif key.name == 'KEY_UP' or key == 'k':  # Also support 'k' for vim-like scrolling
            logs = self.get_current_logs()
            available_height = max(5, self.term.height - 11 - 2)
            max_scroll = max(0, len(logs) - available_height)
            self.scroll_position = min(self.scroll_position + 1, max_scroll)
        elif key.name == 'KEY_DOWN' or key == 'j':  # Also support 'j' for vim-like scrolling
            self.scroll_position = max(self.scroll_position - 1, 0)
        elif key.name == 'KEY_PGUP':
            logs = self.get_current_logs()
            available_height = max(5, self.term.height - 11 - 2)
            max_scroll = max(0, len(logs) - available_height)
            page_size = max(1, available_height // 2)
            self.scroll_position = min(self.scroll_position + page_size, max_scroll)
        elif key.name == 'KEY_PGDN':
            available_height = max(5, self.term.height - 11 - 2)
            page_size = max(1, available_height // 2)
            self.scroll_position = max(self.scroll_position - page_size, 0)
        elif key.name == 'KEY_HOME':
            logs = self.get_current_logs()
            available_height = max(5, self.term.height - 11 - 2)
            self.scroll_position = max(0, len(logs) - available_height)
        elif key.name == 'KEY_END':
            self.scroll_position = 0
    
    def cleanup(self):
        """Enhanced cleanup"""
        self.log_message("system", "Shutting down enhanced development manager...", "INFO")
        self.stop_all()
        
        # Write final session info to log file
        try:
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(f"\nSession ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total logs captured: {len(self.all_logs)}\n")
                f.write("="*80 + "\n\n")
        except Exception:
            pass
    
    def run(self):
        """Enhanced main loop with better performance"""
        with self.term.fullscreen(), self.term.cbreak(), self.term.hidden_cursor():
            self.log_message("system", "Enhanced Development Manager started", "SUCCESS")
            
            try:
                stats_timer = 0
                refresh_counter = 0
                
                while self.running:
                    # Only redraw when necessary
                    if refresh_counter % 4 == 0 or self.force_redraw:  # Every ~1 second
                        self.draw_header()
                        self.draw_controls()
                        self.force_redraw = False
                    
                    # Always update logs (most dynamic part)
                    self.draw_logs()
                    
                    # Fetch stats periodically
                    stats_timer += 1
                    if stats_timer >= 40 and self.backend_status == "Running":  # Every ~10 seconds
                        threading.Thread(target=self.fetch_dashboard_stats, daemon=True).start()
                        stats_timer = 0
                    
                    # Very responsive input handling
                    key = self.term.inkey(timeout=0.1)
                    if key:
                        self.handle_input(key)
                        self.force_redraw = True
                    
                    refresh_counter += 1
                    
            except KeyboardInterrupt:
                pass
            finally:
                self.cleanup()
                print("\n🔧 Enhanced Development Manager stopped.")


def main():
    """Entry point with enhanced help"""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("""
🚀 MakerMatrix Development Server Manager [ENHANCED]

A highly responsive TUI application to manage both backend (FastAPI) and frontend (React) servers.

Usage: python dev_manager.py

🎮 Controls:
  1-4: Start/stop individual servers    5: Start both servers
  6: Stop all servers                   7-8: Restart servers  
  9: Build frontend for production      
  
  v: Switch log view (All/Backend/Frontend/Errors)
  e: Quick jump to Errors Only view    r: Refresh dashboard stats
  c: Clear all logs                     s: Enter search mode
  ESC: Exit search/clear filter         q: Quit application
  
  ↑↓: Scroll through logs               PgUp/PgDn: Fast scroll
  Home: Jump to oldest logs             End: Jump to newest logs

🚀 Enhanced Features:
  • Real-time server status monitoring with better error detection
  • Enhanced log management with 5000+ entry buffer
  • Advanced search and filtering capabilities  
  • Errors Only view (press 'e') for quick debugging
  • Improved scrolling with Home/End navigation
  • Better performance with selective screen updates
  • Comprehensive file logging with timestamps
  • No authentication requirements for API calls
  • Color-coded log levels and HMR detection

📋 Requirements:
  - blessed package: pip install blessed
  - Node.js and npm for frontend
  - Python environment with MakerMatrix dependencies

📁 Logs saved to: dev_manager.log
        """)
        return
    
    # Check dependencies
    try:
        import blessed
        import requests
    except ImportError as e:
        print(f"❌ Error: Missing dependency: {e}")
        print("📦 Install with: pip install blessed requests")
        sys.exit(1)
    
    manager = EnhancedServerManager()
    
    # Graceful shutdown handling
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