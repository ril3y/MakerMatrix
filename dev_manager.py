#!/usr/bin/env python3
"""
MakerMatrix Development Server Manager - Rich TUI Version
A responsive TUI application to manage both backend and frontend development servers using Rich.

Also exposes a lightweight HTTP control API (defaults to http://127.0.0.1:8765)
for automated agents or LLMs to start, stop, and monitor the dev services.
"""

import asyncio
import json
import os
import psutil
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
from typing import Optional, Dict, List, Any

import requests
from blessed import Terminal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.markup import escape
from urllib.parse import urlparse, parse_qs

# File watching for auto-restart
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True

    class DebouncedRestartHandler(FileSystemEventHandler):
        """A debounced file system event handler to trigger restarts."""
        def __init__(self, manager, service_name, file_extensions, restart_function, status_checker, enabled_checker):
            self.manager = manager
            self.service_name = service_name
            self.file_extensions = file_extensions
            self.restart_function = restart_function
            self.status_checker = status_checker
            self.enabled_checker = enabled_checker
            self.pending_restart = False
            self.restart_timer = None
            self.debounce_delay = 5  # Wait 5 seconds after last change before restarting

        def on_modified(self, event):
            if event.is_directory or not any(event.src_path.endswith(ext) for ext in self.file_extensions):
                return

            if '__pycache__' in event.src_path or '.pyc' in event.src_path:
                return

            try:
                rel_path = os.path.relpath(event.src_path, self.manager.project_root)
            except ValueError:
                rel_path = event.src_path

            self.manager.log_message("system", f"📝 {self.service_name.capitalize()} file changed: {rel_path}", "CHANGE")

            if self.status_checker() == "Running" and self.enabled_checker():
                self._schedule_restart()
            elif self.status_checker() == "Running" and not self.enabled_checker():
                key = 'r' if self.service_name == 'backend' else 't'
                self.manager.log_message("system", f"📁 {self.service_name.upper()} file changed but auto-restart disabled (press '{key}' to enable)", "INFO")

        def _schedule_restart(self):
            if self.restart_timer:
                self.restart_timer.cancel()

            if not self.pending_restart:
                self.pending_restart = True
                self.manager.log_message("system", f"⏱️ {self.service_name.upper()} restart scheduled in {self.debounce_delay}s", "INFO")

            self.restart_timer = threading.Timer(self.debounce_delay, self._execute_restart)
            self.restart_timer.daemon = True
            self.restart_timer.start()

        def _execute_restart(self):
            self.pending_restart = False
            self.restart_timer = None
            status = self.status_checker()
            enabled = self.enabled_checker()
            self.manager.log_message("system", f"🔍 {self.service_name.upper()} restart check: Status={status}, Enabled={enabled}", "DEBUG")
            if status == "Running" and enabled:
                self.manager.log_message("system", f"🔄 Executing {self.service_name.upper()} auto-restart", "INFO")
                threading.Thread(target=self.restart_function, daemon=True).start()
            else:
                self.manager.log_message("system", f"⏹️ {self.service_name.upper()} restart cancelled (Status: {status}, Enabled: {enabled})", "INFO")

except ImportError:
    WATCHDOG_AVAILABLE = False
    class DebouncedRestartHandler:
        def __init__(self, *args, **kwargs): pass


class LogEntry:
    """Log entry with metadata."""
    def __init__(self, service: str, message: str, level: str = "INFO", timestamp: datetime = None):
        self.service = service
        self.message = message
        self.level = level
        self.timestamp = timestamp or datetime.now()
        self.full_timestamp = self.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        self.display_timestamp = self.timestamp.strftime("%H:%M:%S")

    def get_display_line(self, show_service=False):
        """Get formatted line for display with Rich markup."""
        level_styles = {
            "CHANGE": "[bold cyan]🔄[/]",
            "ERROR": "[bold red]❌[/]",
            "WARN": "[bold yellow]⚠️[/]",
            "SUCCESS": "[bold green]✅[/]",
            "INFO": "[bold blue]ℹ️[/]",
            "DEBUG": "[bold magenta]🔍[/]",
        }
        symbol = level_styles.get(self.level, "📝")
        service_prefix = f"[[bold purple]{self.service.upper()}[/]] " if show_service else ""
        escaped_message = escape(self.message)
        return f"[[dim]{self.display_timestamp}[/]] {symbol} {service_prefix}{escaped_message}"

    def get_file_line(self):
        """Get formatted line for file logging."""
        return f"[{self.full_timestamp}] [{self.service.upper()}] [{self.level}] {self.message}"


