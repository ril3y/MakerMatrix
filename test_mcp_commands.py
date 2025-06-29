#!/usr/bin/env python3
"""Test MCP server commands"""

import json
import subprocess
import sys

def test_mcp_server():
    """Test the MCP server by sending proper initialization and commands"""
    
    # Start the MCP server process
    process = subprocess.Popen(
        ["/home/ril3y/MakerMatrix/venv_test/bin/python", "mcp_dev_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd="/home/ril3y/MakerMatrix"
    )
    
    try:
        # Initialize the server
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            },
            "id": 1
        }
        
        # Send initialization
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        
        # Wait for initialization response
        response = process.stdout.readline()
        print("Initialization response:", response.strip())
        
        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        
        process.stdin.write(json.dumps(initialized_notification) + "\n")
        process.stdin.flush()
        
        # Now start the dev manager
        start_manager_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "start_dev_manager",
                "arguments": {}
            },
            "id": 2
        }
        
        process.stdin.write(json.dumps(start_manager_request) + "\n")
        process.stdin.flush()
        
        # Wait for response
        response = process.stdout.readline()
        print("Start manager response:", response.strip())
        
        # Start both servers
        start_all_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "start_all_servers",
                "arguments": {}
            },
            "id": 3
        }
        
        process.stdin.write(json.dumps(start_all_request) + "\n")
        process.stdin.flush()
        
        # Wait for response
        response = process.stdout.readline()
        print("Start all servers response:", response.strip())
        
        # Get status
        status_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "get_dev_status",
                "arguments": {}
            },
            "id": 4
        }
        
        process.stdin.write(json.dumps(status_request) + "\n")
        process.stdin.flush()
        
        # Wait for response
        response = process.stdout.readline()
        print("Status response:", response.strip())
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        process.terminate()
        process.wait()

if __name__ == "__main__":
    test_mcp_server()