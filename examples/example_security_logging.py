"""
Example: Comprehensive security logging in Fabric/Databricks environments.

Demonstrates how to implement multi-layer security to prevent data leaks.
"""

from laketrace import get_logger
from laketrace.security import (
    SecurityConfig,
    DataLeakDetector,
    FieldWhitelist,
    SensitiveDataRedactor,
    mask_pii,
)


class SecureApplicationLogger:
    """
    Production-grade logging wrapper with comprehensive security.
    
    Features:
    - Field whitelisting (strict mode)
    - Automatic PII masking
    - Credential redaction
    - Data leak detection
    - Rate limiting
    """

    def __init__(self, app_name: str, environment: str = "production"):
        """
        Initialize secure logger.

        Args:
            app_name: Application/service name
            environment: "production", "staging", "development"
        """
        self.environment = environment
        
        # 1. Security configuration
        self.security_config = SecurityConfig(
            enable_sanitization=True,
            enable_pii_masking=(environment == "production"),
            safe_mode=False,  # Log warnings instead of raising
        )
        
        # 2. Initialize core logger
        self.logger = get_logger(app_name, config=self.security_config.__dict__)
        
        # 3. Field whitelist (what's allowed to log)
        self.whitelist = FieldWhitelist(
            allowed_fields={
                "timestamp",
                "level",
                "message",
                "logger_name",
                "request_id",
                "user_id",  # Public ID only, not email!
                "action",
                "status",
                "duration_ms",
                "error_code",
                "error_message",
                "retry_count",
                "region",
                "environment",
            },
            strict=True,  # Reject unknown fields
        )
        
        # 4. Data leak detector
        self.leak_detector = DataLeakDetector(
            max_log_size_kb=50,  # Warn if log > 50 KB
            max_logs_per_second=500,
            window_seconds=5,
            detect_field_combinations=True,
        )
        
        # 5. Redactor (credentials, connection strings, etc.)
        self.redactor = SensitiveDataRedactor()

    def log_action(
        self,
        action: str,
        user_id: str,
        details: dict = None,
        level: str = "info",
    ) -> bool:
        """
        Log an action with comprehensive security checks.

        Args:
            action: Action name (e.g., "user_login", "data_export")
            user_id: Public user identifier (not email!)
            details: Additional structured data
            level: Log level (info, warning, error, debug)

        Returns:
            True if logged successfully, False if rejected
        """
        details = details or {}
        
        # Prepare log record
        log_record = {
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
            "action": action,
            "user_id": user_id,
            "environment": self.environment,
            **details,
        }
        
        # CHECK 1: Detect potential data leaks
        is_safe, warnings = self.leak_detector.check_log_record(action, details)
        if warnings:
            self.logger.warning(
                f"Security check failed for {action}",
                violations=warnings,
                level=level,
            )
            return False
        
        # CHECK 2: Enforce field whitelist
        safe_record, wh_warnings = self.whitelist.validate_record(log_record)
        if wh_warnings and self.environment == "production":
            self.logger.debug(f"Unapproved fields filtered for {action}", filters=wh_warnings)
        
        # CHECK 3: Redact sensitive patterns
        # (passwords, connection strings, tokens, etc.)
        redacted_record = self.redactor.redact_record(safe_record)
        
        # CHECK 4: Apply PII masking if enabled
        if self.security_config.enable_pii_masking:
            redacted_record = mask_pii(redacted_record, self.security_config)
        
        # LOG: Finally, log the safe record
        log_method = getattr(self.logger, level.lower())
        log_method(action, **redacted_record)
        
        return True

    def log_error(
        self,
        error_code: str,
        error_message: str,
        user_id: str = None,
        details: dict = None,
        exception: Exception = None,
    ):
        """
        Log errors safely without exposing internal paths or credentials.

        Args:
            error_code: Application error code (e.g., "AUTH_001")
            error_message: User-facing error message
            user_id: User identifier if applicable
            details: Additional context
            exception: Exception object (will extract safe info)
        """
        details = details or {}
        
        # Extract safe exception info (no traceback)
        if exception:
            details["exception_type"] = type(exception).__name__
            # Redact exception message to remove internal paths
            safe_message = self.redactor.redact(str(exception))
            details["exception_message"] = safe_message
        
        record = {
            "error_code": error_code,
            "error_message": error_message,
            **({"user_id": user_id} if user_id else {}),
            **details,
        }
        
        # Check and log
        is_safe, warnings = self.leak_detector.check_log_record(error_code, record)
        if warnings:
            self.logger.debug("Error logging security check", warnings=warnings)
        
        safe_record, _ = self.whitelist.validate_record(record)
        redacted_record = self.redactor.redact_record(safe_record)
        
        self.logger.error(error_code, **redacted_record)

    def log_data_access(
        self,
        user_id: str,
        dataset_name: str,
        record_count: int,
        columns_accessed: list = None,
    ):
        """
        Securely log data access events (for audit/compliance).

        Args:
            user_id: User identifier
            dataset_name: Dataset accessed
            record_count: Number of records accessed
            columns_accessed: List of column names (not values!)
        """
        columns_accessed = columns_accessed or []
        
        # IMPORTANT: Never log actual data values, only metadata
        record = {
            "action": "data_access",
            "user_id": user_id,
            "dataset": dataset_name,
            "records_accessed": record_count,
            "columns_count": len(columns_accessed),
        }
        
        # Whitelist enforces we can't add sensitive fields
        safe_record, _ = self.whitelist.validate_record(record)
        self.logger.info("Data access audit", **safe_record)

    def log_with_context(self, context_dict: dict, message: str, level: str = "info"):
        """
        Log with request context (bound logging).

        Args:
            context_dict: Request/session context
            message: Log message
            level: Log level
        """
        # Bind context to logger for all subsequent logs
        bound_logger = self.logger.bind(**context_dict)
        
        # Whitelist the bound fields
        safe_context, _ = self.whitelist.validate_record(context_dict)
        bound_logger = self.logger.bind(**safe_context)
        
        log_method = getattr(bound_logger, level.lower())
        log_method(message)


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

