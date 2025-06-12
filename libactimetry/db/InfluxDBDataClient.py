from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
import pandas as pd
import numpy as np
from influxdb_client import Point, WritePrecision


class InfluxDBDataClient:
    def __init__(self, host: str, port: int, token: str, org: str = None):
        self.host = host
        self.port = port
        self.token = token
        self.org = org
        self.client = InfluxDBClient(
            url=f"http://{self.host}:{self.port}",
            token=self.token,
            org=self.org,
            enable_gzip=True,
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

    def df_to_points(self, df, measurement: str, tag_columns=None, time_column=None):
        """
        Convert a Pandas DataFrame to a list of InfluxDB Point objects.

        Args:
            df (pd.DataFrame): The input DataFrame.
            measurement (str): The measurement name in InfluxDB.
            tag_columns (list[str]): Column names to be used as tags.
            time_column (str or None): Column to be used as the timestamp. If None, uses index.

        Returns:
        list[Point]: List of InfluxDB Point objects.
        """

        tag_columns = tag_columns or []
        points = []

        for idx, row in df.iterrows():
            time = row[time_column] if time_column else idx
            p = Point(measurement)

            # Add tags
            for tag in tag_columns:
                p = p.tag(tag, str(row[tag]))

            # Add fields (everything not a tag or time)
            for col in df.columns:
                if col != time_column and col not in tag_columns:
                    value = row[col]
                    if pd.notnull(value):  # skip NaNs
                        if isinstance(value, (np.integer, np.floating, np.bool_)):
                            # Handle numpy types
                            value = value.item()
                        if isinstance(value, (int, float, bool)):
                            p = p.field(col, value)
                        else:
                            p = p.field(col, str(value))

            # Add timestamp
            p = p.time(time, WritePrecision.NS)
            points.append(p)

        return points

    def write_data(
        self,
        bucket_name: str,
        measurement_name: str,
        data: pd.DataFrame,
        tag_columns: list[str] = None,
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

        flux_query = f"""
        from(bucket: "{bucket_name}")
        |> range(start: 0)
        |> filter(fn: (r) => r._measurement == "{measurement}")
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        """

        records = self.client.query_api().query_data_frame(query=flux_query)

        # records = self.client.query_api().query_data_frame(
        #    query=flux_query,
        #    org=self.org,
        # )

        print("Data queried from bucket:", bucket_name)

        # query_api = self.client.query_api()
        # result = query_api.query(
        #    query=f'from(bucket: "{bucket_name}") |> range(start: 0) |> filter(fn: (r) => r._measurement == "{measurement}")',
        #    org=self.org,
        # )
        # Convert the result to a DataFrame

        # data_frames = []
        # for table in result:
        #    for record in table.records:
        #        data_frames.append(record.values)
        # df = pd.DataFrame(data_frames)
        # print(f"Data queried from bucket '{bucket_name}' successfully.")
        # return df

    def close(self):
        """
        Close the InfluxDB client connection.
        """
        self.client.close()
        print("InfluxDB client connection closed.")
