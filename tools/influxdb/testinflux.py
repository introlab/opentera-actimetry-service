from influxdb_client import InfluxDBClient
import pandas as pd

# InfluxDB setup
url = "http://influxdb:8086"
token = "my-super-token"
org = "my-org"
bucket = "my-bucket"

# Connect
client = InfluxDBClient(url=url, token=token, org=org)

# Flux query
query = f"""
from(bucket: "{bucket}")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "temperature")
"""

# Query into a DataFrame
df = client.query_api().query_data_frame(query)

print(df.head())
