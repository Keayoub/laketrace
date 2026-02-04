# LakeTrace Logger

**Production-grade logging for Spark data platforms (Microsoft Fabric & Databricks)**

LakeTrace is a cross-platform Python logging module designed specifically for Spark data platforms. It provides safe, performant logging with structured output, local file rotation, and optional lakehouse storage integration.

## ✨ Key Features

- **Cross-Platform Compatibility**: Works identically in Microsoft Fabric Notebooks, Fabric Spark Job Definitions, and Databricks notebooks/jobs
- **Safe Spark Integration**: Driver-only pattern with no remote file appends during logging
- **Structured JSON Logging**: Rich context with runtime metadata, bound fields, and timestamps
- **Local File Rotation**: Automatic log rotation by size with configurable retention
- **Stdout Emission**: Logs appear in job output for easy debugging
- **Optional Lakehouse Upload**: End-of-run upload to Fabric/Databricks lakehouse storage
- **Thread-Safe**: Safe for concurrent operations
- **Notebook Re-execution Safe**: No duplicate handlers on cell re-runs

## 🚀 Quick Start

### Installation

```bash
pip install laketrace
```

### Basic Usage

```python
from laketrace import get_laketrace_logger

# Create logger
logger = get_laketrace_logger("my_job")

# Log messages
logger.info("Starting data processing")
logger.warning("High memory usage detected")
logger.error("Failed to connect to database")

# Bind context for structured logging
stage_logger = logger.bind(stage="extract", dataset="sales")
stage_logger.info("Extracting sales data")  # Includes stage and dataset fields

# Upload logs at end of job (optional)
logger.upload_log_to_lakehouse("Files/logs/my_job.log")
```

## 📋 Usage Examples

### Example 1: Microsoft Fabric Notebook

```python
from laketrace import get_laketrace_logger

# Initialize logger
logger = get_laketrace_logger("fabric_notebook")

# Log with context
logger.info("Notebook started", user="data_engineer")

# Bind stage context
extract_logger = logger.bind(stage="extract", source="sales_db")
extract_logger.info("Starting data extraction")

# Process data...
try:
    # Your code here
    extract_logger.success("Extraction completed successfully")
except Exception as e:
    extract_logger.exception("Extraction failed")

# View recent logs (useful in notebook)
logger.tail(20)

# Upload to lakehouse at end
logger.upload_log_to_lakehouse("Files/logs/notebook_run.log")
```

### Example 2: Fabric Spark Job Definition

```python
from laketrace import get_laketrace_logger, stop_spark_if_active
from pyspark.sql import SparkSession

def main():
    # Initialize logger with custom config
    logger = get_laketrace_logger(
        "fabric_spark_job",
        config={
            "log_dir": "/tmp/fabric_logs",
            "rotation_mb": 20,
            "retention_files": 10,
            "level": "DEBUG",
        }
    )
    
    logger.info("Spark job started")
    
    try:
        # Create Spark session
        spark = SparkSession.builder.appName("MyJob").getOrCreate()
        
        # Bind job context
        job_logger = logger.bind(job_type="etl", version="1.2.3")
        
        # Process data
        job_logger.info("Reading source data")
        df = spark.read.parquet("Files/raw/sales")
        
        job_logger.info(f"Processing {df.count()} records")
        # ... transformation logic ...
        
        job_logger.success("Job completed successfully")
        
    except Exception as e:
        logger.exception("Job failed")
        raise
    
    finally:
        # Upload logs
        logger.upload_log_to_lakehouse("Files/logs/spark_job.log")
        
        # Stop Spark
        stop_spark_if_active()

if __name__ == "__main__":
    main()
```

### Example 3: Databricks Job

```python
from laketrace import get_laketrace_logger, stop_spark_if_active
from pyspark.sql import SparkSession

def run_databricks_job():
    # Logger automatically detects Databricks environment
    logger = get_laketrace_logger("databricks_etl")
    
    logger.info("Databricks job initialized")
    
    spark = SparkSession.builder.getOrCreate()
    
    # Bind pipeline context
    pipeline_logger = logger.bind(
        pipeline="customer_360",
        stage="bronze_to_silver"
    )
    
    try:
        # Read from bronze
        pipeline_logger.info("Reading bronze layer")
        bronze_df = spark.read.table("bronze.customers")
        
        # Transform
        pipeline_logger.info("Applying transformations")
        silver_df = bronze_df.filter("is_active = true")
        
        # Write to silver
        pipeline_logger.info("Writing to silver layer")
        silver_df.write.mode("overwrite").saveAsTable("silver.customers")
        
        pipeline_logger.success("Pipeline completed successfully")
        
    except Exception as e:
        pipeline_logger.exception("Pipeline failed")
        raise
    
    finally:
        # Upload to DBFS
        logger.upload_log_to_lakehouse("dbfs:/logs/customer_360.log")
        stop_spark_if_active()

if __name__ == "__main__":
    run_databricks_job()
```

