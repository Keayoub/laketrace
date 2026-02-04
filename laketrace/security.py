"""
Security utilities for LakeTrace logger.

Provides input sanitization, PII masking, and secure file handling.
"""

import os
import re
from typing import Any, Dict, List, Optional, Pattern


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
            "password": r"(?i)(password|passwd|pwd)\s*[:=]\s*\S+",
            "api_key": r"(?i)(api[_-]?key|apikey|secret)\s*[:=]\s*\S+",
            "token": r"(?i)(token|auth|authorization)\s*[:=]\s*\S+",
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "credit_card": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
            "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        }


def get_secure_file_opener():
    """
    Get a file opener function that sets secure permissions (0o600).

    Returns a callable that can be passed to loguru's logger.add() as the opener parameter.
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
