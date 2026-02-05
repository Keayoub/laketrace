"""
Security utilities for LakeTrace logger.

Provides input sanitization, PII masking, secure file handling, and advanced
data leak prevention for production Spark environments.
"""

import hashlib
import os
import re
from typing import Any, Dict, List, Optional, Pattern, Set, Tuple
from datetime import datetime, timedelta
from collections import defaultdict


class SecurityConfig:
    """Configuration for security features."""

    def __init__(
        self,
        enable_sanitization: bool = True,
        enable_pii_masking: bool = False,
        pii_patterns: Optional[Dict[str, str]] = None,
        safe_mode: bool = False,
    ):
        """
        Initialize security configuration.

        Args:
            enable_sanitization: Enable log injection prevention (default: True)
            enable_pii_masking: Enable PII field masking (default: False)
            pii_patterns: Dict of {field_name: regex_pattern} for custom PII detection
            safe_mode: Raise exceptions on security issues instead of logging warnings (default: False)
        """
        self.enable_sanitization = enable_sanitization
        self.enable_pii_masking = enable_pii_masking
        self.pii_patterns = pii_patterns or self._default_pii_patterns()
        self.safe_mode = safe_mode
        self._compiled_patterns = {
            name: re.compile(pattern)
            for name, pattern in self.pii_patterns.items()
        }

    def _default_pii_patterns(self) -> Dict[str, str]:
        """Default PII patterns to mask."""
        return {
            # Authentication
            "password": r"(?i)(password|passwd|pwd|secret|pass)\s*[:=]\s*['\"]?[^\s'\"]*['\"]?",
            "api_key": r"(?i)(api[_-]?key|apikey|api[_-]?secret|secret[_-]?key)\s*[:=]\s*['\"]?[^\s'\"]*['\"]?",
            "token": r"(?i)(token|auth|authorization|bearer|jwt|access[_-]?token)\s*[:=]\s*[^\s]+",
            
            # Connection strings and credentials
            "connection_string": r"(?i)(connection[_-]?string|server\s*=|database\s*=|password\s*=)",
            "azure_key": r"(?i)(accountkey|storageaccountkey|SharedAccessKey)\s*[:=]\s*[^\s]+",
            
            # Personal data
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "phone": r"\b(?:\+1|1)?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b",
            "credit_card": r"\b(?:\d{4}[\s-]?){3}\d{4}\b",
            "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
            
            # Cloud/Infrastructure
            "aws_key": r"(?i)AKIA[0-9A-Z]{16}",
            "azure_subscription": r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",
            "private_key": r"-----BEGIN\s(?:RSA|PRIVATE|EC|OPENSSH)\s(?:PRIVATE\s)?KEY-----",
            
            # IP addresses (internal networks - often sensitive)
            "internal_ip": r"\b(?:10\.|172\.(?:1[6-9]|2\d|3[01])\.|192\.168\.)\d{1,3}\.\d{1,3}\b",
        }


def get_secure_file_opener():
    """
    Get a file opener function that sets secure permissions (0o600).

    Returns a callable that can be passed to logger.add() as the opener parameter.
    This ensures log files are readable/writable by owner only.

    Returns:
        Callable that opens files with 0o600 permissions

    Example:
        ```python
        from laketrace.security import get_secure_file_opener
        logger.add("secure.log", opener=get_secure_file_opener())
        ```
    """

    def secure_opener(file: str, flags: int) -> int:
        """Open file with owner-only permissions (0o600)."""
        return os.open(file, flags, 0o600)

    return secure_opener


def sanitize_message(message: str) -> str:
    """
    Sanitize log message to prevent log injection attacks.

    Replaces newlines and carriage returns with escaped sequences to prevent
    attackers from forging fake log entries.

    Args:
        message: Raw log message

    Returns:
        Sanitized message with newlines escaped

    Example:
        ```python
        user_input = "Login\\nINFO Admin logged in"
        safe = sanitize_message(user_input)
        logger.info(safe)  # Newline is escaped, prevents injection
        ```
    """
    if not isinstance(message, str):
        return str(message)

    # Escape newlines and carriage returns
    sanitized = message.replace("\n", "\\n").replace("\r", "\\r").replace("\x00", "\\x00")

    return sanitized


