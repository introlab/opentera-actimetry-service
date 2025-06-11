from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
import pandas as pd


class InfluxDBDataClient:
    def __init__(self, host: str, port: int, token: str, org: str = None):
        self.host = host
        self.port = port
        self.token = token
        self.org = org
        self.client = InfluxDBClient(
            url=f"http://{self.host}:{self.port}", token=self.token, org=self.org
        )

    def available_bucket_names(self) -> list[str]:
        """
        List all available buckets in the InfluxDB instance.
        """
        buckets_info = self.client.buckets_api().find_buckets()
        return [bucket.name for bucket in buckets_info.buckets]

    def create_bucket(self, bucket_name: str) -> bool:
        """
        Create a new bucket in the InfluxDB instance.
        """
        if bucket_name not in self.available_bucket_names():
            self.client.buckets_api().create_bucket(bucket_name=bucket_name)
            print(f"Bucket '{bucket_name}' created successfully.")
            return True
        else:
            print(f"Bucket '{bucket_name}' already exists.")
            return False

    def delete_bucket(self, bucket_name: str) -> bool:
        """
        Delete a specified bucket in the InfluxDB instance.
        """
        if bucket_name in self.available_bucket_names():
            self.client.buckets_api().delete_bucket(
                self.client.buckets_api().find_bucket_by_name(bucket_name).id
            )
            print(f"Bucket '{bucket_name}' deleted successfully.")
            return True
        else:
            print(f"Bucket '{bucket_name}' does not exist.")
            return False

    def write_data(
        self, bucket_name: str, measurement_name: str, data: pd.DataFrame
    ) -> bool:
        """
        Write data to a specified bucket in the InfluxDB instance.
        """
        if bucket_name not in self.available_bucket_names():
            raise ValueError(f"Bucket '{bucket_name}' does not exist.")

        try:
            result = self.client.write_api(write_options=SYNCHRONOUS).write(
                bucket=bucket_name,
                record=data,
                data_frame_measurement_name=measurement_name,
            )
            print(f"Data written to bucket '{bucket_name}' successfully.")
            return True
        except Exception as e:
            print(f"Error writing data to bucket '{bucket_name}': {e}")
            return False

    def query_data(self, bucket_name: str, measurement: str) -> pd.DataFrame:
        """
        Query data from a specified bucket in the InfluxDB instance.
        """
        if bucket_name not in self.available_bucket_names():
            raise ValueError(f"Bucket '{bucket_name}' does not exist.")

        query_api = self.client.query_api()
        result = query_api.query(
            query=f'from(bucket: "{bucket_name}") |> range(start: 0) |> filter(fn: (r) => r._measurement == "{measurement}")',
            org=self.org,
        )
        # Convert the result to a DataFrame
        data_frames = []
        for table in result:
            for record in table.records:
                data_frames.append(record.values)
        df = pd.DataFrame(data_frames)
        print(f"Data queried from bucket '{bucket_name}' successfully.")
        return df

    def close(self):
        """
        Close the InfluxDB client connection.
        """
        self.client.close()
        print("InfluxDB client connection closed.")
