"""
Example: Unified logging for Spark framework + application events.

This example demonstrates how to capture both Spark framework logs
and your application logs in a single LakeTrace logger using the
spark_integration module.

Works identically in:
- Microsoft Fabric Notebooks
- Microsoft Fabric Spark Jobs
- Databricks Notebooks
- Databricks Jobs
"""

from pyspark.sql import SparkSession
from laketrace import setup_logging_with_spark, stop_spark_and_upload_logs


def main():
    """
    Run unified logging example with Spark framework integration.
    """
    
    # Initialize Spark
    spark = SparkSession.builder \
        .appName("UnifiedLoggingExample") \
        .getOrCreate()

    # Setup unified logging (captures both app and Spark logs)
    logger = setup_logging_with_spark(
        app_name="unified_etl",
        spark_session=spark,
        config={
            "level": "INFO",
            "json": True,
            "stdout": True,
            "rotation_mb": 20,
        },
        capture_spark_logs=True,
        spark_log_level="INFO",
    )

    try:
        # Application event
        logger.info("Starting ETL job")
        
        # Spark framework logs will be captured automatically
        logger.info("Creating sample data")
        data = [
            {"id": 1, "name": "Alice", "sales": 1000},
            {"id": 2, "name": "Bob", "sales": 1500},
            {"id": 3, "name": "Charlie", "sales": 2000},
        ]
        
        # Create DataFrame (Spark logs captured here)
        df = spark.createDataFrame(data)
        logger.info(f"Created DataFrame with {df.count()} rows")
        
        # Show schema (Spark logs captured)
        logger.info("DataFrame schema created")
        df.printSchema()
        
        # Transformation step
        logger.info("Starting data transformations")
        
        # Filter (Spark logs captured)
        df_filtered = df.filter("sales > 1000")
        logger.info(f"Filtered data: {df_filtered.count()} rows remaining")
        
        # Aggregation (Spark logs captured)
        logger.info("Computing sales statistics")
        stats = df_filtered.groupby().sum("sales").collect()[0][0]
        logger.info("Sales aggregation complete", total_sales=stats)
        
        # Bind context for structured logging
        transform_logger = logger.bind(stage="transform", dataset="sales")
        transform_logger.info("Data transformation stage", records_processed=df.count())
        
        # Load step
        logger.info("Starting data load phase")
        # Note: This would actually write to storage in production
        # df_filtered.write.mode("overwrite").parquet("Files/output/sales")
        logger.success(
            "Data load complete",
            output_records=df_filtered.count(),
            output_path="Files/output/sales"
        )
        
        # Final summary
        logger.success(
            "ETL job completed successfully",
            total_input_records=df.count(),
            final_output_records=df_filtered.count(),
            job_duration_seconds=30,
        )

    except Exception as e:
        # Exception logging (including stack trace)
        logger.exception("ETL job failed")
        raise

    finally:
        # Upload logs and stop Spark
        # In production, use the helper function:
        # stop_spark_and_upload_logs(
        #     logger,
        #     target_path="Files/logs/unified_etl.log",
        #     spark_session=spark
        # )
        
        # Or manually:
        logger.info("Finalizing job")
        logger.upload_log_to_lakehouse("Files/logs/unified_etl.log")
        spark.stop()
        logger.info("Job resources cleaned up")


if __name__ == "__main__":
    main()
