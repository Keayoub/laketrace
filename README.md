# LakeTrace Logger

**Production-grade logging for Spark data platforms (Microsoft Fabric & Databricks)**

LakeTrace is a cross-platform Python logging module designed specifically for Spark data platforms. It provides safe, performant logging with structured output, local file rotation, and optional lakehouse storage integration.

## Installation

```bash
pip install laketrace
```

## ✅ Why LakeTrace (vs SparkLogger)

LakeTrace is built for Spark data platforms and removes the common failure modes of basic Spark logging:

- **Driver-safe**: no executor logging, no distributed file writes.
- **No remote appends**: all logging stays local with rotation and retention.
- **Structured JSON**: consistent records with runtime metadata and bound context.
- **Fabric + Databricks aware**: platform detection built in.
- **Crash‑safe logging**: optional `catch` prevents formatter errors from breaking jobs.
- **Scalable I/O**: enqueue mode for high-throughput workloads.

## ✨ Key Features

- Cross‑platform: Fabric notebooks, Fabric Spark jobs, Databricks notebooks/jobs
- Structured JSON with context binding and runtime metadata
- Local rotation, retention, and compression
- Stdout emission for job logs
- Optional end‑of‑run lakehouse upload
- Thread‑safe and notebook re‑execution safe

## 🚀 Quick Start

```python
from laketrace import get_logger

logger = get_logger("my_job")
logger.info("Starting data processing")

stage = logger.bind(stage="extract", dataset="sales")
stage.info("Extracting sales data")

logger.upload_log_to_lakehouse("Files/logs/my_job.log")
```

## ⚙️ Configuration Highlights

```python
logger = get_logger(
    "my_job",
    config={
        "log_dir": "/tmp/laketrace_logs",
        "rotation": "500 MB",
        "retention": "7 days",
        "compression": "gz",
        "level": "INFO",
        "json": True,
        "stdout": True,
        "serialize": True,
        "enqueue": False,
        "filter": None,
        "formatter": None,
        "catch": True,
    }
)
```

## 🔄 Migration Guides

### From SparkLogger

SparkLogger often leads to executor logging overhead and cross-partition serialization issues. LakeTrace moves all logging to the driver:

**Before (SparkLogger):**

```python
from pyspark.taskcontext import TaskContext
from delta.tables import DeltaTable

# Problem: Executors attempt to log, causing distributed serialization
for partition in range(num_partitions):
    df.filter(...).collect()  # Executor logs serialized back to driver
```

**After (LakeTrace):**

```python
from laketrace import get_logger

logger = get_logger("my_job")  # Driver only

# Log from driver, use print() in executors
df = spark.read.parquet(path)
logger.info(f"Loaded {df.count()} rows")  # Clean, structured, driver-safe
```

### From notebookutils.fs.append

Using `notebookutils.fs.append()` for logging causes performance degradation and can hang Spark jobs due to repeated remote I/O per log line. LakeTrace uses local rotation instead:

**Before (notebookutils.fs.append):**

```python
from notebookutils.mssparkutils import fs

# Problem: Each log line triggers remote I/O → job hangs
for i in range(1000):
    fs.append("/mnt/logs/job.log", f"Processing {i}\n")  # Remote write per line
    process_data(i)
```

**After (LakeTrace):**

```python
from laketrace import get_logger

logger = get_logger("my_job")

# Local rotation, zero remote I/O during execution
for i in range(1000):
    logger.info(f"Processing {i}")  # Fast local write, no hangs
    process_data(i)

# Upload once at the end
logger.upload_log_to_lakehouse("/Files/logs/job.log")
```

## 🧪 Workload Test Runner

Run the consolidated workload tests:

```bash
python tests/run_workloads.py
```

Workload groups live under:

- [tests/workloads/basic](tests/workloads/basic)
- [tests/workloads/core](tests/workloads/core)
- [tests/workloads/advanced](tests/workloads/advanced)
- [tests/workloads/performance](tests/workloads/performance)
- [tests/workloads/security](tests/workloads/security)

## ✅ Safety Notes

- **Driver only**: use `print()` in executors.
- **Single upload**: call `upload_log_to_lakehouse()` once at the end.
- **No remote append**: avoids Spark job hangs and retries.

## 📝 License

MIT License - see LICENSE file for details.
