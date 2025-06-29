#!/usr/bin/env python3
"""
MCP Server for MakerMatrix Development Manager
Provides Claude Code with tools to interact with the development environment
"""

import asyncio
import json
import logging
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import MCP dependencies
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        TextContent,
        Tool,
    )
except ImportError as e:
    print(f"Error: MCP dependencies not found: {e}")
    print("Install with: pip install mcp")
    sys.exit(1)

# Import our development manager
try:
    from dev_manager import EnhancedServerManager, LogEntry
except ImportError as e:
    print(f"Error: Could not import dev_manager: {e}")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DevManagerMCPServer:
    """MCP Server wrapper for EnhancedServerManager"""
    
    def __init__(self):
        self.dev_manager: Optional[EnhancedServerManager] = None
        self.manager_thread: Optional[threading.Thread] = None
        self.running = False
        
    def start_manager(self):
        """Start the development manager in a separate thread"""
        if self.dev_manager is not None:
            return {"status": "already_running", "message": "Development manager already running"}
            
        try:
            self.dev_manager = EnhancedServerManager()
            self.running = True
            logger.info("Development manager started successfully")
            return {"status": "success", "message": "Development manager started"}
        except Exception as e:
            logger.error(f"Failed to start development manager: {e}")
            return {"status": "error", "message": f"Failed to start: {e}"}
    
    def stop_manager(self):
        """Stop the development manager"""
        if self.dev_manager is None:
            return {"status": "not_running", "message": "Development manager not running"}
            
        try:
            self.dev_manager.cleanup()
            self.dev_manager = None
            self.running = False
            logger.info("Development manager stopped")
            return {"status": "success", "message": "Development manager stopped"}
        except Exception as e:
            logger.error(f"Error stopping development manager: {e}")
            return {"status": "error", "message": f"Error stopping: {e}"}
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of all services"""
        if self.dev_manager is None:
            return {
                "manager_running": False,
                "backend_status": "Unknown",
                "frontend_status": "Unknown",
                "backend_url": None,
                "frontend_url": None,
                "https_enabled": False
            }
        
        return {
            "manager_running": True,
            "backend_status": self.dev_manager.backend_status,
            "frontend_status": self.dev_manager.frontend_status,
            "backend_url": self.dev_manager.backend_url,
            "frontend_url": self.dev_manager.frontend_url,
            "https_enabled": self.dev_manager.https_enabled,
            "auto_restart_enabled": self.dev_manager.auto_restart_enabled,
            "log_counts": {
                "backend": len(self.dev_manager.backend_logs),
                "frontend": len(self.dev_manager.frontend_logs), 
                "total": len(self.dev_manager.all_logs)
            }
        }
    
    def start_backend(self) -> Dict[str, Any]:
        """Start the backend server"""
        if self.dev_manager is None:
            return {"status": "error", "message": "Development manager not running"}
        
        try:
            self.dev_manager.start_backend()
            return {"status": "success", "message": "Backend start initiated"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to start backend: {e}"}
    
    def stop_backend(self) -> Dict[str, Any]:
        """Stop the backend server"""
        if self.dev_manager is None:
            return {"status": "error", "message": "Development manager not running"}
        
        try:
            self.dev_manager.stop_backend()
            return {"status": "success", "message": "Backend stopped"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to stop backend: {e}"}
    
    def restart_backend(self) -> Dict[str, Any]:
        """Restart the backend server"""
        if self.dev_manager is None:
            return {"status": "error", "message": "Development manager not running"}
        
        try:
            # Use the safe restart method
            threading.Thread(target=self.dev_manager._safe_restart_backend, daemon=True).start()
            return {"status": "success", "message": "Backend restart initiated"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to restart backend: {e}"}
    
    def start_frontend(self) -> Dict[str, Any]:
        """Start the frontend server"""
        if self.dev_manager is None:
            return {"status": "error", "message": "Development manager not running"}
        
        try:
            self.dev_manager.start_frontend()
            return {"status": "success", "message": "Frontend start initiated"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to start frontend: {e}"}
    
    def stop_frontend(self) -> Dict[str, Any]:
        """Stop the frontend server"""
        if self.dev_manager is None:
            return {"status": "error", "message": "Development manager not running"}
        
        try:
            self.dev_manager.stop_frontend()
            return {"status": "success", "message": "Frontend stopped"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to stop frontend: {e}"}
    
    def restart_frontend(self) -> Dict[str, Any]:
        """Restart the frontend server"""
        if self.dev_manager is None:
            return {"status": "error", "message": "Development manager not running"}
        
        try:
            threading.Thread(target=self.dev_manager.restart_frontend, daemon=True).start()
            return {"status": "success", "message": "Frontend restart initiated"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to restart frontend: {e}"}
    
    def start_all(self) -> Dict[str, Any]:
        """Start both backend and frontend servers"""
        if self.dev_manager is None:
            return {"status": "error", "message": "Development manager not running"}
        
        try:
            self.dev_manager.start_backend()
            self.dev_manager.start_frontend()
            return {"status": "success", "message": "Both servers start initiated"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to start servers: {e}"}
    
    def stop_all(self) -> Dict[str, Any]:
        """Stop both servers"""
        if self.dev_manager is None:
            return {"status": "error", "message": "Development manager not running"}
        
        try:
            self.dev_manager.stop_all()
            return {"status": "success", "message": "Both servers stopped"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to stop servers: {e}"}
    
    def build_frontend(self) -> Dict[str, Any]:
        """Build frontend for production"""
        if self.dev_manager is None:
            return {"status": "error", "message": "Development manager not running"}
        
        try:
            threading.Thread(target=self.dev_manager.build_frontend, daemon=True).start()
            return {"status": "success", "message": "Frontend build initiated"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to build frontend: {e}"}
    
    def get_logs(self, service: str = "all", limit: int = 100, search: str = None) -> Dict[str, Any]:
        """Get logs from the development manager"""
        if self.dev_manager is None:
            return {"status": "error", "message": "Development manager not running"}
        
        try:
            # Get logs based on service type
            if service == "backend":
                logs = list(self.dev_manager.backend_logs)
            elif service == "frontend":
                logs = list(self.dev_manager.frontend_logs)
            elif service == "errors":
                logs = [log for log in self.dev_manager.all_logs 
                       if log.level in ["ERROR", "WARN", "CRITICAL", "FATAL"]]
            else:  # all
                logs = list(self.dev_manager.all_logs)
            
            # Apply search filter if provided
            if search:
                search_lower = search.lower()
                logs = [log for log in logs 
                       if (search_lower in log.message.lower() or 
                           search_lower in log.service.lower() or
                           search_lower in log.level.lower())]
            
            # Limit results (get most recent)
            if limit > 0:
                logs = logs[-limit:]
            
            # Convert to serializable format
            log_data = []
            for log in logs:
                log_data.append({
                    "timestamp": log.full_timestamp,
                    "service": log.service,
                    "level": log.level,
                    "message": log.message,
                    "display_line": log.get_display_line(service == "all")
                })
            
            return {
                "status": "success",
                "logs": log_data,
                "total_count": len(log_data),
                "service": service,
                "search": search
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to get logs: {e}"}
    
    def clear_logs(self) -> Dict[str, Any]:
        """Clear all logs"""
        if self.dev_manager is None:
            return {"status": "error", "message": "Development manager not running"}
        
        try:
            self.dev_manager.clear_logs()
            return {"status": "success", "message": "Logs cleared"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to clear logs: {e}"}
    
    def health_check(self) -> Dict[str, Any]:
        """Perform backend health check"""
        if self.dev_manager is None:
            return {"status": "error", "message": "Development manager not running"}
        
        try:
            self.dev_manager._check_backend_health()
            return {"status": "success", "message": "Health check initiated"}
        except Exception as e:
            return {"status": "error", "message": f"Health check failed: {e}"}
    
    def toggle_auto_restart(self) -> Dict[str, Any]:
        """Toggle auto-restart feature"""
        if self.dev_manager is None:
            return {"status": "error", "message": "Development manager not running"}
        
        try:
            self.dev_manager.auto_restart_enabled = not self.dev_manager.auto_restart_enabled
            status = "enabled" if self.dev_manager.auto_restart_enabled else "disabled"
            return {"status": "success", "message": f"Auto-restart {status}", "enabled": self.dev_manager.auto_restart_enabled}
        except Exception as e:
            return {"status": "error", "message": f"Failed to toggle auto-restart: {e}"}
    
    def switch_mode(self, https: bool) -> Dict[str, Any]:
        """Switch between HTTP and HTTPS mode"""
        if self.dev_manager is None:
            return {"status": "error", "message": "Development manager not running"}
        
        try:
            if https:
                self.dev_manager.switch_to_https_mode()
                mode = "HTTPS"
            else:
                self.dev_manager.switch_to_http_mode()
                mode = "HTTP"
            
            return {"status": "success", "message": f"Switched to {mode} mode"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to switch mode: {e}"}
    
    def read_log_file(self, lines: int = 50) -> Dict[str, Any]:
        """Read the last N lines from the dev_manager.log file"""
        log_file_path = Path(__file__).parent / "dev_manager.log"
        
        try:
            if not log_file_path.exists():
                return {"status": "error", "message": "Log file does not exist"}
            
            # Read the file and get the last N lines
            with open(log_file_path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            
            # Clean up the lines and prepare for return
            log_entries = []
            for line in last_lines:
                line = line.strip()
                if line:  # Skip empty lines
                    log_entries.append(line)
            
            return {
                "status": "success",
                "log_file": str(log_file_path),
                "total_lines_in_file": len(all_lines),
                "lines_returned": len(log_entries),
                "logs": log_entries
            }
            
        except Exception as e:
            return {"status": "error", "message": f"Failed to read log file: {e}"}

# Initialize the MCP server and development manager
server = Server("makermatrix-dev-manager")
dev_manager = DevManagerMCPServer()

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List all available tools"""
    return [
        Tool(
            name="start_dev_manager",
            description="Start the development manager",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="stop_dev_manager", 
            description="Stop the development manager",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_dev_status",
            description="Get current status of all development services",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="start_backend",
            description="Start the FastAPI backend server",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="stop_backend",
            description="Stop the FastAPI backend server",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="restart_backend",
            description="Restart the FastAPI backend server",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="start_frontend",
            description="Start the React frontend development server",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="stop_frontend",
            description="Stop the React frontend development server",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="restart_frontend",
            description="Restart the React frontend development server",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="start_all_servers",
            description="Start both backend and frontend servers",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="stop_all_servers",
            description="Stop both backend and frontend servers", 
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="build_frontend",
            description="Build the frontend for production",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_logs",
            description="Get logs from the development servers",
            inputSchema={
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "enum": ["all", "backend", "frontend", "errors"],
                        "default": "all",
                        "description": "Which service logs to retrieve"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 100,
                        "minimum": 1,
                        "maximum": 1000,
                        "description": "Maximum number of log entries to return"
                    },
                    "search": {
                        "type": "string",
                        "description": "Search term to filter logs"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="clear_logs",
            description="Clear all development server logs",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="health_check",
            description="Perform a health check on the backend server",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="toggle_auto_restart",
            description="Toggle automatic restart on file changes",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="switch_mode",
            description="Switch between HTTP and HTTPS mode",
            inputSchema={
                "type": "object",
                "properties": {
                    "https": {
                        "type": "boolean",
                        "description": "True for HTTPS mode, False for HTTP mode"
                    }
                },
                "required": ["https"]
            }
        ),
        Tool(
            name="read_log_file",
            description="Read the last N lines from the dev_manager.log file",
            inputSchema={
                "type": "object",
                "properties": {
                    "lines": {
                        "type": "integer",
                        "default": 50,
                        "minimum": 1,
                        "maximum": 500,
                        "description": "Number of lines to read from the end of the log file"
                    }
                },
                "required": []
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    """Handle tool calls"""
    try:
        if name == "start_dev_manager":
            result = dev_manager.start_manager()
        elif name == "stop_dev_manager":
            result = dev_manager.stop_manager()
        elif name == "get_dev_status":
            result = dev_manager.get_status()
        elif name == "start_backend":
            result = dev_manager.start_backend()
        elif name == "stop_backend":
            result = dev_manager.stop_backend()
        elif name == "restart_backend":
            result = dev_manager.restart_backend()
        elif name == "start_frontend":
            result = dev_manager.start_frontend()
        elif name == "stop_frontend":
            result = dev_manager.stop_frontend()
        elif name == "restart_frontend":
            result = dev_manager.restart_frontend()
        elif name == "start_all_servers":
            result = dev_manager.start_all()
        elif name == "stop_all_servers":
            result = dev_manager.stop_all()
        elif name == "build_frontend":
            result = dev_manager.build_frontend()
        elif name == "get_logs":
            service = arguments.get("service", "all")
            limit = arguments.get("limit", 100)
            search = arguments.get("search")
            result = dev_manager.get_logs(service, limit, search)
        elif name == "clear_logs":
            result = dev_manager.clear_logs()
        elif name == "health_check":
            result = dev_manager.health_check()
        elif name == "toggle_auto_restart":
            result = dev_manager.toggle_auto_restart()
        elif name == "switch_mode":
            https = arguments.get("https", True)
            result = dev_manager.switch_mode(https)
        elif name == "read_log_file":
            lines = arguments.get("lines", 50)
            result = dev_manager.read_log_file(lines)
        else:
            result = {"status": "error", "message": f"Unknown tool: {name}"}
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}")
        return [TextContent(type="text", text=json.dumps({
            "status": "error",
            "message": f"Tool execution failed: {e}"
        }, indent=2))]

async def main():
    """Main entry point"""
    logger.info("Starting MakerMatrix Development Manager MCP Server")
    
    try:
        # Use stdio transport
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())