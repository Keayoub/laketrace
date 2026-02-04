"""
Runtime detection and platform identification for LakeTrace.

Provides utilities to detect the execution environment (Fabric, Databricks, Spark, etc.)
and extract runtime metadata for logging context.
"""

import os
import socket
from enum import Enum
from typing import Dict, Any, Optional


class RuntimePlatform(Enum):
    """Enumeration of supported runtime platforms."""
    FABRIC = "fabric"
    DATABRICKS = "databricks"
    SPARK = "spark"
    LOCAL = "local"
    UNKNOWN = "unknown"


class RuntimeDetector:
    """
    Detects the current runtime environment and provides platform metadata.
    
    This class identifies whether code is running in:
    - Microsoft Fabric (Notebooks or Spark Job Definitions)
    - Databricks (Notebooks or Jobs)
    - Generic Spark environment
    - Local Python environment
    
    Detection is cached after first call for performance.
    """
    
    _cached_platform: Optional[RuntimePlatform] = None
    _cached_metadata: Optional[Dict[str, Any]] = None
    
    @classmethod
    def detect_platform(cls) -> RuntimePlatform:
        """
        Detect the current runtime platform.
        
        Returns:
            RuntimePlatform enum value
        """
        if cls._cached_platform is not None:
            return cls._cached_platform
        
        # Check for Microsoft Fabric
        if cls._is_fabric():
            cls._cached_platform = RuntimePlatform.FABRIC
            return cls._cached_platform
        
        # Check for Databricks
        if cls._is_databricks():
            cls._cached_platform = RuntimePlatform.DATABRICKS
            return cls._cached_platform
        
        # Check for generic Spark
        if cls._is_spark():
            cls._cached_platform = RuntimePlatform.SPARK
            return cls._cached_platform
        
        # Check for local development
        if cls._is_local():
            cls._cached_platform = RuntimePlatform.LOCAL
            return cls._cached_platform
        
        cls._cached_platform = RuntimePlatform.UNKNOWN
        return cls._cached_platform
    
    @classmethod
    def get_runtime_metadata(cls) -> Dict[str, Any]:
        """
        Get comprehensive runtime metadata for logging context.
        
        Returns:
            Dictionary containing platform, hostname, pid, and platform-specific info
        """
        if cls._cached_metadata is not None:
            return cls._cached_metadata.copy()
        
        platform = cls.detect_platform()
        
        metadata = {
            "platform": platform.value,
            "hostname": cls._get_hostname(),
            "pid": os.getpid(),
        }
        
        # Add platform-specific metadata
        if platform == RuntimePlatform.FABRIC:
            metadata.update(cls._get_fabric_metadata())
        elif platform == RuntimePlatform.DATABRICKS:
            metadata.update(cls._get_databricks_metadata())
        elif platform == RuntimePlatform.SPARK:
            metadata.update(cls._get_spark_metadata())
        
        cls._cached_metadata = metadata
        return metadata.copy()
    
    @staticmethod
    def _is_fabric() -> bool:
        """Check if running in Microsoft Fabric environment."""
        # Try importing notebookutils (Fabric-specific module)
        try:
            import notebookutils  # type: ignore
            return True
        except ImportError:
            pass
        
        # Check for Fabric-related environment variables
        fabric_vars = [
            "FABRIC_WORKSPACE_ID",
            "FABRIC_LAKEHOUSE_ID",
            "ONELAKE_WORKSPACE_ID",
            "SYNAPSE_WORKSPACE_NAME",
        ]
        return any(var in os.environ for var in fabric_vars)
    
    @staticmethod
    def _is_databricks() -> bool:
        """Check if running in Databricks environment."""
        # Try importing dbutils (Databricks-specific module)
        try:
            from pyspark.dbutils import DBUtils  # type: ignore
            return True
        except ImportError:
            pass
        
        # Check for Databricks environment variables
        return "DATABRICKS_RUNTIME_VERSION" in os.environ
    
    @staticmethod
    def _is_spark() -> bool:
        """Check if running in a generic Spark environment."""
        try:
            from pyspark.sql import SparkSession
            spark = SparkSession.getActiveSession()
            return spark is not None
        except ImportError:
            return False
    
    @staticmethod
    def _is_local() -> bool:
        """Check if running in local development environment."""
        # Consider local if not in any cloud platform
        return True
    
    @staticmethod
    def _get_hostname() -> str:
        """Get current hostname."""
        try:
            return socket.gethostname()
        except Exception:
            return "unknown"
    
    @staticmethod
    def _get_fabric_metadata() -> Dict[str, Any]:
        """Extract Fabric-specific metadata."""
        metadata = {}
        
        # Get workspace and lakehouse IDs if available
        if "FABRIC_WORKSPACE_ID" in os.environ:
            metadata["workspace_id"] = os.environ["FABRIC_WORKSPACE_ID"]
        
        if "FABRIC_LAKEHOUSE_ID" in os.environ:
            metadata["lakehouse_id"] = os.environ["FABRIC_LAKEHOUSE_ID"]
        
        if "SYNAPSE_WORKSPACE_NAME" in os.environ:
            metadata["workspace_name"] = os.environ["SYNAPSE_WORKSPACE_NAME"]
        
        return metadata
    
    @staticmethod
    def _get_databricks_metadata() -> Dict[str, Any]:
        """Extract Databricks-specific metadata."""
        metadata = {}
        
        # Get runtime version
        if "DATABRICKS_RUNTIME_VERSION" in os.environ:
            metadata["runtime_version"] = os.environ["DATABRICKS_RUNTIME_VERSION"]
        
        # Get cluster/job information
        if "DB_CLUSTER_ID" in os.environ:
            metadata["cluster_id"] = os.environ["DB_CLUSTER_ID"]
        
        if "DB_JOB_ID" in os.environ:
            metadata["job_id"] = os.environ["DB_JOB_ID"]
        
        if "DB_JOB_RUN_ID" in os.environ:
            metadata["job_run_id"] = os.environ["DB_JOB_RUN_ID"]
        
        return metadata
    
    @staticmethod
    def _get_spark_metadata() -> Dict[str, Any]:
        """Extract Spark-specific metadata."""
        metadata = {}
        
        try:
            from pyspark.sql import SparkSession
            spark = SparkSession.getActiveSession()
            if spark:
                metadata["spark_app_id"] = spark.sparkContext.applicationId
                metadata["spark_app_name"] = spark.sparkContext.appName
        except Exception:
            pass
        
        return metadata
    
    @classmethod
    def reset_cache(cls) -> None:
        """Reset cached platform detection. Useful for testing."""
        cls._cached_platform = None
        cls._cached_metadata = None


def stop_spark_if_active() -> None:
    """
    Safely stop active SparkSession if present.
    
    This is a utility function for cleanup at end of Spark jobs.
    It will not raise an exception if Spark is not available or already stopped.
    """
    try:
        from pyspark.sql import SparkSession
        spark = SparkSession.getActiveSession()
        if spark:
            spark.stop()
    except Exception:
        # Silently ignore if Spark is not available or already stopped
        pass


def get_run_id_from_environment() -> Optional[str]:
    """
    Extract run ID from environment variables if available.
    
    Returns:
        Run ID string or None if not found
    """
    # Check Databricks
    if "DB_JOB_RUN_ID" in os.environ:
        return os.environ["DB_JOB_RUN_ID"]
    
    # Check Fabric (may have different variable names)
    if "FABRIC_RUN_ID" in os.environ:
        return os.environ["FABRIC_RUN_ID"]
    
    # Check for generic run ID
    if "RUN_ID" in os.environ:
        return os.environ["RUN_ID"]
    
    return None
