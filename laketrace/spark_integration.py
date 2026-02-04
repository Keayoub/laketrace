"""
Spark framework log integration with LakeTrace.

Provides utilities to redirect Spark framework logs to LakeTrace logger,
enabling unified logging for both application and Spark events.

This is particularly useful for Microsoft Fabric and Databricks environments
where you want all logs (app + Spark) in a single lakehouse file.
"""

import logging
from typing import Optional, Any

from laketrace.logger import Logger, get_logger


class SparkLogHandler(logging.Handler):
    """
    Custom logging handler that redirects Python/Spark logs to LakeTrace.

    This handler captures all logs from the Spark framework (org.apache.spark)
    and routes them to the LakeTrace logger, allowing unified logging output.

    Args:
        logger: LakeTraceLogger instance to redirect logs to
    """

    def __init__(self, logger: LakeTraceLogger):
        """Initialize handler with LakeTrace logger."""
        super().__init__()
        self.logger = logger

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record by routing it to LakeTrace.

        Args:
            record: LogRecord from Python logging system
        """
        try:
            # Get log level method (info, warning, error, etc.)
            level = record.levelname.lower()
            
            # Format the message
            message = self.format(record)
            
            # Route to LakeTrace logger
            log_method = getattr(self.logger._logger, level, self.logger._logger.info)
            log_method(message)
        except Exception:
            # Prevent logging errors from breaking the application
            self.handleError(record)


def setup_logging_with_spark(
    app_name: str,
    spark_session: Optional[Any] = None,
    config: Optional[dict] = None,
    capture_spark_logs: bool = True,
    spark_log_level: str = "INFO",
) -> LakeTraceLogger:
    """
    Setup unified logging for application and Spark framework events.

    This function creates a LakeTrace logger and optionally redirects all Spark
    framework logs (org.apache.spark) to the same logger. This enables unified
    logging where both your application events and Spark framework events are
    captured in a single log file.

    Args:
        app_name: Name of your application
        spark_session: PySpark SparkSession instance (optional, used to detect Spark)
        config: Optional configuration dictionary for LakeTrace logger
        capture_spark_logs: Whether to redirect Spark logs (default: True)
        spark_log_level: Minimum level for Spark logs (default: INFO)

    Returns:
        Configured LakeTraceLogger instance

    Example:
        ```python
        from pyspark.sql import SparkSession
        from laketrace import setup_logging_with_spark

        spark = SparkSession.builder.appName("MyApp").getOrCreate()
        logger = setup_logging_with_spark("my_etl", spark)

        logger.info("Starting ETL")
        df = spark.read.parquet("data")  # Spark logs captured here
        logger.info(f"Processed {df.count()} records")
        logger.upload_log_to_lakehouse("Files/logs/etl.log")
        ```

    Note:
        - In Fabric Notebooks: Works with Spark Session automatically
        - In Fabric Spark Jobs: Works with Spark Session automatically
        - In Databricks: Works with Spark Session automatically
        - In Local Development: Captures application logs only (no Spark)
    """
    # Create LakeTrace logger with optional config
    app_logger = get_logger(app_name, config=config)

    # Setup Spark log redirection if requested
    if capture_spark_logs:
        try:
            # Get root Python logger for Spark
            spark_logger = logging.getLogger("org.apache.spark")
            spark_logger.setLevel(getattr(logging, spark_log_level.upper(), logging.INFO))

            # Create and add our custom handler
            handler = SparkLogHandler(app_logger)
            handler.setLevel(getattr(logging, spark_log_level.upper(), logging.INFO))
            
            # Avoid duplicate handlers if called multiple times
            existing_handlers = [
                h for h in spark_logger.handlers 
                if isinstance(h, SparkLogHandler)
            ]
            if not existing_handlers:
                spark_logger.addHandler(handler)

            app_logger.debug(f"Spark logging configured to redirect to {app_name}")

        except Exception as e:
            app_logger.warning(f"Failed to setup Spark log redirection: {e}")

    return app_logger


def stop_spark_and_upload_logs(
    logger: LakeTraceLogger,
    target_path: str,
    spark_session: Optional[Any] = None,
) -> None:
    """
    Stop Spark session and upload logs to lakehouse.

    Convenience function to handle both graceful Spark shutdown and log upload
    in a single call. Useful for end-of-job cleanup.

    Args:
        logger: LakeTraceLogger instance
        target_path: Target path in lakehouse (e.g., "Files/logs/job.log")
        spark_session: PySpark SparkSession to stop (optional)

    Example:
        ```python
        from laketrace import setup_logging_with_spark, stop_spark_and_upload_logs
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.appName("MyApp").getOrCreate()
        logger = setup_logging_with_spark("my_job", spark)

        try:
            # Your Spark job
            logger.info("Working...")
        finally:
            stop_spark_and_upload_logs(logger, "Files/logs/job.log", spark)
        ```
    """
    try:
        # Upload logs first (before stopping Spark)
        logger.info("Uploading logs to lakehouse")
        logger.upload_log_to_lakehouse(target_path)
        logger.success(f"Logs uploaded to {target_path}")
    except Exception as e:
        logger.error(f"Failed to upload logs: {e}")

    # Stop Spark session if provided
    if spark_session:
        try:
            logger.debug("Stopping Spark session")
            spark_session.stop()
            logger.debug("Spark session stopped")
        except Exception as e:
            logger.error(f"Failed to stop Spark session: {e}")