### Example 4: Spark Driver with Bound Context

```python
from laketrace import get_laketrace_logger
from datetime import datetime

# Create base logger
base_logger = get_laketrace_logger(
    "multi_stage_pipeline",
    config={"level": "INFO", "json": True}
)

# Track pipeline metadata
run_date = datetime.now().strftime("%Y-%m-%d")
base_logger = base_logger.bind(run_date=run_date, environment="production")

# Stage 1: Extract
extract_logger = base_logger.bind(stage="extract")
extract_logger.info("Starting extraction")
# ... extraction logic ...
extract_logger.success("Extraction complete", records=10000)

# Stage 2: Transform
transform_logger = base_logger.bind(stage="transform")
transform_logger.info("Starting transformation")
# ... transformation logic ...
transform_logger.success("Transformation complete", records=9500)

# Stage 3: Load
load_logger = base_logger.bind(stage="load")
load_logger.info("Starting load")
# ... load logic ...
load_logger.success("Load complete", records=9500)

# Final summary
base_logger.info("Pipeline completed", total_runtime_seconds=125)

# Upload consolidated log
base_logger.upload_log_to_lakehouse("Files/logs/pipeline.log")
```

## 🧵 Microsoft Fabric Specific Guidance

### Fabric Notebook Usage

Use LakeTrace in the notebook driver process and keep logging simple and light:

- Use `get_laketrace_logger()` once per notebook.
- Use `logger.tail()` for quick inspection during interactive work.
- Upload logs at the end with `upload_log_to_lakehouse()`.

Example pattern:

```python
from laketrace import get_laketrace_logger

logger = get_laketrace_logger("fabric_notebook")
logger.info("Notebook started")

# ... work ...

logger.tail(20)
logger.upload_log_to_lakehouse("Files/logs/notebook_run.log")
```

### Fabric Spark Job Definitions

In Spark jobs, keep logging on the driver only and use end-of-run upload:

- Call `stop_spark_if_active()` in `finally`.
- Use a stable log path under `Files/` so it lands in the Lakehouse.
- Avoid logging from executors (use `print()` there).

Example pattern:

```python
from laketrace import get_laketrace_logger, stop_spark_if_active

logger = get_laketrace_logger("fabric_job")

try:
    # Spark work on driver
    logger.info("Job started")
    # ... work ...
finally:
    logger.upload_log_to_lakehouse("Files/logs/fabric_job.log")
    stop_spark_if_active()
```

## ⚡ High Concurrency Mode Tuning (Fabric)

High Concurrency Mode shares a single Spark session across notebooks. LakeTrace is safe for this mode when used on the driver. For best performance and lower contention:

- Keep logging **driver-only**; avoid executor logging.
- Use `INFO` or `WARNING` for busy notebooks.
- Consider `stdout=False` if job output becomes noisy.
- Keep `enqueue=False` (default) to avoid background queue overhead in shared sessions.

Recommended config for busy concurrent notebooks:

```python
logger = get_laketrace_logger(
    "fabric_concurrent",
    config={
        "level": "INFO",
        "stdout": False,
        "enqueue": False,
        "rotation_mb": 20,
        "retention_files": 10,
    }
)
```

## ⚙️ Configuration

Configure the logger by passing a configuration dictionary:

```python
logger = get_laketrace_logger(
    "my_job",
    config={
        "log_dir": "/custom/log/path",      # Log directory (default: /tmp/laketrace_logs)
        "rotation_mb": 20,                   # Rotate after 20 MB (default: 10)
        "retention_files": 10,               # Keep 10 files (default: 5)
        "level": "DEBUG",                    # Log level (default: INFO)
        "json": True,                        # JSON format (default: True)
        "stdout": True,                      # Emit to stdout (default: True)
        "compression": "gz",                 # Compression: gz, zip, none (default: none)
        "add_runtime_context": True,         # Add platform metadata (default: True)
    }
)
```

## 🏗️ Architecture

### Design Principles

