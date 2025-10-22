# Security Scripts

This directory contains security auditing and penetration testing scripts for the MakerMatrix API.

## ⚠️ IMPORTANT: These are AUDIT tools, not ATTACK tools

These scripts are for **authorized security testing only**. They help identify vulnerabilities so they can be fixed.

**DO NOT:**
- Run against production without authorization
- Use for malicious purposes
- Run destructive operations
- Attempt to bypass security controls maliciously

## Scripts

### `security_audit_tasks_api.py`

**Purpose:** Comprehensive security scanner for the Tasks API

**What it tests:**
- Authentication enforcement
- Authorization controls (RBAC)
- Task parameter validation
- Injection vulnerabilities (command, SQL, path traversal)
- SSRF protection
- Rate limiting
- Access control (IDOR prevention)
- WebSocket security

**Usage:**
```bash
cd /home/ril3y/MakerMatrix
python3 scripts/security/security_audit_tasks_api.py
```

**Output:**
- Console output with colored test results
- JSON report: `tests/security_audit_report.json`
- Identifies vulnerabilities with severity ratings
- Provides proof-of-concept examples

**Test API Key:** `REDACTED_API_KEY`

---

### `security_assessment.py`

**Purpose:** General security assessment tool for MakerMatrix API

**What it tests:**
- General API security posture
- Authentication mechanisms
- Common web vulnerabilities
- Security headers
- Input validation

**Usage:**
```bash
cd /home/ril3y/MakerMatrix
python3 scripts/security/security_assessment.py
```

**Features:**
- Automated vulnerability scanning
- Categorized findings (Critical, High, Medium, Low)
- Detailed remediation recommendations
- OWASP and CWE references

---

## Security Testing Workflow

### 1. Use Pytest Tests (Preferred)

For regular security testing and CI/CD, use the pytest suite:

```bash
# Run all security tests
./venv_test/bin/pytest tests/test_security_fixes.py -v

# Run critical tests only (fast)
./venv_test/bin/pytest tests/test_security_fixes.py -v -m critical
```

**Why pytest is better:**
- Integrated into CI/CD
- Fast execution
- Prevents regression
- Clear pass/fail status

### 2. Use Audit Scripts (Deep Testing)

Use these scripts for:
- Comprehensive security audits
- Finding new vulnerabilities
- Quarterly security reviews
- Pre-deployment validation

```bash
# Run comprehensive audit
python3 scripts/security/security_audit_tasks_api.py

# Review findings
cat tests/security_audit_report.json
```

---

## Current Security Status

**Last Audit:** October 22, 2025
**Vulnerabilities Found:** 9 CVEs
**Vulnerabilities Fixed:** 9/9 (100%)
**Risk Level:** LOW (10/100)

### All CVEs Fixed ✅

1. **CVE-001:** Authorization Bypass - FIXED
2. **CVE-002:** Command Injection - FIXED
3. **CVE-003:** SSRF - FIXED
4. **CVE-004:** Path Traversal (part_id) - FIXED
5. **CVE-005:** Alt Command Injection - FIXED
6. **CVE-006:** Path Traversal (file imports) - FIXED
7. **CVE-007:** Malicious Capabilities - FIXED
8. **CVE-008:** Parameter Injection - FIXED
9. **CVE-009:** Rate Limiting - FIXED

**Full Details:** See `/home/ril3y/MakerMatrix/tests/SECURITY_REMEDIATION_COMPLETE.md`

---

## When to Run Security Scripts

### Daily Development
✅ Use: `pytest tests/test_security_fixes.py -v -m critical`
❌ Don't use: Full audit scripts (too slow for daily use)

### Before Production Deployment
✅ Use: Both pytest AND audit scripts
✅ Verify: All tests pass, no new vulnerabilities

### Quarterly Security Review
✅ Use: Full audit scripts
✅ Document: Any new findings
✅ Update: Security documentation

### After Major Changes
✅ Use: Full test suite + audit scripts
✅ Focus on: Changed areas of code
✅ Verify: No regressions

---

## Configuration

Both scripts use the same configuration:

**Base URL:** `https://10.2.0.2:8443` (or `http://localhost:8000`)
**Test API Key:** `REDACTED_API_KEY`
**SSL Verification:** Disabled for self-signed certs (development only)

To modify configuration, edit the scripts directly:
```python
BASE_URL = "https://10.2.0.2:8443"
API_KEY = "REDACTED_API_KEY"
VERIFY_SSL = False  # Set True for production
```

---

## Output Files

Scripts generate reports in `/home/ril3y/MakerMatrix/tests/`:

- `security_audit_report.json` - Machine-readable findings
- `SECURITY_AUDIT_TASKS_API_REPORT.md` - Detailed technical report
- `SECURITY_AUDIT_EXECUTIVE_SUMMARY.md` - Management summary

---

## Dependencies

```bash
pip install requests urllib3
```

All dependencies are already in `requirements.txt`.

---

## Troubleshooting

### Connection Refused
```
Error: Connection refused to https://10.2.0.2:8443
```
**Solution:** Ensure backend is running
```bash
python3 dev_manager.py
# Check status at http://localhost:8765/status
```

### SSL Certificate Error
```
Error: SSL certificate verification failed
```
**Solution:** Scripts disable SSL verification by default. If needed:
```python
VERIFY_SSL = False  # Already set in scripts
```

### API Key Invalid
```
Error: 401 Unauthorized - Invalid API key
```
**Solution:** Check that test API key exists in database
```bash
# Query database to verify
sqlite3 makermatrix.db "SELECT * FROM api_keys WHERE key LIKE 'mm_Z8p%'"
```

---

## Best Practices

### DO:
✅ Run security tests before deployment
✅ Document all findings
✅ Fix vulnerabilities immediately
✅ Re-test after fixes
✅ Keep scripts updated

### DON'T:
❌ Run against production without authorization
❌ Ignore security findings
❌ Modify scripts to bypass security
❌ Share vulnerability details publicly before fixes
❌ Use for malicious purposes

---

## Questions?

For security issues or questions:
- **Documentation:** `/home/ril3y/MakerMatrix/tests/SECURITY_TESTING.md`
- **Main README:** `/home/ril3y/MakerMatrix/README.md`
- **Development Guide:** `/home/ril3y/MakerMatrix/CLAUDE.md`

---

**Last Updated:** October 22, 2025
**Maintained By:** MakerMatrix Development Team
