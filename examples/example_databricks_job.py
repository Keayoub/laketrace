"""
Example 3: Databricks Job

This example demonstrates how to use LakeTrace in a Databricks job environment.
"""

from laketrace import get_logger, stop_spark_if_active
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, current_timestamp
import sys


def run_databricks_etl():
    """
    Run Databricks ETL pipeline with LakeTrace logging.
    
    This demonstrates a multi-stage pipeline:
    1. Bronze to Silver (cleansing)
    2. Silver to Gold (business logic)
    """
    
    # Initialize logger - automatically detects Databricks environment
    logger = get_logger(
        "databricks_customer_360_pipeline",
        config={
            "level": "INFO",
            "rotation_mb": 15,
            "retention_files": 7,
        }
    )
    
    logger.info("=== Databricks Customer 360 Pipeline Started ===")
    
    # Get or create Spark session
    spark = SparkSession.builder.getOrCreate()
    
    # Bind pipeline metadata
    pipeline_logger = logger.bind(
        pipeline="customer_360",
        version="3.2.1",
        cluster_type="job_cluster"
    )
    
    try:
        # ===== Stage 1: Bronze to Silver =====
        bronze_logger = pipeline_logger.bind(stage="bronze_to_silver")
        bronze_logger.info("Starting bronze to silver transformation")
        
        # Read bronze layer
        bronze_logger.info("Reading bronze layer customer data")
        bronze_df = spark.read.table("bronze.customers")
        bronze_count = bronze_df.count()
        bronze_logger.info(f"Bronze layer loaded", records=bronze_count)
        
        # Apply data quality rules
        bronze_logger.info("Applying data quality filters")
        silver_df = bronze_df \
            .filter(col("customer_id").isNotNull()) \
            .filter(col("email").isNotNull()) \
            .filter(col("is_active") == True) \
            .withColumn("last_updated", current_timestamp())
        
        silver_count = silver_df.count()
        rejected_count = bronze_count - silver_count
        
        bronze_logger.info(
            "Data quality filters applied",
            valid_records=silver_count,
            rejected_records=rejected_count
        )
        
        # Write to silver layer
        bronze_logger.info("Writing to silver layer")
        silver_df.write \
            .mode("overwrite") \
            .option("overwriteSchema", "true") \
            .saveAsTable("silver.customers")
        
        bronze_logger.success("Bronze to silver transformation completed")
        
        # ===== Stage 2: Silver to Gold =====
        gold_logger = pipeline_logger.bind(stage="silver_to_gold")
        gold_logger.info("Starting silver to gold transformation")
        
        # Read silver layer
        silver_enriched_df = spark.read.table("silver.customers")
        
        # Apply business logic
        gold_logger.info("Applying business rules and enrichment")
        gold_df = silver_enriched_df \
            .withColumn(
                "customer_tier",
                when(col("lifetime_value") > 10000, "Platinum")
                .when(col("lifetime_value") > 5000, "Gold")
                .when(col("lifetime_value") > 1000, "Silver")
                .otherwise("Bronze")
            )
        
        # Write to gold layer
        gold_logger.info("Writing to gold layer")
        gold_df.write \
            .mode("overwrite") \
            .option("overwriteSchema", "true") \
            .saveAsTable("gold.customer_360")
        
        gold_count = gold_df.count()
        gold_logger.success(
            "Silver to gold transformation completed",
            output_records=gold_count
        )
        
        # ===== Pipeline Summary =====
        pipeline_logger.success(
            "Pipeline completed successfully",
            bronze_records=bronze_count,
            silver_records=silver_count,
            gold_records=gold_count,
            data_quality_pass_rate=f"{(silver_count/bronze_count)*100:.2f}%"
        )
        
        return 0
    
    except Exception as e:
        pipeline_logger.exception("Pipeline failed")
        return 1
    
    finally:
        # Upload logs to DBFS
        logger.info("Uploading logs to DBFS")
        logger.upload_log_to_lakehouse("dbfs:/mnt/logs/customer_360_pipeline.log")
        
        # Stop Spark
        logger.info("Stopping Spark session")
        stop_spark_if_active()
        
        logger.info("=== Databricks Customer 360 Pipeline Finished ===")


if __name__ == "__main__":
    exit_code = run_databricks_etl()
    sys.exit(exit_code)
