"""
Example 2: Microsoft Fabric Spark Job Definition

This example demonstrates how to use LakeTrace in a Fabric Spark Job Definition.
This is the main.py file for a Fabric Spark job.
"""

from laketrace import get_logger, stop_spark_if_active
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, sum as _sum
import sys


def main():
    """Main entry point for Fabric Spark job."""
    
    # Initialize logger with custom configuration
    logger = get_logger(
        "fabric_spark_etl_job",
        config={
            "log_dir": "/tmp/fabric_spark_logs",
            "rotation_mb": 20,
            "retention_files": 10,
            "level": "INFO",
            "json": True,
            "stdout": True,
        }
    )
    
    logger.info("=== Fabric Spark Job Started ===")
    logger.info(f"Python version: {sys.version}")
    
    # Bind job metadata
    job_logger = logger.bind(
        job_name="daily_sales_aggregation",
        job_version="2.1.0",
        environment="production"
    )
    
    spark = None
    
    try:
        # Create Spark session
        job_logger.info("Initializing Spark session")
        spark = SparkSession.builder \
            .appName("FabricDailySalesAggregation") \
            .getOrCreate()
        
        job_logger.info(f"Spark version: {spark.version}")
        
        # Stage 1: Extract
        extract_logger = job_logger.bind(stage="extract")
        extract_logger.info("Reading source data from lakehouse")
        
        sales_df = spark.read.parquet("Files/raw/sales/daily_transactions")
        record_count = sales_df.count()
        
        extract_logger.info(f"Loaded sales transactions", records=record_count)
        
        # Stage 2: Transform
        transform_logger = job_logger.bind(stage="transform")
        transform_logger.info("Applying aggregations")
        
        # Aggregate sales by product and date
        aggregated_df = sales_df.groupBy("product_id", "sale_date") \
            .agg(
                _sum("quantity").alias("total_quantity"),
                _sum("revenue").alias("total_revenue")
            )
        
        agg_count = aggregated_df.count()
        transform_logger.info(f"Aggregation completed", output_records=agg_count)
        
        # Stage 3: Load
        load_logger = job_logger.bind(stage="load")
        load_logger.info("Writing to gold layer")
        
        aggregated_df.write \
            .mode("overwrite") \
            .format("delta") \
            .save("Tables/gold/sales_daily_aggregation")
        
        load_logger.success("Data successfully written to gold layer")
        
        # Job summary
        job_logger.success(
            "Job completed successfully",
            input_records=record_count,
            output_records=agg_count
        )
        
        return 0
    
    except Exception as e:
        job_logger.exception("Job failed with error")
        return 1
    
    finally:
        # Upload logs to lakehouse
        logger.info("Uploading job logs to lakehouse")
        logger.upload_log_to_lakehouse("Files/logs/spark_jobs/daily_sales_aggregation.log")
        
        # Stop Spark session
        if spark:
            job_logger.info("Stopping Spark session")
            stop_spark_if_active()
        
        job_logger.info("=== Fabric Spark Job Finished ===")


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
