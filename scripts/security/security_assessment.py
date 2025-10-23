#!/usr/bin/env python3
"""
Comprehensive Security Assessment for MakerMatrix API
IMPORTANT: This is a security audit script - DO NOT run destructive operations
"""

import requests
import json
import sys
from typing import Dict, List, Tuple
from urllib.parse import urljoin
import time

# Disable SSL warnings for self-signed certificates
requests.packages.urllib3.disable_warnings()


class SecurityAssessment:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        self.session.verify = False
        self.findings = []

    def add_finding(
        self,
        severity: str,
        title: str,
        description: str,
        location: str,
        poc: str,
        impact: str,
        recommendation: str,
        cwe: str = "",
        owasp: str = "",
    ):
        """Add a security finding"""
        self.findings.append(
            {
                "severity": severity,
                "title": title,
                "description": description,
                "location": location,
                "poc": poc,
                "impact": impact,
                "recommendation": recommendation,
                "cwe": cwe,
                "owasp": owasp,
            }
        )

    def print_finding(self, finding: Dict):
        """Print a finding in a formatted way"""
        severity_colors = {"CRITICAL": "\033[91m", "HIGH": "\033[91m", "MEDIUM": "\033[93m", "LOW": "\033[94m"}
        color = severity_colors.get(finding["severity"], "\033[0m")
        reset = "\033[0m"

        print(f"\n{color}[{finding['severity']}]{reset} {finding['title']}")
        print(f"Location: {finding['location']}")
        if finding["cwe"]:
            print(f"CWE: {finding['cwe']}")
        if finding["owasp"]:
            print(f"OWASP: {finding['owasp']}")
        print(f"\nDescription:\n{finding['description']}")
        print(f"\nImpact:\n{finding['impact']}")
        print(f"\nProof of Concept:\n{finding['poc']}")
        print(f"\nRecommendation:\n{finding['recommendation']}")
        print("-" * 80)

    # ========== AUTHENTICATION TESTING ==========

    def test_authentication_bypass(self):
        """Test accessing protected endpoints without authentication"""
        print("\n=== Testing Authentication Bypass ===")

        protected_endpoints = [
            ("GET", "/api/parts/get_all_parts"),
            ("GET", "/api/users/me"),
            ("GET", "/api/tasks/"),
            ("GET", "/api/backup/list"),
            ("GET", "/api/analytics/dashboard/summary"),
        ]

        vulnerable = []
        for method, endpoint in protected_endpoints:
            url = urljoin(self.base_url, endpoint)
            try:
                response = requests.request(method, url, verify=False, timeout=5)
                if response.status_code == 200:
                    vulnerable.append((method, endpoint, response.status_code))
                    print(f"  [!] {method} {endpoint} - Accessible without auth (HTTP {response.status_code})")
                elif response.status_code == 401:
                    print(f"  [✓] {method} {endpoint} - Properly protected (HTTP 401)")
                else:
                    print(f"  [?] {method} {endpoint} - HTTP {response.status_code}")
            except Exception as e:
                print(f"  [ERROR] {method} {endpoint} - {str(e)}")

        if vulnerable:
            self.add_finding(
                severity="CRITICAL",
                title="Authentication Bypass - Protected Endpoints Accessible Without Credentials",
                description=f"Found {len(vulnerable)} protected endpoints that are accessible without authentication.",
                location=", ".join([f"{m} {e}" for m, e, _ in vulnerable]),
                poc=f"curl -k {self.base_url}{vulnerable[0][1]}",
                impact="Unauthorized users can access sensitive data and functionality without authentication.",
                recommendation="Ensure all protected endpoints enforce authentication via the security decorator.",
                cwe="CWE-306: Missing Authentication for Critical Function",
                owasp="A01:2021 - Broken Access Control",
            )

    def test_jwt_validation(self):
        """Test JWT token validation"""
        print("\n=== Testing JWT Validation ===")

        # Test with valid token
        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = urljoin(self.base_url, "/api/users/me")

        try:
            response = requests.get(url, headers=headers, verify=False, timeout=5)
            if response.status_code == 200:
                print(f"  [✓] Valid token accepted (HTTP 200)")
                user_data = response.json()
                print(f"      User: {user_data.get('data', {}).get('username', 'unknown')}")
            else:
                print(f"  [!] Valid token rejected (HTTP {response.status_code})")
        except Exception as e:
            print(f"  [ERROR] Valid token test - {str(e)}")

        # Test with invalid token
        invalid_tokens = [
            "invalid_token",
            "Bearer invalid_token",
            self.api_key + "x",  # Modified valid token
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.invalid",  # Malformed JWT
        ]

        for invalid_token in invalid_tokens:
            headers = {"Authorization": f"Bearer {invalid_token}"}
            try:
                response = requests.get(url, headers=headers, verify=False, timeout=5)
                if response.status_code == 401:
                    print(f"  [✓] Invalid token rejected: {invalid_token[:20]}... (HTTP 401)")
                else:
                    print(f"  [!] Invalid token accepted: {invalid_token[:20]}... (HTTP {response.status_code})")
                    self.add_finding(
                        severity="HIGH",
                        title="JWT Validation Bypass",
                        description=f"Invalid JWT token was accepted by the API.",
                        location="/api/users/me (and potentially other endpoints)",
                        poc=f"curl -k -H 'Authorization: Bearer {invalid_token}' {url}",
                        impact="Attackers could forge authentication tokens and gain unauthorized access.",
                        recommendation="Ensure proper JWT signature validation and implement token expiration checks.",
                        cwe="CWE-347: Improper Verification of Cryptographic Signature",
                    )
            except Exception as e:
                print(f"  [ERROR] Invalid token test - {str(e)}")

    def test_role_based_access(self):
        """Test role-based access control"""
        print("\n=== Testing Role-Based Access Control ===")

        # Test admin-only endpoints
        admin_endpoints = [
            ("GET", "/api/users/all"),
            ("GET", "/api/api-keys/admin/all"),
            ("GET", "/api/backup/list"),
            ("POST", "/api/tasks/worker/start"),
            ("POST", "/api/tasks/worker/stop"),
        ]

        headers = {"Authorization": f"Bearer {self.api_key}"}

        for method, endpoint in admin_endpoints:
            url = urljoin(self.base_url, endpoint)
            try:
                response = requests.request(method, url, headers=headers, verify=False, timeout=5)
                print(f"  {method} {endpoint} - HTTP {response.status_code}")

                if response.status_code == 403:
                    print(f"      [✓] Access properly restricted")
                elif response.status_code == 200:
                    print(f"      [i] Access granted (check if user has admin role)")
                    # This might be expected if test key has admin privileges
            except Exception as e:
                print(f"  [ERROR] {method} {endpoint} - {str(e)}")

    # ========== IDOR TESTING ==========

    def test_idor_vulnerabilities(self):
        """Test for Insecure Direct Object Reference vulnerabilities"""
        print("\n=== Testing IDOR Vulnerabilities ===")

        headers = {"Authorization": f"Bearer {self.api_key}"}

        # Test part access
        print("\n  Testing Part Access:")
        for part_id in [1, 2, 999, -1, 0]:
            url = urljoin(self.base_url, f"/api/parts/get_part?part_id={part_id}")
            try:
                response = requests.get(url, headers=headers, verify=False, timeout=5)
                print(f"    Part ID {part_id}: HTTP {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    # Check if proper authorization is enforced
                    print(f"      [i] Part data retrieved - verify ownership check")
            except Exception as e:
                print(f"    Part ID {part_id}: ERROR - {str(e)}")

        # Test user access
        print("\n  Testing User Access:")
        for user_id in [1, 2, 999, -1, 0]:
            url = urljoin(self.base_url, f"/api/users/{user_id}")
            try:
                response = requests.get(url, headers=headers, verify=False, timeout=5)
                print(f"    User ID {user_id}: HTTP {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    print(f"      [!] User data accessible - potential IDOR")
                elif response.status_code == 403:
                    print(f"      [✓] Access properly restricted")
            except Exception as e:
                print(f"    User ID {user_id}: ERROR - {str(e)}")

        # Test task access
        print("\n  Testing Task Access:")
        for task_id in [1, 2, 999]:
            url = urljoin(self.base_url, f"/api/tasks/{task_id}")
            try:
                response = requests.get(url, headers=headers, verify=False, timeout=5)
                print(f"    Task ID {task_id}: HTTP {response.status_code}")

                if response.status_code == 200:
                    print(f"      [!] Task data accessible - verify ownership check")
            except Exception as e:
                print(f"    Task ID {task_id}: ERROR - {str(e)}")

    # ========== INPUT VALIDATION TESTING ==========

    def test_sql_injection(self):
        """Test for SQL injection vulnerabilities"""
        print("\n=== Testing SQL Injection ===")

        headers = {"Authorization": f"Bearer {self.api_key}"}

        sql_payloads = [
            "' OR '1'='1",
            "1' OR '1'='1",
            "' OR 1=1--",
            "admin'--",
            "1; DROP TABLE parts--",
            "1' UNION SELECT NULL--",
        ]

        # Test search endpoints
        print("\n  Testing Search Endpoints:")
        for payload in sql_payloads:
            url = urljoin(self.base_url, f"/api/parts/search_text?query={payload}")
            try:
                response = requests.get(url, headers=headers, verify=False, timeout=5)

                if response.status_code == 500:
                    print(f"    [!] Payload caused 500 error: {payload}")
                    self.add_finding(
                        severity="HIGH",
                        title="Potential SQL Injection Vulnerability",
                        description=f"SQL injection payload caused server error, indicating possible vulnerability.",
                        location="/api/parts/search_text",
                        poc=f"curl -k -H 'Authorization: Bearer {self.api_key}' '{url}'",
                        impact="Attackers could read, modify, or delete database contents.",
                        recommendation="Use parameterized queries and input validation. Never concatenate user input into SQL.",
                        cwe="CWE-89: SQL Injection",
                        owasp="A03:2021 - Injection",
                    )
                elif response.status_code == 200:
                    data = response.json()
                    # Check if payload was interpreted
                    print(f"    Payload returned 200: {payload[:30]}...")
                else:
                    print(f"    Payload HTTP {response.status_code}: {payload[:30]}...")
            except Exception as e:
                print(f"    ERROR with payload {payload[:30]}...: {str(e)}")

    def test_command_injection(self):
        """Test for command injection in file operations"""
        print("\n=== Testing Command Injection ===")

        # Test file download endpoints with path traversal
        headers = {"Authorization": f"Bearer {self.api_key}"}

        cmd_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "../../.env",
            "; ls -la",
            "| cat /etc/passwd",
            "`whoami`",
        ]

        print("\n  Testing File Access:")
        for payload in cmd_payloads:
            url = urljoin(self.base_url, f"/api/utility/static/datasheets/{payload}")
            try:
                response = requests.get(url, headers=headers, verify=False, timeout=5)

                if response.status_code == 200:
                    content = response.text[:100]
                    print(f"    [!] Payload succeeded: {payload}")
                    print(f"        Content preview: {content}...")

                    if "root:" in content or "admin" in content.lower():
                        self.add_finding(
                            severity="CRITICAL",
                            title="Path Traversal / Directory Traversal",
                            description="Able to access files outside intended directory using path traversal.",
                            location="/api/utility/static/datasheets/",
                            poc=f"curl -k -H 'Authorization: Bearer {self.api_key}' '{url}'",
                            impact="Attackers can read sensitive files including configuration, passwords, and source code.",
                            recommendation="Validate and sanitize file paths. Use allowlist of permitted filenames. Never pass user input directly to file operations.",
                            cwe="CWE-22: Path Traversal",
                            owasp="A01:2021 - Broken Access Control",
                        )
                else:
                    print(f"    Payload HTTP {response.status_code}: {payload}")
            except Exception as e:
                print(f"    ERROR: {str(e)}")

    def test_xss_vulnerabilities(self):
        """Test for XSS vulnerabilities in API responses"""
        print("\n=== Testing XSS Vulnerabilities ===")

        headers = {"Authorization": f"Bearer {self.api_key}"}

        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
        ]

        # Test part creation with XSS payloads
        print("\n  Testing Part Creation:")
        for payload in xss_payloads:
            data = {"name": payload, "description": payload, "part_number": f"TEST-XSS-{hash(payload)}", "quantity": 1}

            url = urljoin(self.base_url, "/api/parts/add_part")
            try:
                response = requests.post(url, headers=headers, json=data, verify=False, timeout=5)

                if response.status_code == 200:
                    resp_data = response.json()
                    # Check if payload is reflected unescaped
                    if payload in str(resp_data):
                        print(f"    [!] XSS payload reflected: {payload[:30]}...")
                        # Note: This doesn't mean XSS is exploitable - depends on frontend rendering
                        print(f"        [i] Payload stored but exploitation depends on frontend handling")
                    else:
                        print(f"    [✓] Payload escaped/sanitized: {payload[:30]}...")
                else:
                    print(f"    HTTP {response.status_code} for payload: {payload[:30]}...")
            except Exception as e:
                print(f"    ERROR: {str(e)}")

    # ========== FILE UPLOAD TESTING ==========

    def test_file_upload_security(self):
        """Test file upload security"""
        print("\n=== Testing File Upload Security ===")

        headers = {"Authorization": f"Bearer {self.api_key}"}

        # Test malicious file uploads
        test_files = [
            ("shell.php", '<?php system($_GET["cmd"]); ?>', "application/x-php"),
            ("shell.jsp", '<% Runtime.getRuntime().exec(request.getParameter("cmd")); %>', "application/x-jsp"),
            ("test.exe", "MZ\x90\x00", "application/x-msdownload"),
            ("test.svg", '<svg onload=alert("XSS")></svg>', "image/svg+xml"),
            ("../../../etc/passwd", "root:x:0:0", "text/plain"),
        ]

        url = urljoin(self.base_url, "/api/utility/upload_image")

        for filename, content, content_type in test_files:
            files = {"file": (filename, content, content_type)}

            try:
                response = requests.post(url, headers=headers, files=files, verify=False, timeout=5)

                if response.status_code == 200:
                    print(f"    [!] Uploaded: {filename} (type: {content_type})")
                    resp_data = response.json()
                    print(f"        Response: {resp_data}")

                    if ".php" in filename or ".jsp" in filename or ".exe" in filename:
                        self.add_finding(
                            severity="HIGH",
                            title="Unrestricted File Upload",
                            description=f"Successfully uploaded potentially malicious file: {filename}",
                            location="/api/utility/upload_image",
                            poc=f"curl -k -H 'Authorization: Bearer {self.api_key}' -F 'file=@{filename}' '{url}'",
                            impact="Attackers could upload webshells or malicious executables leading to remote code execution.",
                            recommendation="Implement strict file type validation, use allowlist of permitted extensions, store files outside webroot, scan uploads with antivirus.",
                            cwe="CWE-434: Unrestricted Upload of File with Dangerous Type",
                            owasp="A04:2021 - Insecure Design",
                        )
                elif response.status_code == 400:
                    print(f"    [✓] Rejected: {filename} (type: {content_type})")
                else:
                    print(f"    HTTP {response.status_code}: {filename}")
            except Exception as e:
                print(f"    ERROR uploading {filename}: {str(e)}")

    # ========== BACKUP SECURITY TESTING ==========

    def test_backup_security(self):
        """Test backup and download endpoint security"""
        print("\n=== Testing Backup Security ===")

        headers = {"Authorization": f"Bearer {self.api_key}"}

        # Test backup list access
        print("\n  Testing Backup List Access:")
        url = urljoin(self.base_url, "/api/backup/list")
        try:
            response = requests.get(url, headers=headers, verify=False, timeout=5)
            print(f"    HTTP {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"    [i] Backup list retrieved: {len(data.get('data', {}).get('backups', []))} backups")
            elif response.status_code == 403:
                print(f"    [✓] Access properly restricted to admin only")
        except Exception as e:
            print(f"    ERROR: {str(e)}")

        # Test backup download with path traversal
        print("\n  Testing Backup Download Path Traversal:")
        traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "../../.env",
            "../../requirements.txt",
        ]

        for payload in traversal_payloads:
            url = urljoin(self.base_url, f"/api/backup/download/{payload}")
            try:
                response = requests.get(url, headers=headers, verify=False, timeout=5)

                if response.status_code == 200:
                    print(f"    [!] Path traversal successful: {payload}")
                    self.add_finding(
                        severity="CRITICAL",
                        title="Path Traversal in Backup Download",
                        description=f"Able to download arbitrary files using path traversal in backup download endpoint.",
                        location="/api/backup/download/",
                        poc=f"curl -k -H 'Authorization: Bearer {self.api_key}' '{url}'",
                        impact="Attackers can download sensitive configuration files, source code, database files, and credentials.",
                        recommendation="Validate backup filenames against a whitelist. Use basename() to strip directory components. Store backups with random names.",
                        cwe="CWE-22: Path Traversal",
                        owasp="A01:2021 - Broken Access Control",
                    )
                else:
                    print(f"    [✓] Path traversal blocked: {payload} (HTTP {response.status_code})")
            except Exception as e:
                print(f"    ERROR: {str(e)}")

    # ========== SENSITIVE DATA EXPOSURE ==========

    def test_sensitive_data_exposure(self):
        """Test for sensitive data exposure in API responses"""
        print("\n=== Testing Sensitive Data Exposure ===")

        headers = {"Authorization": f"Bearer {self.api_key}"}

        # Test error messages
        print("\n  Testing Error Messages:")
        url = urljoin(self.base_url, "/api/parts/get_part?part_id=99999999")
        try:
            response = requests.get(url, headers=headers, verify=False, timeout=5)
            error_msg = response.text

            # Check for sensitive information in errors
            sensitive_patterns = ["traceback", "exception", "sql", "database", "password", "secret", "token"]
            found = [p for p in sensitive_patterns if p.lower() in error_msg.lower()]

            if found:
                print(f"    [!] Sensitive info in error message: {', '.join(found)}")
                self.add_finding(
                    severity="MEDIUM",
                    title="Sensitive Information in Error Messages",
                    description="Error messages contain sensitive technical details.",
                    location=url,
                    poc=f"curl -k -H 'Authorization: Bearer {self.api_key}' '{url}'",
                    impact="Information disclosure aids attackers in understanding system architecture and finding vulnerabilities.",
                    recommendation="Use generic error messages for clients. Log detailed errors server-side only.",
                    cwe="CWE-209: Information Exposure Through Error Messages",
                )
            else:
                print(f"    [✓] Error messages appear safe")
        except Exception as e:
            print(f"    ERROR: {str(e)}")

        # Test for credential exposure in config endpoints
        print("\n  Testing Credential Exposure:")
        config_endpoints = [
            "/api/suppliers/config/suppliers",
            "/api/ai/config",
            "/api/printer/printers",
        ]

        for endpoint in config_endpoints:
            url = urljoin(self.base_url, endpoint)
            try:
                response = requests.get(url, headers=headers, verify=False, timeout=5)

                if response.status_code == 200:
                    data = response.json()
                    resp_str = json.dumps(data)

                    # Check for exposed credentials
                    credential_patterns = ["password", "api_key", "secret", "token", "private_key"]
                    found = []

                    for pattern in credential_patterns:
                        if pattern in resp_str.lower():
                            # Check if value is masked
                            import re

                            matches = re.findall(rf'"{pattern}":\s*"([^"]+)"', resp_str, re.IGNORECASE)
                            for match in matches:
                                if match and match != "***" and match != "REDACTED" and not match.startswith("*"):
                                    found.append((pattern, match[:20]))

                    if found:
                        print(f"    [!] Exposed credentials in {endpoint}:")
                        for pattern, value in found:
                            print(f"        {pattern}: {value}...")
                    else:
                        print(f"    [✓] No exposed credentials in {endpoint}")
            except Exception as e:
                print(f"    ERROR: {str(e)}")

    # ========== TASK API SECURITY ==========

    def test_task_api_security(self):
        """Test task API security (CAREFUL - HIGH RISK)"""
        print("\n=== Testing Task API Security (Read-Only Tests) ===")

        headers = {"Authorization": f"Bearer {self.api_key}"}

        # Test task list access
        print("\n  Testing Task List Access:")
        url = urljoin(self.base_url, "/api/tasks/")
        try:
            response = requests.get(url, headers=headers, verify=False, timeout=5)
            print(f"    HTTP {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                tasks = data.get("data", {}).get("tasks", [])
                print(f"    [i] Retrieved {len(tasks)} tasks")
        except Exception as e:
            print(f"    ERROR: {str(e)}")

        # Test task capabilities (safe read-only)
        print("\n  Testing Task Capabilities:")
        url = urljoin(self.base_url, "/api/tasks/capabilities/suppliers")
        try:
            response = requests.get(url, headers=headers, verify=False, timeout=5)
            print(f"    HTTP {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"    [✓] Capabilities endpoint accessible")
        except Exception as e:
            print(f"    ERROR: {str(e)}")

        # Test security permissions
        print("\n  Testing Task Security Permissions:")
        url = urljoin(self.base_url, "/api/tasks/security/permissions")
        try:
            response = requests.get(url, headers=headers, verify=False, timeout=5)
            print(f"    HTTP {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"    [i] Security permissions: {json.dumps(data.get('data', {}), indent=2)}")
        except Exception as e:
            print(f"    ERROR: {str(e)}")

        print("\n  [!] SKIPPING task creation tests to avoid triggering operations")
        print("      Manual testing required for task creation authorization")

    # ========== RATE LIMITING ==========

    def test_rate_limiting(self):
        """Test API rate limiting"""
        print("\n=== Testing Rate Limiting ===")

        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = urljoin(self.base_url, "/api/utility/get_counts")

        print("  Sending 50 rapid requests...")
        responses = []

        for i in range(50):
            try:
                response = requests.get(url, headers=headers, verify=False, timeout=5)
                responses.append(response.status_code)

                if response.status_code == 429:
                    print(f"    [✓] Rate limit enforced at request {i+1}")
                    break
            except Exception as e:
                print(f"    ERROR at request {i+1}: {str(e)}")
                break

        if 429 not in responses:
            print(f"    [!] No rate limiting detected after {len(responses)} requests")
            self.add_finding(
                severity="MEDIUM",
                title="Missing Rate Limiting",
                description="API does not implement rate limiting, allowing unlimited requests.",
                location="All API endpoints",
                poc=f'for i in {{1..100}}; do curl -k -H "Authorization: Bearer {self.api_key}" {url}; done',
                impact="Attackers can perform brute force attacks, denial of service, and resource exhaustion.",
                recommendation="Implement rate limiting per user/IP. Use exponential backoff. Consider using middleware like slowapi.",
                cwe="CWE-770: Allocation of Resources Without Limits or Throttling",
            )
        else:
            print(f"    [✓] Rate limiting appears to be working")

    # ========== WEBSOCKET SECURITY ==========

    def test_websocket_security(self):
        """Test WebSocket security"""
        print("\n=== Testing WebSocket Security ===")
        print("  [i] WebSocket testing requires ws/wss client - manual testing recommended")
        print("  [i] Endpoints to test: /ws/tasks, /ws/admin")
        print("  [i] Tests needed:")
        print("      - Authentication requirement")
        print("      - Authorization checks")
        print("      - Message injection")
        print("      - Cross-user data access")

    # ========== MAIN EXECUTION ==========

    def run_all_tests(self):
        """Run all security tests"""
        print("=" * 80)
        print("MAKERMATRIX SECURITY ASSESSMENT")
        print("=" * 80)
        print(f"Target: {self.base_url}")
        print(f"Test API Key: {self.api_key[:20]}...")
        print("=" * 80)

        try:
            self.test_authentication_bypass()
            self.test_jwt_validation()
            self.test_role_based_access()
            self.test_idor_vulnerabilities()
            self.test_sql_injection()
            self.test_command_injection()
            self.test_xss_vulnerabilities()
            self.test_file_upload_security()
            self.test_backup_security()
            self.test_sensitive_data_exposure()
            self.test_task_api_security()
            self.test_rate_limiting()
            self.test_websocket_security()

        except KeyboardInterrupt:
            print("\n\n[!] Assessment interrupted by user")

        print("\n" + "=" * 80)
        print("ASSESSMENT COMPLETE")
        print("=" * 80)

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print summary of findings"""
        print(f"\nTotal Findings: {len(self.findings)}")

        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

        for finding in self.findings:
            severity_counts[finding["severity"]] += 1

        print(f"  Critical: {severity_counts['CRITICAL']}")
        print(f"  High: {severity_counts['HIGH']}")
        print(f"  Medium: {severity_counts['MEDIUM']}")
        print(f"  Low: {severity_counts['LOW']}")

        if self.findings:
            print("\n" + "=" * 80)
            print("DETAILED FINDINGS")
            print("=" * 80)

            for finding in self.findings:
                self.print_finding(finding)

        return self.findings


if __name__ == "__main__":
    BASE_URL = "https://10.2.0.2:8443"
    API_KEY = os.getenv("MAKERMATRIX_API_KEY", "")  # Set in .env

    assessment = SecurityAssessment(BASE_URL, API_KEY)
    findings = assessment.run_all_tests()

    # Save findings to JSON
    with open("/home/ril3y/MakerMatrix/tests/security_findings.json", "w") as f:
        json.dump(findings, f, indent=2)

    print(f"\n[i] Findings saved to /home/ril3y/MakerMatrix/tests/security_findings.json")
