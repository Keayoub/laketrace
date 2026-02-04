"""
Example 4: Multi-Stage Pipeline with Bound Context

This example demonstrates advanced usage of LakeTrace with multiple stages,
hierarchical context binding, and comprehensive error handling.
"""

from laketrace import get_logger
from datetime import datetime, timedelta
from typing import Dict, Any
import random
import time


class DataPipeline:
    """Example multi-stage data pipeline with LakeTrace logging."""
    
    def __init__(self, pipeline_name: str, run_date: str):
        """
        Initialize pipeline with logger.
        
        Args:
            pipeline_name: Name of the pipeline
            run_date: Date for this pipeline run (YYYY-MM-DD)
        """
        # Create base logger with pipeline context
        self.base_logger = get_logger(
            pipeline_name,
            config={
                "level": "DEBUG",
                "rotation_mb": 10,
                "json": True,
            }
        )
        
        # Bind pipeline-level context
        self.logger = self.base_logger.bind(
            run_date=run_date,
            pipeline_version="4.5.2",
            environment="production"
        )
        
        self.run_date = run_date
        self.stats: Dict[str, Any] = {}
    
    def extract_data(self, source: str) -> Dict[str, Any]:
        """
        Extract data from source.
        
        Args:
            source: Data source identifier
        
        Returns:
            Extraction results
        """
        # Create stage-specific logger
        extract_logger = self.logger.bind(stage="extract", source=source)
        
        extract_logger.info(f"Starting data extraction from {source}")
        
        try:
            # Simulate extraction
            extract_logger.debug("Connecting to data source")
            time.sleep(0.5)
            
            record_count = random.randint(5000, 15000)
            extract_logger.debug(f"Reading data", estimated_records=record_count)
            
            # Simulate some validation
            validation_errors = random.randint(0, 50)
            if validation_errors > 0:
                extract_logger.warning(
                    f"Validation errors detected",
                    error_count=validation_errors
                )
            
            results = {
                "source": source,
                "records": record_count,
                "validation_errors": validation_errors,
            }
            
            extract_logger.success(
                "Extraction completed successfully",
                **results
            )
            
            return results
        
        except Exception as e:
            extract_logger.exception("Extraction failed")
            raise
    
    def transform_data(self, extract_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform extracted data.
        
        Args:
            extract_results: Results from extraction stage
        
        Returns:
            Transformation results
        """
        source = extract_results["source"]
        input_records = extract_results["records"]
        
        # Create stage-specific logger with inherited context
        transform_logger = self.logger.bind(
            stage="transform",
            source=source,
            input_records=input_records
        )
        
        transform_logger.info("Starting data transformation")
        
        try:
            # Simulate transformation steps
            transform_logger.debug("Applying data quality rules")
            time.sleep(0.3)
            
            # Simulate some records being filtered out
            filtered_records = random.randint(10, 100)
            valid_records = input_records - filtered_records
            
            transform_logger.debug(
                "Data quality filters applied",
                filtered_out=filtered_records,
                valid_records=valid_records
            )
            
            transform_logger.debug("Applying business transformations")
            time.sleep(0.4)
            
            # Simulate enrichment
            enrichment_fields = ["customer_segment", "risk_score", "value_tier"]
            transform_logger.debug(
                "Enriching data",
                enrichment_fields=enrichment_fields
            )
            
            results = {
                "source": source,
                "input_records": input_records,
                "output_records": valid_records,
                "filtered_records": filtered_records,
            }
            
            transform_logger.success(
                "Transformation completed successfully",
                **results
            )
            
            return results
        
        except Exception as e:
            transform_logger.exception("Transformation failed")
            raise
    
    def load_data(self, transform_results: Dict[str, Any], destination: str) -> Dict[str, Any]:
        """
        Load transformed data to destination.
        
        Args:
            transform_results: Results from transformation stage
            destination: Data destination identifier
        
        Returns:
            Load results
        """
        source = transform_results["source"]
        output_records = transform_results["output_records"]
        
        # Create stage-specific logger
        load_logger = self.logger.bind(
            stage="load",
            source=source,
            destination=destination,
            records=output_records
        )
        
        load_logger.info(f"Starting data load to {destination}")
        
        try:
            load_logger.debug("Preparing data for load")
            time.sleep(0.2)
            
            load_logger.debug("Writing data to destination")
            time.sleep(0.6)
            
            # Simulate partition information
            partitions_written = random.randint(5, 20)
            load_logger.debug(f"Data partitioned", partition_count=partitions_written)
            
            results = {
                "destination": destination,
                "records_loaded": output_records,
                "partitions": partitions_written,
            }
            
            load_logger.success(
                "Load completed successfully",
                **results
            )
            
            return results
        
        except Exception as e:
            load_logger.exception("Load failed")
            raise
    
    def run(self, sources: list, destination: str) -> None:
        """
        Run the complete pipeline.
        
        Args:
            sources: List of data sources
            destination: Data destination
        """
        pipeline_start = time.time()
        
        self.logger.info(
            "=== Pipeline Execution Started ===",
            sources=sources,
            destination=destination
        )
        
        try:
            # Process each source
            total_input_records = 0
            total_output_records = 0
            
            for source in sources:
                source_logger = self.logger.bind(data_source=source)
                source_logger.info(f"Processing source: {source}")
                
                # Extract
                extract_results = self.extract_data(source)
                
                # Transform
                transform_results = self.transform_data(extract_results)
                
                # Load
                load_results = self.load_data(transform_results, destination)
                
                # Accumulate stats
                total_input_records += extract_results["records"]
                total_output_records += transform_results["output_records"]
                
                source_logger.info(f"Source {source} processing completed")
            
            # Calculate pipeline stats
            pipeline_duration = time.time() - pipeline_start
            
            self.stats = {
                "sources_processed": len(sources),
                "total_input_records": total_input_records,
                "total_output_records": total_output_records,
                "data_quality_pass_rate": f"{(total_output_records/total_input_records)*100:.2f}%",
                "duration_seconds": round(pipeline_duration, 2),
            }
            
            self.logger.success(
                "=== Pipeline Execution Completed Successfully ===",
                **self.stats
            )
        
        except Exception as e:
            pipeline_duration = time.time() - pipeline_start
            self.logger.error(
                "=== Pipeline Execution Failed ===",
                duration_seconds=round(pipeline_duration, 2)
            )
            self.logger.exception("Pipeline error details")
            raise
        
        finally:
            # Show recent logs
            print("\n")
            self.logger.tail(15)
            
            # Upload logs
            log_filename = f"pipeline_{self.run_date.replace('-', '')}.log"
            self.logger.info(f"Uploading logs: {log_filename}")
            self.base_logger.upload_log_to_lakehouse(f"Files/logs/pipelines/{log_filename}")


def main():
    """Main entry point."""
    # Initialize pipeline
    run_date = datetime.now().strftime("%Y-%m-%d")
    
    pipeline = DataPipeline(
        pipeline_name="multi_source_etl_pipeline",
        run_date=run_date
    )
    
    # Define sources and destination
    sources = ["sales_db", "marketing_db", "customer_db"]
    destination = "data_warehouse.fact_sales"
    
    # Run pipeline
    pipeline.run(sources=sources, destination=destination)
    
    print("\n=== Pipeline Stats ===")
    for key, value in pipeline.stats.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
