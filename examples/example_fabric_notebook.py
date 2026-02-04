"""
Example 1: Microsoft Fabric Notebook Usage

This example demonstrates how to use LakeTrace in a Fabric notebook environment.
"""

from laketrace import get_laketrace_logger

# Initialize logger
logger = get_laketrace_logger("fabric_notebook_demo")

# Basic logging
logger.info("Notebook execution started")
logger.debug("Initializing data sources")

# Bind context for structured logging
logger.info("Starting data extraction phase")
extract_logger = logger.bind(stage="extract", source="sales_db")

try:
    # Simulate extraction
    extract_logger.info("Connecting to source database")
    extract_logger.info("Extracting sales data for Q4 2025")
    extract_logger.success("Extraction completed successfully", records=15000)
    
except Exception as e:
    extract_logger.exception("Extraction failed")
    raise

# Next stage with different context
transform_logger = logger.bind(stage="transform")
transform_logger.info("Starting data transformation")
transform_logger.info("Applying business rules")
transform_logger.success("Transformation completed", output_records=14500)

# Load stage
load_logger = logger.bind(stage="load", destination="lakehouse")
load_logger.info("Loading data to lakehouse")
load_logger.success("Load completed successfully")

# View recent logs (useful in notebook for debugging)
print("\n=== Recent Logs ===")
logger.tail(10)

# Upload logs to lakehouse at end of notebook
logger.info("Uploading logs to lakehouse")
success = logger.upload_log_to_lakehouse("Files/logs/fabric_notebook_demo.log")

if success:
    logger.info("Notebook execution completed successfully")
else:
    logger.warning("Notebook completed but log upload failed")