def mask_pii(
    data: Dict[str, Any],
    security_config: Optional[SecurityConfig] = None,
    fields_to_mask: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Mask sensitive PII fields in structured log data.

    Args:
        data: Dictionary containing potential PII
        security_config: SecurityConfig with PII patterns
        fields_to_mask: Specific field names to mask (overrides pattern matching)

    Returns:
        Dictionary with masked sensitive values

    Example:
        ```python
        from laketrace.security import mask_pii, SecurityConfig

        config = SecurityConfig(enable_pii_masking=True)
        data = {"user": "john@example.com", "password": "secret123"}
        safe = mask_pii(data, config)
        # Result: {"user": "***", "password": "***"}
        ```
    """
    if security_config is None:
        security_config = SecurityConfig()

    masked = {}

    for key, value in data.items():
        # Check if field name matches PII field list
        if fields_to_mask and key in fields_to_mask:
            masked[key] = mask_value(value)
            continue

        # Check if value matches any PII pattern
        if isinstance(value, str) and security_config._compiled_patterns:
            should_mask = False
            for pattern in security_config._compiled_patterns.values():
                if pattern.search(value):
                    should_mask = True
                    break

            if should_mask:
                masked[key] = mask_value(value)
                continue

        masked[key] = value

    return masked


def mask_value(value: Any) -> str:
    """
    Replace a value with masked placeholder.

    Args:
        value: Value to mask

    Returns:
        Masked placeholder string
    """
    if isinstance(value, str) and len(value) > 3:
        # Show first 3 chars, mask the rest
        return f"{value[:3]}{'*' * (len(value) - 3)}"
    else:
        return "***"


def escape_newlines(text: str) -> str:
    """
    Escape newlines in text for safe logging.

    Alias for sanitize_message() - alternative name for clarity.

    Args:
        text: Text to escape

    Returns:
        Text with newlines escaped
    """
    return sanitize_message(text)


def escape_format_strings(text: str) -> str:
    """
    Escape curly braces to prevent string format attacks.

    Prevents attackers from using logger.info(user_input, obj=value)
    to access object internals via format string exploits.

    Args:
        text: Text that will be used as format string

    Returns:
        Text with braces escaped
    """
    if not isinstance(text, str):
        return str(text)

    return text.replace("{", "{{").replace("}", "}}")


class DataLeakDetector:
    """
    Detects suspicious logging patterns that may indicate data exfiltration.
    
    Monitors:
    - Unusually large log records (potential bulk data dump)
    - Rapid repeated logging (flooding attack)
    - Sensitive field combinations (e.g., password + connection string together)
    - Cross-partition logging (potential data movement tracking)
    """

    def __init__(
        self,
        max_log_size_kb: int = 100,
        max_logs_per_second: int = 100,
        window_seconds: int = 5,
        detect_field_combinations: bool = True,
    ):
        """
        Initialize data leak detector.

        Args:
            max_log_size_kb: Warn if single log record exceeds this size
            max_logs_per_second: Max logs allowed per time window
            window_seconds: Time window for rate limiting check
            detect_field_combinations: Detect suspicious field combinations
        """
        self.max_log_size_bytes = max_log_size_kb * 1024
        self.max_logs_per_second = max_logs_per_second
        self.window_seconds = window_seconds
        self.detect_field_combinations = detect_field_combinations
        
        # Ring buffer for rate limiting: stores (timestamp, count) tuples
        self.log_timestamps: List[float] = []
        
        # Suspicious field combinations that often indicate data theft (use frozenset for hashability)
        self.sensitive_combinations = {
            frozenset({"password", "connection_string"}),
            frozenset({"api_key", "password"}),
            frozenset({"token", "user_id", "email"}),
            frozenset({"credit_card", "ssn"}),
            frozenset({"private_key", "certificate"}),
        }

    def check_log_record(
        self, message: str, data: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Check a log record for potential data leak patterns.

        Args:
            message: Log message text
            data: Structured log data (dict)

        Returns:
            Tuple of (is_safe, warnings) where warnings is list of detected issues
        """
        warnings = []
        
        # Check 1: Large log record
        total_size = len(message.encode("utf-8"))
        if data:
            import json
            total_size += len(json.dumps(data).encode("utf-8"))
        
        if total_size > self.max_log_size_bytes:
            warnings.append(
                f"LARGE_LOG: {total_size / 1024:.1f} KB exceeds {self.max_log_size_bytes / 1024:.0f} KB limit"
            )
        
        # Check 2: Rapid logging (potential flooding)
        import time
        now = time.time()
        self.log_timestamps = [ts for ts in self.log_timestamps if now - ts < self.window_seconds]
        self.log_timestamps.append(now)
        
        logs_in_window = len(self.log_timestamps)
        max_allowed = self.max_logs_per_second * self.window_seconds
        if logs_in_window > max_allowed:
            warnings.append(
                f"RATE_LIMIT: {logs_in_window} logs in {self.window_seconds}s exceeds {max_allowed}"
            )
        
        # Check 3: Suspicious field combinations
        if self.detect_field_combinations and data:
            field_names = set(data.keys())
            for combo in self.sensitive_combinations:
                if combo.issubset(field_names):
                    warnings.append(
                        f"SENSITIVE_COMBO: Fields {combo} logged together (potential data leak)"
                    )
        
        return len(warnings) == 0, warnings


class FieldWhitelist:
    """
    Enforce strict field whitelisting to prevent accidental data leaks.
    
    Only allows explicitly approved fields in structured logs.
    Useful for enforcing compliance (PCI-DSS, HIPAA, etc).
    """

    def __init__(self, allowed_fields: Optional[Set[str]] = None, strict: bool = False):
        """
        Initialize field whitelist.

        Args:
            allowed_fields: Set of allowed field names (None = all allowed, unless strict=True)
            strict: If True, only allowed_fields permitted; if False, allowed_fields is just recommended
        """
        self.allowed_fields = allowed_fields or set()
        self.strict = strict
        self.violation_count = 0

    def add_allowed_fields(self, *fields: str) -> None:
        """Add more fields to whitelist."""
        self.allowed_fields.update(fields)

    def validate_record(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """
        Filter record to only include whitelisted fields.

        Args:
            data: Log record data

        Returns:
            Tuple of (filtered_data, warnings)
        """
        warnings = []
        filtered = {}
        
        for key, value in data.items():
            if key in self.allowed_fields:
                filtered[key] = value
            elif not self.strict:
                filtered[key] = value
                warnings.append(f"UNAPPROVED_FIELD: {key} not in whitelist")
            else:
                self.violation_count += 1
                warnings.append(f"BLOCKED_FIELD: {key} not in whitelist (strict mode)")
        
        return filtered, warnings

    def get_violation_count(self) -> int:
        """Get total validation violations."""
        return self.violation_count


class LogIntegrityVerifier:
    """
    Verify log integrity using checksums and detect tampering.
    
    Useful for audit trails and compliance.
    """

    def __init__(self, hash_algorithm: str = "sha256"):
        """
        Initialize integrity verifier.

        Args:
            hash_algorithm: Hash algorithm to use (sha256, sha512, etc)
        """
        self.hash_algorithm = hash_algorithm
        self.log_hashes: Dict[str, str] = {}

    def compute_hash(self, record: Dict[str, Any]) -> str:
        """
        Compute hash of a log record for integrity verification.

        Args:
            record: Log record as dictionary

        Returns:
            Hex digest of hash
        """
        import json
        record_str = json.dumps(record, sort_keys=True, default=str)
        h = hashlib.new(self.hash_algorithm)
        h.update(record_str.encode("utf-8"))
        return h.hexdigest()

    def verify_record(self, record: Dict[str, Any], expected_hash: str) -> bool:
        """
        Verify a record matches expected hash.

        Args:
            record: Log record
            expected_hash: Expected hash value

        Returns:
            True if hash matches
        """
        actual_hash = self.compute_hash(record)
        return actual_hash == expected_hash

    def add_hash_header(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add integrity hash to a record.

        Args:
            record: Log record

        Returns:
            Record with added _integrity_hash field
        """
        record_copy = record.copy()
        record_hash = self.compute_hash(record_copy)
        record_copy["_integrity_hash"] = record_hash
        return record_copy


class SensitiveDataRedactor:
    """
    Aggressively redact sensitive data patterns from logs.
    
    Handles:
    - Database credentials
    - Connection strings
    - API responses with sensitive data
    - Stack traces with internal paths
    """

    def __init__(self):
        """Initialize with default redaction patterns."""
        self.redaction_patterns = {
            r"password\s*[=:]\s*['\"]?([^'\";\s]+)['\"]?": "[REDACTED_PASSWORD]",
            r"(accountkey|storageaccountkey|sharedaccesskey)\s*[=:]\s*([^\s;]+)": "[REDACTED_KEY]",
            r"(server\s*=\s*)([\w.-]+)": r"\1[REDACTED_HOST]",
            r"(Data Source\s*=\s*)([\w.-]+)": r"\1[REDACTED_HOST]",
            r"(Catalog\s*=\s*)([\w.-]+)": r"\1[REDACTED_DB]",
            r"Authorization:\s*Bearer\s+\S+": "Authorization: Bearer [REDACTED_TOKEN]",
            r"X-API-Key:\s*\S+": "X-API-Key: [REDACTED_KEY]",
        }

    def redact(self, text: str) -> str:
        """
        Redact sensitive patterns from text.

        Args:
            text: Text that may contain sensitive data

        Returns:
            Redacted text
        """
        if not isinstance(text, str):
            return str(text)
        
        redacted = text
        for pattern, replacement in self.redaction_patterns.items():
            redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)
        
        return redacted

    def redact_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact sensitive values in structured data.

        Args:
            data: Log record dictionary

        Returns:
            Dictionary with sensitive values redacted
        """
        redacted = {}
        for key, value in data.items():
            if isinstance(value, str):
                redacted[key] = self.redact(value)
            elif isinstance(value, dict):
                redacted[key] = self.redact_record(value)
            else:
                redacted[key] = value
        return redacted


class DataEncryption:
    """
    Encrypt sensitive log data at rest (local files only, not in-flight).
    
    Uses Fernet symmetric encryption (requires cryptography package).
    WARNING: For production, use Azure Key Vault or HashiCorp Vault for key management.
    """

    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption handler.

        Args:
            encryption_key: Base64-encoded Fernet key. If None, encryption is disabled.
        
        Example:
            ```python
            from cryptography.fernet import Fernet
            key = Fernet.generate_key()  # Save this securely!
            encryptor = DataEncryption(key.decode())
            ```
        """
        self.encryption_key = encryption_key
        self.fernet = None
        
        if encryption_key:
            try:
                from cryptography.fernet import Fernet
                self.fernet = Fernet(encryption_key.encode())
            except ImportError:
                raise ImportError(
                    "cryptography package required for DataEncryption. "
                    "Install with: pip install cryptography"
                )
            except Exception as e:
                raise ValueError(f"Invalid encryption key: {e}")

    def encrypt_field(self, value: str) -> str:
        """
        Encrypt a single field value.

        Args:
            value: Field value to encrypt

        Returns:
            Base64-encoded encrypted value
        """
        if not self.fernet:
            return value
        
        encrypted = self.fernet.encrypt(value.encode())
        return encrypted.decode()

    def decrypt_field(self, encrypted_value: str) -> str:
        """
        Decrypt a field value.

        Args:
            encrypted_value: Base64-encoded encrypted value

        Returns:
            Decrypted value
        """
        if not self.fernet:
            return encrypted_value
        
        try:
            decrypted = self.fernet.decrypt(encrypted_value.encode())
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt: {e}")

    def encrypt_record(self, data: Dict[str, Any], fields_to_encrypt: Set[str]) -> Dict[str, Any]:
        """
        Encrypt specific fields in a record.

        Args:
            data: Log record
            fields_to_encrypt: Set of field names to encrypt

        Returns:
            Record with selected fields encrypted
        """
        if not self.fernet:
            return data
        
        encrypted = {}
        for key, value in data.items():
            if key in fields_to_encrypt and isinstance(value, str):
                encrypted[key] = self.encrypt_field(value)
            else:
                encrypted[key] = value
        return encrypted

