"""
Printer Discovery Task - Background task for discovering available printers.
"""

import asyncio
import socket
import subprocess
import time
import threading
from typing import Dict, List, Any
import ipaddress

from MakerMatrix.models.task_models import TaskStatus, UpdateTaskRequest
from MakerMatrix.tasks.base_task import BaseTask


class PrinterDiscoveryTask(BaseTask):
    """Task for discovering available printers on network and USB."""
    
    def __init__(self, task_service=None):
        super().__init__(task_service)
        self.discovered_printers = []
        self.discovery_lock = threading.Lock()
    
    @property
    def task_type(self) -> str:
        return "printer_discovery"
    
    @property
    def name(self) -> str:
        return "Printer Discovery"
    
    @property
    def description(self) -> str:
        return "Scan network and USB for available printers"
    
    async def execute(self, task: 'TaskModel') -> Dict[str, Any]:
        """Execute the printer discovery task."""
        try:
            await self._update_task_progress(task, 0, "Starting printer discovery...")
            
            # Get configuration from task input
            input_data = task.get_input_data() or {}
            scan_network = input_data.get("scan_network", True)
            scan_usb = input_data.get("scan_usb", True)
            network_ranges = input_data.get("network_ranges", ["192.168.1.0/24"])
            timeout_seconds = input_data.get("timeout_seconds", 30)
            
            # Get supported drivers
            drivers = await self._get_supported_drivers()
            
            await self._update_task_progress(task, 10, "Loading driver information...")
            
            # Start discovery processes
            discovery_tasks = []
            
            if scan_usb:
                await self._update_task_progress(task, 20, "Scanning USB devices...")
                usb_async_task = asyncio.create_task(self._scan_usb_printers(task, drivers))
                discovery_tasks.append(usb_async_task)
            
            if scan_network:
                await self._update_task_progress(task, 30, "Starting network discovery...")
                network_async_task = asyncio.create_task(self._scan_network_printers(task, drivers, network_ranges))
                discovery_tasks.append(network_async_task)
            
            # Wait for all discovery tasks with timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(*discovery_tasks, return_exceptions=True),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                self.logger.warning(f"Discovery timeout after {timeout_seconds} seconds")
            
            await self._update_task_progress(task, 90, "Finalizing results...")
            
            # Sort and deduplicate results
            unique_printers = self._deduplicate_printers(self.discovered_printers)
            unique_printers.sort(key=lambda p: (p.get("driver_type", ""), p.get("ip", ""), p.get("identifier", "")))
            
            await self._update_task_progress(task, 100, f"Discovery complete - found {len(unique_printers)} printers")
            
            # Prepare result data
            result = {
                "discovered_printers": unique_printers,
                "discovery_time_ms": int(timeout_seconds * 1000),
                "scan_info": {
                    "network_ranges_scanned": network_ranges if scan_network else [],
                    "usb_scan_attempted": scan_usb,
                    "drivers_checked": [d["name"] for d in drivers],
                    "total_found": len(unique_printers),
                    "network_printers": len([p for p in unique_printers if p.get("backend") == "network"]),
                    "usb_printers": len([p for p in unique_printers if p.get("backend") in ["linux_kernel", "pyusb"]])
                }
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Printer discovery failed: {e}")
            raise
    
    async def _get_supported_drivers(self) -> List[Dict[str, Any]]:
        """Get supported printer drivers."""
        # This would normally call the printer routes, but we'll inline it here
        # to avoid circular imports
        return [
            {
                "id": "brother_ql",
                "name": "Brother QL Series",
                "supported_models": ["QL-500", "QL-550", "QL-570", "QL-700", "QL-710W", "QL-720NW", "QL-800", "QL-810W", "QL-820NWB", "QL-1100", "QL-1110NWB"],
                "backends": ["network", "linux_kernel", "pyusb"],
                "backend_options": {
                    "network": {
                        "default_port": 9100,
                        "identifier_format": "tcp://IP:PORT",
                        "example": "tcp://192.168.1.100:9100"
                    }
                }
            },
            {
                "id": "mock_thermal",
                "name": "Mock Thermal Printer", 
                "supported_models": ["ThermalPrint-X1", "ThermalPrint-X2", "ThermalPrint-Pro"],
                "backends": ["serial", "network", "usb"],
                "backend_options": {
                    "network": {
                        "default_port": 9100,
                        "identifier_format": "IP:PORT",
                        "example": "192.168.1.200:9100"
                    }
                }
            }
        ]
    
    async def _scan_usb_printers(self, task: 'TaskModel', drivers: List[Dict[str, Any]]):
        """Scan for USB printers."""
        try:
            await self._update_task_progress(task, 25, "Scanning USB devices...")
            
            # Run lsusb command
            result = await asyncio.create_subprocess_exec(
                'lsusb',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                lines = stdout.decode().split('\n')
                for line in lines:
                    if '04f9:' in line.lower() or 'brother' in line.lower():
                        with self.discovery_lock:
                            self.discovered_printers.append({
                                "name": "USB Brother QL Printer",
                                "identifier": "/dev/usb/lp0",
                                "driver_type": "brother_ql",
                                "model": "QL-800",
                                "status": "detected",
                                "backend": "linux_kernel",
                                "discovery_method": "usb_scan",
                                "usb_info": line.strip()
                            })
        except Exception as e:
            self.logger.warning(f"USB scanning failed: {e}")
    
    async def _scan_network_printers(self, task: 'TaskModel', drivers: List[Dict[str, Any]], network_ranges: List[str]):
        """Scan network for printers."""
        try:
            # Get all network-capable drivers
            network_drivers = [d for d in drivers if "network" in d.get("backends", [])]
            
            if not network_drivers:
                self.logger.info("No network-capable drivers found")
                return
            
            total_ips = 0
            for range_str in network_ranges:
                try:
                    network = ipaddress.ip_network(range_str, strict=False)
                    total_ips += network.num_addresses
                except:
                    continue
            
            scanned_ips = 0
            
            for range_str in network_ranges:
                try:
                    network = ipaddress.ip_network(range_str, strict=False)
                    await self._update_task_progress(
                        task, 30 + int(40 * scanned_ips / total_ips), 
                        f"Scanning network {range_str}..."
                    )
                    
                    # Scan this network range
                    async_tasks = []
                    for ip in network.hosts():
                        ip_str = str(ip)
                        for driver in network_drivers:
                            port = driver.get("backend_options", {}).get("network", {}).get("default_port", 9100)
                            async_task = asyncio.create_task(self._check_network_printer(ip_str, port, driver))
                            async_tasks.append(async_task)
                        
                        scanned_ips += 1
                        
                        # Update progress periodically
                        if scanned_ips % 10 == 0:
                            progress = 30 + int(40 * scanned_ips / total_ips)
                            await self._update_task_progress(task, progress, f"Scanning {ip_str}...")
                    
                    # Wait for this range to complete with timeout
                    try:
                        await asyncio.wait_for(asyncio.gather(*async_tasks, return_exceptions=True), timeout=10)
                    except asyncio.TimeoutError:
                        self.logger.warning(f"Network scan timeout for range {range_str}")
                        
                except Exception as e:
                    self.logger.warning(f"Failed to scan network range {range_str}: {e}")
            
            await self._update_task_progress(task, 70, "Network scan complete")
            
        except Exception as e:
            self.logger.error(f"Network scanning failed: {e}")
    
    async def _check_network_printer(self, ip: str, port: int, driver_info: Dict[str, Any]):
        """Check if a printer is available at the given IP and port, and try to identify it."""
        try:
            # Try to connect and identify the printer
            future = asyncio.get_event_loop().run_in_executor(
                None, self._sync_identify_printer, ip, port, driver_info
            )
            
            printer_info = await asyncio.wait_for(future, timeout=3)
            
            if printer_info:
                with self.discovery_lock:
                    self.discovered_printers.append(printer_info)
                    
        except Exception:
            pass  # No printer at this address
    
    def _sync_identify_printer(self, ip: str, port: int, driver_info: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous printer identification."""
        try:
            sock = socket.create_connection((ip, port), timeout=2)
            
            # Try different identification methods based on driver type
            identification_result = self._try_printer_identification(sock, driver_info)
            
            sock.close()
            
            if identification_result:
                return {
                    "name": identification_result.get("name", f"Network {driver_info['name']}"),
                    "ip": ip,
                    "port": port,
                    "identifier": f"tcp://{ip}:{port}",
                    "driver_type": driver_info["id"],
                    "model": identification_result.get("model", driver_info["supported_models"][0] if driver_info["supported_models"] else "Unknown"),
                    "status": "identified" if identification_result.get("identified") else "detected",
                    "backend": "network",
                    "discovery_method": "identification" if identification_result.get("identified") else "port_scan",
                    "printer_response": identification_result.get("response_data"),
                    "identification_method": identification_result.get("method"),
                    "firmware_version": identification_result.get("firmware_version"),
                    "serial_number": identification_result.get("serial_number")
                }
            else:
                # Just port detection
                return {
                    "name": f"Network {driver_info['name']} (Port Open)",
                    "ip": ip,
                    "port": port,
                    "identifier": f"tcp://{ip}:{port}",
                    "driver_type": driver_info["id"],
                    "model": driver_info["supported_models"][0] if driver_info["supported_models"] else "Unknown",
                    "status": "detected",
                    "backend": "network",
                    "discovery_method": "port_scan"
                }
                
        except:
            return None
    
    def _try_printer_identification(self, sock: socket.socket, driver_info: Dict[str, Any]) -> Dict[str, Any]:
        """Try various methods to identify the printer."""
        sock.settimeout(2)
        
        # Try different identification methods based on driver type
        if driver_info["id"] == "brother_ql":
            return self._identify_brother_ql(sock)
        elif driver_info["id"] == "mock_thermal":
            return self._identify_mock_thermal(sock)
        else:
            return self._identify_generic_printer(sock)
    
    def _identify_brother_ql(self, sock: socket.socket) -> Dict[str, Any]:
        """Try to identify a Brother QL printer."""
        try:
            # Brother QL status command sequence
            commands = [
                # ESC @ - Initialize printer
                (b'\x1b\x40', "ESC @ (Initialize)"),
                # ESC i S - Status information request  
                (b'\x1b\x69\x53', "ESC i S (Status)"),
                # Get printer info
                (b'\x1b\x69\x4c', "ESC i L (Model info)"),
            ]
            
            best_result = None
            
            for command, description in commands:
                try:
                    sock.send(command)
                    time.sleep(0.2)  # Give printer time to respond
                    
                    response = sock.recv(1024)
                    if response:
                        # Parse Brother QL response
                        result = self._parse_brother_response(response, description)
                        if result and result.get("identified"):
                            return result
                        elif result:
                            best_result = result
                            
                except Exception as e:
                    continue
            
            return best_result or {"method": "brother_ql_attempt", "identified": False}
            
        except Exception:
            return {"method": "brother_ql_failed", "identified": False}
    
    def _identify_mock_thermal(self, sock: socket.socket) -> Dict[str, Any]:
        """Try to identify a mock thermal printer (for testing)."""
        try:
            # Mock thermal printer commands (these won't actually work)
            commands = [
                (b'\x10\x04\x01', "Status request"),
                (b'\x1d\x49\x01', "Model ID"),
            ]
            
            for command, description in commands:
                try:
                    sock.send(command)
                    time.sleep(0.1)
                    response = sock.recv(1024)
                    if response:
                        return {
                            "name": "Mock Thermal Printer",
                            "model": "ThermalPrint-X1", 
                            "method": f"mock_thermal_{description}",
                            "identified": True,
                            "response_data": response.hex()
                        }
                except:
                    continue
                    
            return {"method": "mock_thermal_attempt", "identified": False}
            
        except Exception:
            return {"method": "mock_thermal_failed", "identified": False}
    
    def _identify_generic_printer(self, sock: socket.socket) -> Dict[str, Any]:
        """Try generic printer identification methods."""
        try:
            # Try common printer commands
            commands = [
                # ESC @ - Initialize (most printers)
                (b'\x1b\x40', "ESC @ (Initialize)"),
                # ESC ? - Status request
                (b'\x1b\x3f', "ESC ? (Status)"),
                # ESC t - Select character table (many thermal printers)
                (b'\x1b\x74\x00', "ESC t (Character table)"),
                # GS I - Information command (ESC/POS)
                (b'\x1d\x49\x01', "GS I (Printer ID)"),
            ]
            
            for command, description in commands:
                try:
                    sock.send(command)
                    time.sleep(0.1)
                    response = sock.recv(1024)
                    if response and len(response) > 0:
                        return {
                            "method": f"generic_{description}",
                            "identified": True,
                            "response_data": response.hex(),
                            "response_length": len(response)
                        }
                except:
                    continue
                    
            return {"method": "generic_attempt", "identified": False}
            
        except Exception:
            return {"method": "generic_failed", "identified": False}
    
    def _parse_brother_response(self, response: bytes, command: str) -> Dict[str, Any]:
        """Parse response from Brother QL printer."""
        try:
            if len(response) == 0:
                return None
                
            # Brother QL status response parsing
            # This is a simplified parser - real Brother QL responses are more complex
            result = {
                "method": f"brother_ql_{command}",
                "identified": True,
                "response_data": response.hex(),
                "response_length": len(response)
            }
            
            # Try to extract model information from response
            if b'QL-' in response:
                # Look for QL model numbers
                response_str = response.decode('ascii', errors='ignore')
                import re
                model_match = re.search(r'QL-(\d+\w*)', response_str)
                if model_match:
                    result["model"] = f"QL-{model_match.group(1)}"
                    result["name"] = f"Brother QL-{model_match.group(1)}"
            
            # Check for status bytes (Brother QL specific)
            if len(response) >= 32:  # Brother QL status is typically 32 bytes
                # Parse status information
                status_byte = response[0] if len(response) > 0 else 0
                if status_byte == 0x00:
                    result["printer_status"] = "ready"
                elif status_byte == 0x01:
                    result["printer_status"] = "error"
                else:
                    result["printer_status"] = f"unknown_{status_byte:02x}"
            
            return result
            
        except Exception:
            return {
                "method": f"brother_ql_{command}_parse_failed",
                "identified": False,
                "response_data": response.hex()
            }
    
    def _deduplicate_printers(self, printers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate printer entries."""
        seen = set()
        unique = []
        
        for printer in printers:
            # Create a unique key based on identifier and driver type
            key = (printer.get("identifier", ""), printer.get("driver_type", ""))
            if key not in seen:
                seen.add(key)
                unique.append(printer)
        
        return unique
    
    async def _update_task_progress(self, task: 'TaskModel', percentage: int, step: str):
        """Update task progress"""
        if self.task_service:
            try:
                update_request = UpdateTaskRequest(
                    progress_percentage=percentage,
                    current_step=step
                )
                await self.task_service.update_task(task.id, update_request)
            except Exception as e:
                self.logger.warning(f"Failed to update task progress: {e}")


# The task will be automatically discovered and registered by the task system