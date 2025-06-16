from libactimetry.db.TimescaleDBDataClient import TimescaleDBDataClient
from abc import ABC, abstractmethod
import pandas as pd


class ImporterError(Exception):
    """
    Custom exception for importer errors.
    """

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class BucketNotFoundError(ImporterError):
    """
    Exception raised when a specified bucket is not found.
    """

    def __init__(self, bucket_name: str):
        super().__init__(f"Bucket '{bucket_name}' not found.")
        self.bucket_name = bucket_name


class BucketAlreadyExistsError(ImporterError):
    """
    Exception raised when trying to create a bucket that already exists.
    """

    def __init__(self, bucket_name: str):
        super().__init__(f"Bucket '{bucket_name}' already exists.")
        self.bucket_name = bucket_name


class BucketWriteError(ImporterError):
    """
    Exception raised when there is an error writing to a bucket.
    """

    def __init__(self, bucket_name: str, message: str):
        super().__init__(f"Error writing to bucket '{bucket_name}': {message}")
        self.bucket_name = bucket_name
        self.message = message


class BucketCreateError(ImporterError):
    """
    Exception raised when there is an error creating a bucket.
    """

    def __init__(self, bucket_name: str, message: str):
        super().__init__(f"Error creating bucket '{bucket_name}': {message}")
        self.bucket_name = bucket_name
        self.message = message


class BaseImporter(ABC):
    """
    Base class for importers.
    """

    def __init__(self, client: TimescaleDBDataClient, bucket_name: str):
        self.db_client = client
        self.bucket_name = bucket_name

    def import_data(self, bucket_name: str):
        # Create bucket if does not exist
        if bucket_name not in self.db_client.available_bucket_names():
            if not self.db_client.create_bucket(bucket_name):
                raise BucketCreateError(bucket_name, "Failed to create bucket.")

        self.import_data_internal(bucket_name)

    @abstractmethod
    def import_data_internal(self, bucket_name: str):
        """
        Internal method to import data into the specified TimeScaleDB/InfluxDB bucket.
        This method should be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def delete_data(self, bucket_name: str):
        """
        Delete all data from the specified TimeScaleDB/InfluxDB bucket.
        """
        if bucket_name not in self.db_client.available_bucket_names():
            raise BucketNotFoundError(bucket_name)

        # Delete the bucket
        if not self.db_client.client.buckets_api().delete_bucket(bucket_name):
            raise ImporterError(f"Failed to delete bucket '{bucket_name}'.")

    def write_data_frame(
        self,
        bucket_name: str,
        measurement_name: str,
        df: pd.DataFrame,
        metadata: dict = None,
    ):
        """
        Save the DataFrame to the specified TimeScaleDB/InfluxDB bucket.
        """
        # Write the DataFrame to the bucket
        if not self.db_client.write_data(
            bucket_name, measurement_name, df, metadata=metadata
        ):
            raise BucketWriteError(bucket_name, "Failed to write data.")

        # Re-query for test
        queried_df = self.db_client.query_data(bucket_name, measurement_name)
        if queried_df.empty:
            raise ImporterError(
                f"No data found in bucket '{bucket_name}' after writing."
            )
