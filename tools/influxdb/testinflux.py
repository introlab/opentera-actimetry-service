from influxdb_client import InfluxDBClient
import pandas as pd

# InfluxDB setup
url = "http://127.0.0.1:8086"
token = "QZhiRft2wrZOqfM5epkW_c0OIjk8oV1E5EKW3V_qjZPyGMU7ZWk42LmukQ63Ar95tC98MEYwIINKIUEaeVSvYA=="
org = "my-org"
bucket = "my-bucket"


# Define data structures for imu, battery, gps, and temperature using pandas
imu_data = pd.DataFrame(
    {
        "time": pd.date_range(start="2023-01-01", periods=10, freq="T"),
        "acceleration_x": range(10),
        "acceleration_y": range(10, 20),
        "acceleration_z": range(20, 30),
        "gyroscope_x": range(30, 40),
        "gyroscope_y": range(40, 50),
        "gyroscope_z": range(50, 60),
        "magnetometer_x": range(60, 70),
        "magnetometer_y": range(70, 80),
        "magnetometer_z": range(80, 90),
    }
)

battery_data = pd.DataFrame(
    {
        "time": pd.date_range(start="2023-01-01", periods=10, freq="T"),
        "voltage": range(10, 20),
        "current": range(20, 30),
        "level": range(30, 40),
    }
)

gps_data = pd.DataFrame(
    {
        "time": pd.date_range(start="2023-01-01", periods=10, freq="T"),
        "latitude": range(40, 50),
        "longitude": range(50, 60),
        "altitude": range(60, 70),
    }
)

temperature_data = pd.DataFrame(
    {
        "time": pd.date_range(start="2023-01-01", periods=10, freq="T"),
        "temperature": range(70, 80),
    }
)

# Connect
client = InfluxDBClient(url=url, token=token, org=org)

org_obj = client.organizations_api().find_organizations(org="my-org")[0]
org_id = org_obj.id

# Create multiple buckets for testing
buckets = ["imu", "battery", "gps", "temperature"]

# Get already existing buckets
existing_buckets = client.buckets_api().find_buckets()

# Create buckets if they do not exist
for bucket in buckets:
    if not any(b.name == bucket for b in existing_buckets.buckets):
        client.buckets_api().create_bucket(bucket_name=bucket, org_id=org_id)

# Create sample data for each bucket
client.write_api().write(
    bucket="imu", org=org_id, record=imu_data.to_dict(orient="records")
)
client.write_api().write(
    bucket="battery", org=org_id, record=battery_data.to_dict(orient="records")
)
client.write_api().write(
    bucket="gps", org=org_id, record=gps_data.to_dict(orient="records")
)

# # Flux query
# query = f"""
# from(bucket: "{bucket}")
#   |> range(start: -1h)
#   |> filter(fn: (r) => r._measurement == "temperature")
# """

# # Query into a DataFrame
# df = client.query_api().query_data_frame(query)

# print(df.head())