1. **Driver-Only Logging**: LakeTrace is designed for Spark driver processes only. Never use it in executor functions (UDFs, map operations, etc.)
2. **No Remote Appends**: All logging is done to local files with rotation. No remote file system writes during log operations
3. **Bounded Retries**: Upload operations have a maximum retry count (default: 2) to prevent infinite loops
4. **Graceful Degradation**: Logging failures never crash your application

### Runtime Detection

LakeTrace automatically detects the execution environment:

- **Microsoft Fabric**: Detected via `notebookutils` module or Fabric environment variables
- **Databricks**: Detected via `dbutils` or `DATABRICKS_RUNTIME_VERSION` environment variable
- **Generic Spark**: Detected via active `SparkSession`
- **Local**: Default fallback for local development

### Log Format

**JSON Format** (default):
```json
{
  "timestamp": "2024-01-15T10:30:45.123456+00:00",
  "level": "INFO",
  "message": "Processing sales data",
  "logger_name": "my_job",
  "hostname": "spark-driver-01",
  "pid": 12345,
  "platform": "fabric",
  "runtime_type": "fabric",
  "run_id": "abc-123",
  "stage": "extract",
  "dataset": "sales"
}
```

**Text Format**:
```
2024-01-15 10:30:45 | INFO     | my_job [run_id=abc-123, stage=extract] | Processing sales data
```

## 🔧 API Reference

### `get_laketrace_logger(name, config=None, run_id=None)`

Factory function to get or create a logger instance.

**Parameters:**
- `name` (str): Logger name
- `config` (dict, optional): Configuration dictionary
- `run_id` (str, optional): Run identifier for correlation

**Returns:** `LakeTraceLogger` instance

### `LakeTraceLogger`

Main logger class with the following methods:

#### Logging Methods
- `trace(message, **kwargs)`: Log trace-level message
- `debug(message, **kwargs)`: Log debug-level message
- `info(message, **kwargs)`: Log info-level message
- `success(message, **kwargs)`: Log success-level message
- `warning(message, **kwargs)`: Log warning-level message
- `error(message, **kwargs)`: Log error-level message
- `critical(message, **kwargs)`: Log critical-level message
- `exception(message, **kwargs)`: Log exception with traceback

#### Context Methods
- `bind(**kwargs)`: Create new logger with bound context fields

#### Utility Methods
- `tail(n=50)`: Print last N lines from log file
- `upload_log_to_lakehouse(target_path, max_retries=2)`: Upload log to lakehouse storage

### `RuntimeDetector`

Utility class for environment detection:

- `detect_platform()`: Returns `RuntimePlatform` enum
- `get_runtime_metadata()`: Returns runtime metadata dictionary

### `stop_spark_if_active()`

Safely stops active SparkSession if present.

## ⚠️ Important Notes

### Spark Executor Warning

**DO NOT use LakeTrace in Spark executors (UDFs, map functions, etc.)**

```python
# ❌ WRONG - Don't do this
def my_udf(value):
    logger = get_laketrace_logger("executor")  # Will cause issues!
    logger.info(f"Processing {value}")
    return value.upper()

# ✅ CORRECT - Use print() in executors
def my_udf(value):
    print(f"Processing {value}")  # Safe for executors
    return value.upper()
```

### Lakehouse Upload Pattern

The `upload_log_to_lakehouse()` method should be called **once at the end of your job**:

```python
# ✅ CORRECT - Single upload at end
logger.info("Step 1 complete")
logger.info("Step 2 complete")
logger.upload_log_to_lakehouse("Files/logs/job.log")  # Called once

# ❌ WRONG - Don't upload repeatedly
logger.info("Step 1 complete")
logger.upload_log_to_lakehouse("Files/logs/job.log")  # Too frequent!
logger.info("Step 2 complete")
logger.upload_log_to_lakehouse("Files/logs/job.log")  # Too frequent!
```

## 📊 Platform-Specific Features

### Microsoft Fabric
- Uses `notebookutils.fs.put()` for lakehouse upload
- Detects workspace and lakehouse IDs automatically
- Works in both notebooks and Spark job definitions

### Databricks
- Uses `dbutils.fs.put()` for DBFS upload
- Detects cluster, job, and run IDs automatically
- Supports both interactive and scheduled jobs

## 📝 License

MIT License - see LICENSE file for details

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## 📚 Additional Resources

- [Microsoft Fabric Documentation](https://learn.microsoft.com/fabric/)
- [Databricks Documentation](https://docs.databricks.com/)
- [Loguru Documentation](https://loguru.readthedocs.io/)
