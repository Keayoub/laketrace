"""
Configuration management for LakeTrace logger.

Provides default settings and configuration validation for the logging system.
All settings are designed to be safe for Spark driver usage.
"""

from typing import Any, Dict, Optional
from pathlib import Path

# Import is deferred to avoid circular imports
# from laketrace.security import SecurityConfig


class LakeTraceConfig:
    """Configuration container for LakeTrace logger."""
    
    # Default configuration values
    DEFAULTS: Dict[str, Any] = {
        "log_dir": "/tmp/laketrace_logs",
        "rotation_mb": 10,  # Rotate after 10 MB
        "retention_files": 5,  # Keep last 5 files
        "level": "INFO",
        "json": True,  # Use JSON format
        "stdout": True,  # Emit to stdout
        "compression": "none",  # Options: "zip", "gz", "none"
        "add_runtime_context": True,  # Add platform/runtime metadata
        "enqueue": False,  # Use background queue for sinks
        # Security settings
        "sanitize_messages": True,  # Prevent log injection attacks
        "mask_pii": False,  # Mask sensitive data (PII)
        "secure_file_permissions": True,  # Use 0o600 for log files
    }
    
    VALID_LEVELS = {"TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"}
    VALID_COMPRESSIONS = {"zip", "gz", "none"}
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize configuration with user overrides.
        
        Args:
            config: Optional dictionary of configuration overrides
        """
        self._config = self.DEFAULTS.copy()
        
        if config:
            self._config.update(config)
            self._validate()
    
    def _validate(self) -> None:
        """Validate configuration values."""
        # Validate level
        level = str(self._config["level"]).upper()
        if level not in self.VALID_LEVELS:
            raise ValueError(
                f"Invalid log level '{level}'. Must be one of {self.VALID_LEVELS}"
            )
        self._config["level"] = level
        
        # Validate compression
        compression = str(self._config["compression"]).lower()
        if compression not in self.VALID_COMPRESSIONS:
            raise ValueError(
                f"Invalid compression '{compression}'. Must be one of {self.VALID_COMPRESSIONS}"
            )
        self._config["compression"] = compression
        
        # Validate numeric values
        if self._config["rotation_mb"] <= 0:
            raise ValueError("rotation_mb must be positive")
        
        if self._config["retention_files"] <= 0:
            raise ValueError("retention_files must be positive")
        
        # Ensure log_dir is string
        self._config["log_dir"] = str(self._config["log_dir"])
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._config.get(key, default)
    
    def __getitem__(self, key: str) -> Any:
        """Get configuration value using dict-like access."""
        return self._config[key]
    
    def __contains__(self, key: str) -> bool:
        """Check if configuration key exists."""
        return key in self._config
    
    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary."""
        return self._config.copy()
    
    @property
    def log_dir(self) -> str:
        """Get log directory path."""
        return self._config["log_dir"]
    
    @property
    def rotation_mb(self) -> int:
        """Get rotation size in MB."""
        return self._config["rotation_mb"]
    
    @property
    def retention_files(self) -> int:
        """Get number of files to retain."""
        return self._config["retention_files"]
    
    @property
    def level(self) -> str:
        """Get log level."""
        return self._config["level"]
    
    @property
    def json(self) -> bool:
        """Check if JSON format is enabled."""
        return self._config["json"]
    
    @property
    def stdout(self) -> bool:
        """Check if stdout sink is enabled."""
        return self._config["stdout"]
    
    @property
    def compression(self) -> str:
        """Get compression type."""
        return self._config["compression"]
    
    @property
    def add_runtime_context(self) -> bool:
        """Check if runtime context should be added."""
        return self._config["add_runtime_context"]

    @property
    def enqueue(self) -> bool:
        """Check if sinks should use enqueue."""
        return self._config["enqueue"]

    @property
    def sanitize_messages(self) -> bool:
        """Check if message sanitization is enabled."""
        return self._config["sanitize_messages"]
    
    @property
    def mask_pii(self) -> bool:
        """Check if PII masking is enabled."""
        return self._config["mask_pii"]
    
    @property
    def secure_file_permissions(self) -> bool:
        """Check if secure file permissions (0o600) are enabled."""
        return self._config["secure_file_permissions"]