if __name__ == "__main__":
    # Initialize secure logger for production
    sec_logger = SecureApplicationLogger("MyApp", environment="production")

    # Example 1: Safe logging - only allowed fields
    sec_logger.log_action(
        action="user_login",
        user_id="usr_12345",
        details={
            "status": "success",
            "duration_ms": 125,
            "region": "us-east-1",
        },
    )

    # Example 2: Dangerous logging - will be filtered/blocked
    print("\n--- Example 2: Attempting to log sensitive data ---")
    success = sec_logger.log_action(
        action="auth_token_refresh",
        user_id="usr_12345",
        details={
            "token": "eyJhbGciOiJIUzI1NiIs...",  # Will be redacted
            "password": "MyPassword123",  # Will be blocked/redacted
            "status": "success",
        },
    )

    # Example 3: Large data detection
    print("\n--- Example 3: Attempting to log large dataset ---")
    large_dump = "x" * (100 * 1024)  # 100 KB
    success = sec_logger.log_action(
        action="data_export",
        user_id="usr_12345",
        details={
            "status": "success",
            "data": large_dump,  # Will be detected and blocked
        },
    )

    # Example 4: Error logging
    print("\n--- Example 4: Safe error logging ---")
    try:
        1 / 0
    except Exception as e:
        sec_logger.log_error(
            error_code="MATH_001",
            error_message="Division operation failed",
            user_id="usr_12345",
            exception=e,
        )

    # Example 5: Data access audit
    print("\n--- Example 5: Data access audit logging ---")
    sec_logger.log_data_access(
        user_id="usr_12345",
        dataset_name="customer_data",
        record_count=50000,
        columns_accessed=["id", "name", "region"],  # Metadata only, no values
    )

    # Example 6: Bound logging with context
    print("\n--- Example 6: Bound logging with request context ---")
    request_context = {
        "request_id": "req_abc123",
        "user_id": "usr_12345",
        "action": "report_generation",
    }
    sec_logger.log_with_context(
        request_context,
        "Generating monthly report",
        level="info",
    )

    print("\n✓ All security checks passed!")
