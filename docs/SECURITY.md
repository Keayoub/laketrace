# Security Guide for LakeTrace

## Overview

This guide covers security best practices for preventing data leaks and exfiltration when logging in Spark data platforms (Fabric, Databricks).

---

## Field Whitelisting

Enforce strict control over what fields can be logged:

```python
from laketrace import get_logger
from laketrace.security import FieldWhitelist

# Define approved fields only
whitelist = FieldWhitelist(
    allowed_fields={
        "timestamp",
        "level", 
        "message",
        "logger_name",
        "request_id",
        "user_id",  # Public identifier only, not email
        "action",
        "status",
    },
    strict=True  # Block any fields not in whitelist
)

logger = get_logger(__name__)

# Block sensitive fields from being logged
data = {
    "user_id": "usr_12345",
    "action": "login",
    "password": "secret123",  # This will be blocked!
    "status": "success",
}

filtered_data, warnings = whitelist.validate_record(data)
logger.info("User action", **filtered_data)
```

---

## PII Masking

Automatically detect and mask personally identifiable information:

```python
from laketrace import get_logger
from laketrace.security import mask_pii, SecurityConfig

config = SecurityConfig(enable_pii_masking=True)

data = {
    "email": "john@example.com",
    "ssn": "123-45-6789",
    "credit_card": "4111-1111-1111-1111",
    "action": "payment",
}

masked = mask_pii(data, config)
# Sensitive data is automatically masked
logger = get_logger(__name__)
logger.info("Transaction", **masked)
```

Detects: Emails, SSN, credit cards, API keys, AWS keys, Azure keys, IP addresses, connection strings, passwords, and more.

---

## Sensitive Data Redaction

Remove credentials and secrets from logs:

```python
from laketrace.security import SensitiveDataRedactor

redactor = SensitiveDataRedactor()

text = "Connecting with password=MySecret123 to database"
redacted = redactor.redact(text)
# Output: "Connecting with [REDACTED_PASSWORD] to database"
```

Redacts: Passwords, API keys, tokens, connection strings, AWS keys, Azure keys, and JWT tokens.

---

## Log Integrity Verification

Add SHA256 checksums to logs for tamper detection:

```python
from laketrace.security import LogIntegrityVerifier

verifier = LogIntegrityVerifier()

record = {"action": "login", "user_id": "123"}
signed = verifier.add_hash_header(record)
# signed now includes _integrity_hash field

is_valid = verifier.verify_record(record, signed["_integrity_hash"])
assert is_valid  # Detects if record was modified
```

---

## Data Leak Detection

Monitor for suspicious patterns and prevent data exfiltration:

```python
from laketrace.security import DataLeakDetector

detector = DataLeakDetector(
    max_log_size_kb=50,      # Max single log size
    max_rate_per_minute=1000, # Max logs per minute
)

is_safe, warnings = detector.check_log_record("logger_name", data)

if not is_safe:
    print(f"Potential leak detected: {warnings}")
```

Detects:
- Oversized logs (potential bulk data dumps)
- High-rate logging (potential data flooding)
- Suspicious field combinations (potential exfiltration patterns)

---

## Secure File Permissions

Control log file access:

```python
from laketrace.security import get_secure_file_opener

opener = get_secure_file_opener()  # Returns 0o600 (owner-only)
# Use with your file operations for 0o600 permissions
```

---

## Complete Example: Secure Application Logger

```python
from laketrace import get_logger
from laketrace.security import (
    FieldWhitelist,
    SensitiveDataRedactor,
    DataLeakDetector,
    mask_pii,
    SecurityConfig,
)

class SecureApplicationLogger:
    def __init__(self):
        self.logger = get_logger("secure_app")
        
        self.whitelist = FieldWhitelist(
            allowed_fields={"user_id", "action", "status", "timestamp"},
            strict=True,
        )
        self.redactor = SensitiveDataRedactor()
        self.detector = DataLeakDetector(max_log_size_kb=50)
        self.pii_config = SecurityConfig(enable_pii_masking=True)
    
    def log_action(self, data):
        """Log with all security checks."""
        # Check for leaks
        is_safe, _ = self.detector.check_log_record("app", data)
        if not is_safe:
            return
        
        # Whitelist fields
        safe_data, _ = self.whitelist.validate_record(data)
        
        # Redact sensitive data in message
        if "message" in safe_data:
            safe_data["message"] = self.redactor.redact(safe_data["message"])
        
        # Mask PII
        safe_data = mask_pii(safe_data, self.pii_config)
        
        # Log safely
        self.logger.info("action", **safe_data)

# Usage
app_logger = SecureApplicationLogger()
app_logger.log_action({
    "user_id": "usr_123",
    "action": "login",
    "message": "User login with email user@example.com",  # PII masked
    "status": "success",
})
```

---

## Compliance Checklist

### PCI-DSS
- ✅ Field whitelisting (restrict sensitive card data)
- ✅ PII masking (mask card numbers, expiration dates)
- ✅ Log integrity (SHA256 checksums)
- ✅ File permissions (0o600 owner-only access)

### HIPAA
- ✅ PII masking (mask patient IDs, medical record numbers)
- ✅ Field whitelisting (block health information)
- ✅ Secure file permissions
- ✅ Audit trail via log integrity

### SOC2
- ✅ Data leak detection (prevent unauthorized access)
- ✅ Log integrity verification (tamper detection)
- ✅ Field whitelisting (access control)
- ✅ Audit logging of all security actions

### GDPR
- ✅ PII masking (right to be forgotten)
- ✅ Data minimization (field whitelisting)
- ✅ Audit trail (log integrity)
- ✅ Secure storage (file permissions)

---

## Best Practices

1. **Always use field whitelisting** in production
2. **Enable PII masking** for applications handling personal data
3. **Monitor detector warnings** for potential data leaks
4. **Verify log integrity** in compliance audits
5. **Set appropriate max_log_size_kb** for your workloads
6. **Test security rules** before deploying

---

## Related Documentation

- [README.md](../README.md) - Main project documentation
- [tests/UNIFIED_TEST_RUNNER.md](../tests/UNIFIED_TEST_RUNNER.md) - Testing guide
- [laketrace/security.py](../laketrace/security.py) - Security module source code