class EnhancedServerManager:
    def __init__(self):
        self.term = Terminal()
        self.backend_process: Optional[subprocess.Popen] = None
        self.frontend_process: Optional[subprocess.Popen] = None

        self.backend_logs = deque(maxlen=2000)
        self.frontend_logs = deque(maxlen=2000)
        self.all_logs = deque(maxlen=5000)

        self.running = True
        self.backend_status = "Stopped"
        self.frontend_status = "Stopped"
        self.selected_view = "all"

        self.scroll_position = 0
        self.search_term = ""
        self.search_mode = False
        self.filtered_logs = []
        self.auto_scroll = True

        self.https_enabled = os.getenv("HTTPS_ENABLED", "true").lower() == "true"
        self.http_port = 8080
        self.https_port = 8443

        self.api_enabled = os.getenv("DEV_MANAGER_API_ENABLED", "true").lower() == "true"
        self.api_host = os.getenv("DEV_MANAGER_API_HOST", "0.0.0.0")
        self.api_port = int(os.getenv("DEV_MANAGER_API_PORT", "8765"))
        self.api_log_requests = os.getenv("DEV_MANAGER_API_LOG_REQUESTS", "true").lower() == "true"
        self.api_server: Optional[ThreadingHTTPServer] = None
        self.api_thread: Optional[threading.Thread] = None

        self.local_ip = self._get_local_ip()
        self.backend_port = self.https_port if self.https_enabled else self.http_port
        protocol = "https" if self.https_enabled else "http"
        self.backend_url = f"{protocol}://{self.local_ip}:{self.backend_port}"
        frontend_protocol = "https" if self.https_enabled else "http"
        self.frontend_url = f"{frontend_protocol}://{self.local_ip}:5173"
        self.project_root = Path(__file__).parent
        self.frontend_path = self.project_root / "MakerMatrix" / "frontend"
        self.log_file_path = self.project_root / "dev_manager.log"

        self.log_lock = threading.RLock()

        self._init_log_file()
        mode = "HTTPS" if self.https_enabled else "HTTP"
        self.log_message("system", f"Development Manager initialized on {self.local_ip} ({mode} mode)", "SUCCESS")

        self.log_message("system", "Checking for stale processes...", "INFO")
        self._kill_stale_processes(self.backend_port, "backend")
        self._kill_stale_processes(5173, "frontend")

        self.file_observer = None
        self.auto_restart_backend_enabled = True
        self.auto_restart_frontend_enabled = False # Off by default
        self._setup_file_watching()

        self._start_api_server()

    def _setup_file_watching(self):
        if not WATCHDOG_AVAILABLE:
            self.log_message("system", "⚠️ watchdog not available - auto-restart disabled.", "WARN")
            return

        self.file_observer = Observer()

        # Backend watcher
        backend_handler = DebouncedRestartHandler(
            self, 'backend', ['.py'], self._safe_restart_backend,
            lambda: self.backend_status, lambda: self.auto_restart_backend_enabled
        )
        backend_watch_path = self.project_root / "MakerMatrix"
        if backend_watch_path.exists():
            self.file_observer.schedule(backend_handler, str(backend_watch_path), recursive=True)
            self.log_message("system", f"📁 Watching Backend files in {backend_watch_path}", "SUCCESS")

        # Frontend watcher
        frontend_handler = DebouncedRestartHandler(
            self, 'frontend', ['.js', '.ts', '.jsx', '.tsx', '.css', '.html', '.svelte'], self.restart_frontend,
            lambda: self.frontend_status, lambda: self.auto_restart_frontend_enabled
        )
        frontend_watch_path = self.frontend_path / "src"
        if frontend_watch_path.exists():
            self.file_observer.schedule(frontend_handler, str(frontend_watch_path), recursive=True)
            self.log_message("system", f"📁 Watching Frontend files in {frontend_watch_path}", "SUCCESS")

        if self.file_observer.emitters:
            self.file_observer.start()
        else:
            self.log_message("system", "⚠️ No valid paths found to watch.", "WARN")


    def _create_api_handler(self):
        manager = self

        class ManagerAPIHandler(BaseHTTPRequestHandler):
            server_version = "MakerMatrixDevManager/1.0"

            def log_message(self, format, *args):
                if manager.api_log_requests:
                    manager.log_message("system", f"API {self.address_string()}: {format % args}", "DEBUG")

            def _write_json(self, status_code: int, payload: Dict[str, Any]):
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()
                self.wfile.write(body)

            def _read_json_body(self) -> Dict[str, Any]:
                length = int(self.headers.get("Content-Length", "0") or 0)
                if length <= 0:
                    return {}
                raw = self.rfile.read(length)
                if not raw:
                    return {}
                try:
                    return json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON body: {exc.msg}") from exc

            def do_OPTIONS(self):
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()

            def do_GET(self):
                parsed = urlparse(self.path)
                path = parsed.path.rstrip('/') or '/'
                try:
                    if path == '/':
                        payload = {
                            "message": "MakerMatrix Development Manager control API",
                            "docs": "See /docs for endpoint reference",
                            "status": manager._api_status_payload(),
                        }
                        self._write_json(200, payload)
                    elif path == '/docs':
                        self._write_json(200, manager._api_docs_payload())
                    elif path == '/status':
                        self._write_json(200, manager._api_status_payload())
                    elif path == '/logs':
                        query = parse_qs(parsed.query or "")
                        service = query.get('service', ['all'])[0]
                        limit_param = query.get('limit', ['100'])[0]
                        try:
                            limit = int(limit_param)
                        except ValueError:
                            self._write_json(400, {"error": "'limit' must be an integer"})
                            return
                        logs = manager.get_logs_snapshot(service=service, limit=limit)
                        self._write_json(200, {"logs": logs, "service": service, "limit": limit})
                    else:
                        self._write_json(404, {"error": "Not found"})
                except ValueError as exc:
                    self._write_json(400, {"error": str(exc)})
                except Exception as exc:
                    manager.log_message("system", f"API GET {path} failed: {exc}", "ERROR")
                    self._write_json(500, {"error": "Internal server error"})

            def do_POST(self):
                parsed = urlparse(self.path)
                path = parsed.path.rstrip('/') or '/'

                try:
                    body = self._read_json_body()
                except ValueError as exc:
                    self._write_json(400, {"error": str(exc)})
                    return

                try:
                    if path == '/backend/start':
                        manager.start_backend()
                        self._write_json(200, {"ok": True, "status": manager._api_status_payload()["backend"]})
                    elif path == '/backend/stop':
                        manager.stop_backend()
                        self._write_json(200, {"ok": True, "status": manager._api_status_payload()["backend"]})
                    elif path == '/backend/restart':
                        manager.schedule_backend_restart()
                        self._write_json(202, {"ok": True, "message": "Backend restart scheduled"})
                    elif path == '/frontend/start':
                        manager.start_frontend()
                        self._write_json(200, {"ok": True, "status": manager._api_status_payload()["frontend"]})
                    elif path == '/frontend/stop':
                        manager.stop_frontend()
                        self._write_json(200, {"ok": True, "status": manager._api_status_payload()["frontend"]})
                    elif path == '/frontend/restart':
                        manager.schedule_frontend_restart()
                        self._write_json(202, {"ok": True, "message": "Frontend restart scheduled"})
                    elif path == '/frontend/build':
                        manager.schedule_frontend_build()
                        self._write_json(202, {"ok": True, "message": "Frontend build started"})
                    elif path == '/all/stop':
                        manager.stop_all()
                        self._write_json(200, {"ok": True, "status": manager._api_status_payload()})
                    elif path == '/logs/clear':
                        manager.clear_logs()
                        self._write_json(200, {"ok": True, "message": "Logs cleared"})
                    elif path == '/mode':
                        if 'https' not in body:
                            self._write_json(400, {"error": "Request body must include 'https' boolean"})
                            return
                        manager.switch_mode(bool(body['https']))
                        self._write_json(200, {"ok": True, "https_enabled": manager.https_enabled})
                    elif path == '/auto-restart':
                        if not any(key in body for key in ('backend', 'frontend')):
                            self._write_json(400, {"error": "Provide 'backend' and/or 'frontend' boolean flags"})
                            return
                        changes = {}
                        if 'backend' in body:
                            manager.set_auto_restart('backend', bool(body['backend']))
                            changes['backend'] = manager.auto_restart_backend_enabled
                        if 'frontend' in body:
                            manager.set_auto_restart('frontend', bool(body['frontend']))
                            changes['frontend'] = manager.auto_restart_frontend_enabled
                        self._write_json(200, {"ok": True, "auto_restart": changes})
                    elif path == '/backend/health':
                        result = manager._check_backend_health()
                        status_code = 200 if result.get('ok') else 503
                        self._write_json(status_code, result)
                    else:
                        self._write_json(404, {"error": "Not found"})
                except Exception as exc:
                    manager.log_message("system", f"API POST {path} failed: {exc}", "ERROR")
                    self._write_json(500, {"error": "Internal server error"})

        return ManagerAPIHandler

    def _start_api_server(self):
        if not self.api_enabled:
            self.log_message("system", "Control API disabled via DEV_MANAGER_API_ENABLED", "INFO")
            return

        handler_cls = self._create_api_handler()
        try:
            self.api_server = ThreadingHTTPServer((self.api_host, self.api_port), handler_cls)
        except OSError as exc:
            self.api_server = None
            self.log_message("system", f"Failed to start control API on {self.api_host}:{self.api_port} ({exc})", "ERROR")
            return

        self.api_thread = threading.Thread(target=self.api_server.serve_forever, name="DevManagerAPI", daemon=True)
        self.api_thread.start()
        self.log_message("system", f"🛰️ Control API listening on http://{self.api_host}:{self.api_port}", "SUCCESS")

    def _stop_api_server(self):
        if not self.api_server:
            return

        try:
            self.api_server.shutdown()
            self.api_server.server_close()
        except Exception as exc:
            self.log_message("system", f"Error while shutting down API server: {exc}", "WARN")
        finally:
            self.api_server = None
            if self.api_thread and self.api_thread.is_alive():
                self.api_thread.join(timeout=1)
            self.api_thread = None
            self.log_message("system", "Control API stopped", "INFO")


    def _get_local_ip(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "localhost"

    def _init_log_file(self):
        """Initialize and clear the log file for the new session."""
        try:
            with open(self.log_file_path, 'w', encoding='utf-8') as f:
                f.write(f"{'='*80}\n")
                f.write(f"MakerMatrix Development Session Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'='*80}\n\n")
        except Exception as e:
            print(f"Warning: Could not initialize log file: {e}")

    def _find_processes_on_port(self, port: int) -> List[psutil.Process]:
        processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    for conn in proc.connections(kind='inet'):
                        if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                            processes.append(proc)
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            self.log_message("system", f"Error scanning for processes on port {port}: {e}", "WARN")
        return processes

    def _kill_stale_processes(self, port: int, service_name: str):
        processes = self._find_processes_on_port(port)
        if not processes:
            return

        for proc in processes:
            try:
                proc_info = f"PID:{proc.pid} ({proc.name()})"
                self.log_message("system", f"Found stale {service_name} process {proc_info} on port {port}", "WARN")
                proc.kill()
                self.log_message("system", f"Killed stale {service_name} process {proc_info}", "SUCCESS")
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                self.log_message("system", f"Could not kill process {proc_info}: {e}", "ERROR")

    def _write_to_log_file(self, log_entry: LogEntry):
        try:
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(f"{log_entry.get_file_line()}\n")
                f.flush()  # Ensure logs are written immediately
        except Exception as e:
            # This print will be visible after the TUI closes if file logging fails
            print(f"[LOGGING ERROR] Failed to write to log file: {e}")

    def log_message(self, service: str, message: str, level: str = "INFO"):
        with self.log_lock:
            log_entry = LogEntry(service, message, level)
            self._write_to_log_file(log_entry)

            if service == "backend":
                self.backend_logs.append(log_entry)
            elif service == "frontend":
                self.frontend_logs.append(log_entry)
            elif service == "system":
                self.backend_logs.append(log_entry)
                self.frontend_logs.append(log_entry)

            self.all_logs.append(log_entry)

            if self.search_term:
                self._update_filtered_logs()

            if self.scroll_position == 0:
                self.auto_scroll = True
            else:
                self.auto_scroll = False

    def _update_filtered_logs(self):
        if not self.search_term:
            self.filtered_logs = []
            return

        search_lower = self.search_term.lower()
        self.filtered_logs = [
            log for log in self.all_logs
            if search_lower in log.message.lower() or
               search_lower in log.service.lower() or
               search_lower in log.level.lower()
        ]

    def start_backend(self):
        if self.backend_process and self.backend_process.poll() is None:
            self.log_message("backend", "Backend already running", "WARN")
            return

        self._kill_stale_processes(self.backend_port, "backend")
        self.log_message("backend", "Starting FastAPI backend server...", "INFO")

        venv_python = self.project_root / "venv_test" / "bin" / "python"
        python_exe = str(venv_python) if venv_python.exists() else sys.executable

        env = os.environ.copy()
        if self.https_enabled:
            env["HTTPS_ENABLED"] = "true"
            cmd = [python_exe, "-m", "MakerMatrix.main"]
            self.log_message("backend", f"Starting in HTTPS mode on port {self.backend_port}", "INFO")
        else:
            env.pop("HTTPS_ENABLED", None)
            cmd = [python_exe, "-m", "uvicorn", "MakerMatrix.main:app", "--host", "0.0.0.0", "--port", str(self.backend_port)]
            self.log_message("backend", f"Starting in HTTP mode on port {self.backend_port}", "INFO")

        self.backend_process = subprocess.Popen(
            cmd, cwd=self.project_root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True, bufsize=1, env=env
        )

        threading.Thread(target=self._monitor_process_output, args=(self.backend_process, "backend"), daemon=True).start()
        self.backend_status = "Starting"
        self.log_message("backend", f"Backend PID: {self.backend_process.pid}", "INFO")

    def start_frontend(self):
        if self.frontend_process and self.frontend_process.poll() is None:
            self.log_message("frontend", "Frontend already running", "WARN")
            return

        if not self.frontend_path.exists():
            self.log_message("frontend", f"Frontend path not found: {self.frontend_path}", "ERROR")
            return

        self._kill_stale_processes(5173, "frontend")
        self.log_message("frontend", "Starting React development server...", "INFO")

        self.frontend_process = subprocess.Popen(
            ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"],
            cwd=self.frontend_path, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True, bufsize=1
        )

        threading.Thread(target=self._monitor_process_output, args=(self.frontend_process, "frontend"), daemon=True).start()
        self.frontend_status = "Starting"
        self.log_message("frontend", f"Frontend PID: {self.frontend_process.pid}", "INFO")

    def _monitor_process_output(self, process: subprocess.Popen, service: str):
        for line in iter(process.stdout.readline, ''):
            if not line: break
            line = line.strip()
            if not line: continue

            level = "INFO"
            if service == "backend":
                if ("Application startup complete" in line or 
                    "Uvicorn running on" in line or 
                    "Starting MakerMatrix with HTTPS" in line or
                    "MakerMatrix API is ready" in line):
                    self.backend_status = "Running"
                    level = "SUCCESS"
                elif any(error in line.upper() for error in ["CRITICAL", "FATAL", "TRACEBACK"]):
                    self.backend_status = "Error"
                    level = "ERROR"
                elif line.upper().startswith("ERROR:") or ":ERROR:" in line.upper():
                    # Only mark as error level in logs if it's actually an ERROR log level, don't change backend status for normal error logs
                    level = "ERROR"
            elif service == "frontend":
                if "Local:" in line and "http" in line:
                    self.frontend_status = "Running"
                    level = "SUCCESS"
                elif any(error in line for error in ["Failed to compile", "Module not found", "SyntaxError"]):
                    self.frontend_status = "Error"
                    level = "ERROR"
                elif any(keyword in line.lower() for keyword in ["hmr update", "file changed"]):
                    level = "CHANGE"

            self.log_message(service, line, level)

        if service == "backend": self.backend_status = "Stopped"
        else: self.frontend_status = "Stopped"

    def stop_process(self, process, service_name):
        if process and process.poll() is None:
            self.log_message(service_name, f"Stopping {service_name} server...", "INFO")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                self.log_message(service_name, f"{service_name.capitalize()} force killed", "WARN")
            return True
        return False

    def stop_backend(self):
        if not self.stop_process(self.backend_process, "backend"):
            self.log_message("backend", "Backend not running", "WARN")
        self.backend_status = "Stopped"

    def stop_frontend(self):
        if not self.stop_process(self.frontend_process, "frontend"):
            self.log_message("frontend", "Frontend not running", "WARN")
        self.frontend_status = "Stopped"

    def stop_all(self):
        self.stop_backend()
        self.stop_frontend()

    def schedule_backend_restart(self):
        threading.Thread(target=self._safe_restart_backend, name="BackendRestart", daemon=True).start()

    def _safe_restart_backend(self):
        self.log_message("system", "🔄 Beginning safe backend restart...", "INFO")
        if self.backend_process and self.backend_process.poll() is None:
            self.stop_backend()
            time.sleep(2)
        self.start_backend()
        if self.backend_status in ["Starting", "Running"]:
            self.log_message("system", "✅ Backend restart completed successfully", "SUCCESS")
        else:
            self.log_message("system", f"⚠️ Backend restart may have failed - status: {self.backend_status}", "WARN")

    def schedule_frontend_restart(self):
        threading.Thread(target=self.restart_frontend, name="FrontendRestart", daemon=True).start()

    def restart_frontend(self):
        self.log_message("system", "🔄 Beginning frontend restart...", "INFO")
        self.stop_frontend()
        time.sleep(1)
        self.start_frontend()

    def schedule_frontend_build(self):
        threading.Thread(target=self.build_frontend, name="FrontendBuild", daemon=True).start()

    def build_frontend(self):
        self.log_message("frontend", "Building frontend for production...", "INFO")
        if self.frontend_process and self.frontend_process.poll() is None:
            self.stop_frontend()
            time.sleep(2)

        try:
            result = subprocess.run(
                ["npm", "run", "build"], cwd=self.frontend_path, capture_output=True, text=True, check=True
            )
            for line in result.stdout.splitlines():
                self.log_message("frontend", f"BUILD: {line}", "INFO")
            self.log_message("frontend", "✅ Frontend build completed successfully!", "SUCCESS")
        except subprocess.CalledProcessError as e:
            for line in e.stderr.splitlines():
                self.log_message("frontend", f"BUILD: {line}", "ERROR")
            self.log_message("frontend", f"❌ Frontend build failed with code {e.returncode}", "ERROR")

    def get_current_logs(self) -> List[LogEntry]:
        if self.search_term and self.filtered_logs:
            return self.filtered_logs
        if self.selected_view == "backend":
            return list(self.backend_logs)
        if self.selected_view == "frontend":
            return list(self.frontend_logs)
        if self.selected_view == "errors":
            return [log for log in self.all_logs if log.level in ["ERROR", "WARN", "CRITICAL", "FATAL"]]
        return list(self.all_logs)

    def get_status_display(self, status: str) -> str:
        status_map = {
            "Running": "[bright_green]🟢 Running[/]",
            "Starting": "[bright_yellow]🟡 Starting[/]",
            "Stopped": "[bright_red]🔴 Stopped[/]",
            "Failed": "[bright_red]❌ Failed[/]",
            "Error": "[bright_red]⚠️ Error[/]",
        }
        return status_map.get(status, "[white]⚪ Unknown[/]")

    def set_auto_restart(self, service: str, enabled: bool):
        state_label = 'enabled' if enabled else 'disabled'
        if service == 'backend':
            self.auto_restart_backend_enabled = enabled
            self.log_message("system", f"📁 BE Auto-restart {state_label}", "INFO")
        elif service == 'frontend':
            self.auto_restart_frontend_enabled = enabled
            self.log_message("system", f"📁 FE Auto-restart {state_label}", "INFO")
        else:
            raise ValueError(f"Unknown service '{service}' for auto-restart toggle")

    def clear_logs(self):
        with self.log_lock:
            self.backend_logs.clear()
            self.frontend_logs.clear()
            self.all_logs.clear()
            self.filtered_logs.clear()
            self.scroll_position = 0
            self.auto_scroll = True
        self.log_message("system", "Logs cleared", "INFO")

    def get_logs_snapshot(self, service: str = "all", limit: int = 100) -> List[Dict[str, str]]:
        if limit <= 0:
            raise ValueError("'limit' must be positive")

        limit = min(limit, 1000)

        with self.log_lock:
            if service == "all":
                selected = list(self.all_logs)
            elif service == "backend":
                selected = list(self.backend_logs)
            elif service == "frontend":
                selected = list(self.frontend_logs)
            elif service == "errors":
                selected = [log for log in self.all_logs if log.level in ["ERROR", "WARN", "CRITICAL", "FATAL"]]
            elif service == "system":
                selected = [log for log in self.all_logs if log.service == "system"]
            else:
                raise ValueError(f"Unknown service filter '{service}'")

            subset = selected[-limit:]

        return [
            {
                "timestamp": log.full_timestamp,
                "service": log.service,
                "level": log.level,
                "message": log.message,
            }
            for log in subset
        ]

    def _api_status_payload(self) -> Dict[str, Any]:
        backend_pid = self.backend_process.pid if self.backend_process and self.backend_process.poll() is None else None
        frontend_pid = self.frontend_process.pid if self.frontend_process and self.frontend_process.poll() is None else None

        return {
            "backend": {
                "status": self.backend_status,
                "pid": backend_pid,
                "port": self.backend_port,
                "url": self.backend_url,
                "auto_restart": self.auto_restart_backend_enabled,
            },
            "frontend": {
                "status": self.frontend_status,
                "pid": frontend_pid,
                "port": 5173,
                "url": self.frontend_url,
                "auto_restart": self.auto_restart_frontend_enabled,
            },
            "https_enabled": self.https_enabled,
            "api": {
                "host": self.api_host,
                "port": self.api_port,
                "log_requests": self.api_log_requests,
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    def _api_docs_payload(self) -> Dict[str, Any]:
        base_url = f"http://{self.api_host}:{self.api_port}"
        endpoints: List[Dict[str, Any]] = [
            {"method": "GET", "path": "/", "description": "Summary message and latest status snapshot"},
            {"method": "GET", "path": "/docs", "description": "Structured list of available control endpoints"},
            {"method": "GET", "path": "/status", "description": "Current status for backend and frontend services"},
            {
                "method": "GET",
                "path": "/logs",
                "description": "Retrieve recent log entries",
                "query": {
                    "service": "all | backend | frontend | errors | system (default all)",
                    "limit": "Number of entries to return (default 100, max 1000)",
                },
            },
            {"method": "POST", "path": "/backend/start", "description": "Start the FastAPI backend"},
            {"method": "POST", "path": "/backend/stop", "description": "Stop the FastAPI backend"},
            {"method": "POST", "path": "/backend/restart", "description": "Restart the FastAPI backend (async)"},
            {"method": "POST", "path": "/backend/health", "description": "Trigger backend health check"},
            {"method": "POST", "path": "/frontend/start", "description": "Start the Vite dev server"},
            {"method": "POST", "path": "/frontend/stop", "description": "Stop the Vite dev server"},
            {"method": "POST", "path": "/frontend/restart", "description": "Restart the Vite dev server (async)"},
            {"method": "POST", "path": "/frontend/build", "description": "Run npm run build asynchronously"},
            {"method": "POST", "path": "/all/stop", "description": "Stop backend and frontend"},
            {
                "method": "POST",
                "path": "/logs/clear",
                "description": "Clear in-memory log buffers",
            },
            {
                "method": "POST",
                "path": "/auto-restart",
                "description": "Toggle auto-restart flags",
                "body": {"backend": "boolean (optional)", "frontend": "boolean (optional)"},
            },
            {
                "method": "POST",
                "path": "/mode",
                "description": "Switch HTTP/HTTPS mode for backend",
                "body": {"https": "boolean"},
            },
        ]

        return {
            "title": "MakerMatrix Dev Manager Control API",
            "base_url": base_url,
            "notes": "All endpoints return application/json and support OPTIONS for CORS preflight.",
            "endpoints": endpoints,
            "status": self._api_status_payload(),
        }

    def handle_input(self, key):
        if self.search_mode:
            if key.name == 'KEY_ESCAPE' or key.name == 'KEY_ENTER':
                self.search_mode = False
                if key.name == 'KEY_ENTER': self._update_filtered_logs()
                self.scroll_position = 0
            elif key.name == 'KEY_BACKSPACE':
                self.search_term = self.search_term[:-1]
            elif key and len(key) == 1 and key.isprintable():
                self.search_term += key
            return

        if key == 'q': self.running = False
        elif key == '1': self.start_backend()
        elif key == '2': self.stop_backend()
        elif key == '3': self.start_frontend()
        elif key == '4': self.stop_frontend()
        elif key == '5': self.start_backend(); self.start_frontend()
        elif key == '6': self.stop_all()
        elif key == '7': self.schedule_backend_restart()
        elif key == '8': self.schedule_frontend_restart()
        elif key == '9': self.schedule_frontend_build()
        elif key == 'v':
            views = ["all", "backend", "frontend", "errors"]
            self.selected_view = views[(views.index(self.selected_view) + 1) % len(views)]
            self.scroll_position = 0; self.auto_scroll = True; self.search_term = ""
        elif key == 'e':
            self.selected_view = "errors"
            self.scroll_position = 0; self.auto_scroll = True; self.search_term = ""
        elif key == 'c': self.clear_logs()
        elif key == 's': self.search_mode = True; self.search_term = ""
        elif key == 'a':
            self.auto_scroll = not self.auto_scroll
            self.log_message("system", f"Auto-scroll {'enabled' if self.auto_scroll else 'disabled'}", "INFO")
        elif key == 'r':
            self.set_auto_restart('backend', not self.auto_restart_backend_enabled)
        elif key == 't':
            self.set_auto_restart('frontend', not self.auto_restart_frontend_enabled)
        elif key == 'h': self._check_backend_health()
        elif key.name == 'KEY_ESCAPE':
            self.search_term = ""; self.filtered_logs = []; self.scroll_position = 0; self.auto_scroll = True

        # Scrolling
        elif key.name in ['KEY_UP', 'KEY_DOWN', 'KEY_PGUP', 'KEY_PGDN', 'KEY_HOME', 'KEY_END'] or key in 'jk':
            logs = self.get_current_logs()
            available_height = self.term.height - 11 # Approximate available height
            max_scroll = max(0, len(logs) - available_height)

            if key.name == 'KEY_UP' or key == 'k': self.scroll_position = min(self.scroll_position + 1, max_scroll)
            elif key.name == 'KEY_DOWN' or key == 'j': self.scroll_position = max(self.scroll_position - 1, 0)
            elif key.name == 'KEY_PGUP': self.scroll_position = min(self.scroll_position + available_height // 2, max_scroll)
            elif key.name == 'KEY_PGDN': self.scroll_position = max(self.scroll_position - available_height // 2, 0)
            elif key.name == 'KEY_HOME': self.scroll_position = max_scroll
            elif key.name == 'KEY_END': self.scroll_position = 0

            self.auto_scroll = self.scroll_position == 0

        elif key == 'H': self.switch_to_http_mode()
        elif key == 'S': self.switch_to_https_mode()

    def switch_mode(self, https: bool):
        if self.https_enabled == https:
            self.log_message("system", f"Already in {'HTTPS' if https else 'HTTP'} mode", "INFO")
            return

        was_running = self.backend_status in ["Running", "Starting"]
        if was_running:
            self.stop_backend()
            time.sleep(1)

        self.https_enabled = https
        self.backend_port = self.https_port if https else self.http_port
        protocol = "https" if https else "http"
        self.backend_url = f"{protocol}://{self.local_ip}:{self.backend_port}"

        self.log_message("system", f"Switched to {'HTTPS' if https else 'HTTP'} mode", "SUCCESS")
        if was_running:
            self.start_backend()

    def switch_to_http_mode(self): self.switch_mode(False)
    def switch_to_https_mode(self): self.switch_mode(True)

    def _check_backend_health(self):
        self.log_message("system", "🏥 Checking backend health...", "INFO")
        result: Dict[str, Optional[str]] = {"ok": False}
        try:
            response = requests.get(f"{self.backend_url}/api/utility/get_counts", timeout=5)
            try:
                response_payload = response.json()
            except ValueError:
                response_payload = response.text

            result.update({
                "status_code": response.status_code,
                "response": response_payload,
            })

            if response.ok:
                self.log_message("system", "✅ Backend health check passed", "SUCCESS")
                if self.backend_status != "Running":
                    self.backend_status = "Running"
                result["ok"] = True
                result["message"] = "Backend healthy"
            else:
                self.log_message("system", f"⚠️ Backend responded with status {response.status_code}", "WARN")
                if self.backend_status == "Running":
                    self.backend_status = "Error"
                result["message"] = "Backend responded with non-success status"
        except requests.RequestException as e:
            self.log_message("system", f"❌ Backend health check failed: {e}", "ERROR")
            if self.backend_status == "Running": self.backend_status = "Error"
            result.update({
                "error": str(e),
                "exception": e.__class__.__name__,
                "message": "Exception while contacting backend",
            })
        return result
    def cleanup(self):
        self.log_message("system", "Shutting down development manager...", "INFO")
        self.stop_all()
        self._stop_api_server()
        if self.file_observer:
            self.file_observer.stop()
            self.file_observer.join(timeout=1)
        with open(self.log_file_path, 'a', encoding='utf-8') as f:
            f.write(f"\nSession ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    def _build_header(self) -> Panel:
        backend_display = self.get_status_display(self.backend_status)
        frontend_display = self.get_status_display(self.frontend_status)
        mode_icon = "🔒" if self.https_enabled else "🌐"
        mode_text = "[bright_green]HTTPS[/]" if self.https_enabled else "[bright_blue]HTTP[/]"

        status_text = Text.from_markup(
            f"Backend: {backend_display} ([dim]{self.backend_url}[/]) [{mode_icon} {mode_text}] | "
            f"Frontend: {frontend_display} ([dim]{self.frontend_url}[/])"
        )
        return Panel(status_text, title="[bold bright_blue]🚀 MakerMatrix Development Manager[/]", border_style="blue")

    def _build_controls(self) -> Panel:
        be_auto_status = "[green]ON[/]" if self.auto_restart_backend_enabled else "[red]OFF[/]"
        fe_auto_status = "[green]ON[/]" if self.auto_restart_frontend_enabled else "[red]OFF[/]"
        controls_text = (
            "[bold]Start/Stop[/]: [green]1[/]:Start BE  [green]2[/]:Stop BE   [green]3[/]:Start FE  [green]4[/]:Stop FE    [green]5[/]:Both       [green]6[/]:Stop All\n"
            "[bold]Manage[/]:     [green]7[/]:Restart BE [green]8[/]:Restart FE [green]9[/]:Build FE\n"
            "[bold]Display[/]:    [green]v[/]:View      [green]e[/]:Errors     [green]c[/]:Clear      [green]s[/]:Search     [green]a[/]:Auto-scroll\n"
            f"[bold]Toggles[/]:    [green]r[/]:BE-Restart({be_auto_status}) [green]t[/]:FE-Restart({fe_auto_status}) [green]H[/]:HTTP [green]S[/]:HTTPS\n"
            "[bold]General[/]:    [green]h[/]:Health     [green]q[/]:Quit       [dim]Scroll[/]: ↑↓ pgup/pgdn home/end"
        )
        return Panel(Text.from_markup(controls_text), title="[bold bright_cyan]Controls[/]", border_style="cyan")

    def _build_logs_panel(self) -> Panel:
        logs = self.get_current_logs()
        available_height = self.term.height - 11 # Header(3) + Controls(5) + Margins(3)

        if self.auto_scroll: self.scroll_position = 0

        total_logs = len(logs)
        if total_logs <= available_height:
            visible_logs = logs
        else:
            start_idx = max(0, total_logs - available_height - self.scroll_position)
            end_idx = start_idx + available_height
            visible_logs = logs[start_idx:end_idx]

        log_texts = []
        for log in visible_logs:
            line = log.get_display_line(self.selected_view == "all")
            text = Text.from_markup(line)
            if self.search_term:
                text.highlight_words([self.search_term], "black on yellow", case_sensitive=False)
            log_texts.append(text)

        log_content = Text("\n").join(log_texts) if log_texts else Text.from_markup("[dim]No logs available...[/]")

        view_indicator = f"📋 View: [bright_magenta]{self.selected_view.title()}[/]"
        if self.selected_view == "errors":
            view_indicator = f"⚠️ View: [bright_red]{self.selected_view.title()}[/]"

        search_indicator = ""
        if self.search_mode: search_indicator = f" | 🔍 Search: [bright_yellow]{self.search_term}_[/]"
        elif self.search_term: search_indicator = f" | 🔍 Filter: [bright_yellow]{self.search_term}[/] ({len(self.filtered_logs)} results)"

        scroll_indicator = ""
        if logs and available_height > 0:
            max_scroll = max(0, len(logs) - available_height)
            auto_scroll_icon = "🔄" if self.auto_scroll else "📍"
            scroll_indicator = f" | {auto_scroll_icon} Scroll: [yellow]{self.scroll_position}/{max_scroll}[/]"

        panel_title = f"{view_indicator}{search_indicator}{scroll_indicator}"
        return Panel(log_content, title=panel_title, border_style="magenta")

    def _build_layout(self) -> Layout:
        layout = Layout(name="root")
        layout.split(
            Layout(self._build_header(), name="header", size=3),
            Layout(self._build_controls(), name="controls", size=5),
            Layout(self._build_logs_panel(), name="logs"),
        )
        return layout

    def run(self):
        with self.term.fullscreen(), self.term.cbreak(), self.term.hidden_cursor():
            self.log_message("system", "Development Manager started", "SUCCESS")
            with Live(self._build_layout(), screen=True, redirect_stderr=False, transient=True) as live:
                try:
                    while self.running:
                        key = self.term.inkey(timeout=0.1)
                        if key:
                            self.handle_input(key)
                        live.update(self._build_layout())
                except KeyboardInterrupt:
                    self.running = False
                finally:
                    self.cleanup()
        print("\n🔧 Development Manager stopped.")


def main():
    if "--help" in sys.argv:
        print("""
🚀 MakerMatrix Development Server Manager [Rich TUI]

A TUI application to manage backend (FastAPI) and frontend (React) servers.

Usage: python dev_manager.py

Controls:
  1-5: Start/Stop servers (1:Start BE, 2:Stop BE, 3:Start FE, 4:Stop FE, 5:Both)
  6-9: Manage servers (6:Stop All, 7:Restart BE, 8:Restart FE, 9:Build FE)

  v: Switch log view (All/Backend/Frontend/Errors)
  e: Quick jump to Errors view      c: Clear logs
  s: Enter search mode (ESC to clear) q: Quit

  r: Toggle Backend auto-restart (default: ON)
  t: Toggle Frontend auto-restart (default: OFF)
  ↑↓/jk: Scroll logs              PgUp/PgDn: Fast scroll
  Home/End: Jump to start/end of logs

Features:
  • UI powered by Rich for a clean, modern look.
  • Auto-kills stale processes on startup.
  • Real-time server status and log monitoring.
  • Auto-restarts services on file changes (if watchdog is installed).
  • HTTP control API for automation (defaults to http://127.0.0.1:8765).

HTTP Control API:
  GET  /docs                   → Endpoint catalog (this document)
  GET  /status                 → JSON status snapshot
  GET  /logs?service=all&limit=100
  POST /backend/start|stop|restart
  POST /frontend/start|stop|restart|build
  POST /all/stop               → Stop both services
  POST /backend/health         → Runs health probe
  POST /auto-restart           → Body {"backend": true, "frontend": false}
  POST /mode                   → Body {"https": true}
  POST /logs/clear             → Clear cached logs

Environment variables:
  DEV_MANAGER_API_ENABLED=true|false
  DEV_MANAGER_API_HOST=127.0.0.1
  DEV_MANAGER_API_PORT=8765
  DEV_MANAGER_API_LOG_REQUESTS=true|false

Requirements:
  - pip install blessed requests psutil watchdog rich

Logs saved to: dev_manager.log (cleared on each run)
        """)
        return

    try:
        import blessed, requests, psutil, rich
    except ImportError as e:
        print(f"❌ Error: Missing dependency: {e.name}")
        print("📦 Install with: pip install blessed requests psutil watchdog rich")
        sys.exit(1)

    manager = EnhancedServerManager()
    signal.signal(signal.SIGINT, lambda s, f: setattr(manager, 'running', False))

    try:
        manager.run()
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
        manager.cleanup()

if __name__ == "__main__":
    main()
