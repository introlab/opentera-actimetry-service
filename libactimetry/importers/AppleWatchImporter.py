import pandas as pd
import json
import struct
import numpy as np
import os

from libactimetry.importers.BaseImporter import BaseImporter
from libactimetry.db.InfluxDBDataClient import InfluxDBDataClient
from libactimetry.db.TimescaleDBDataClient import TimescaleDBDataClient


class AppleWatchImporter(BaseImporter):
    def __init__(
        self, data_directory: str, db_client: InfluxDBDataClient, bucket_name: str
    ):
        BaseImporter.__init__(self, db_client, bucket_name)
        self.data_directory = data_directory

    def import_data_internal(self, bucket_name: str):
        # Implement data import logic here
        # First, verify that the session.oimi JSON file exists
        session_file = f"{self.data_directory}/session.oimi"
        try:
            with open(session_file, "r") as file:
                # Load the session data from the JSON file
                session_info = json.load(file)

                for file_name in session_info.get("files", []):
                    file_path: str = f"{self.data_directory}/{file_name}"

                    # TODO Check if the file exists before trying to read it
                    # TODO Exceptiion handling if file does not exist
                    if os.path.exists(file_path):
                        if file_name == "watch_Activity.data":
                            self._import_activity_data(file_path, bucket_name)
                        elif file_name == "watch_Battery.data":
                            self._import_battery_data(file_path, bucket_name)
                        elif file_name == "watch_Beacons.data":
                            self._import_beacons_data(file_path, bucket_name)
                        elif file_name == "watch_Calorie.data":
                            self._import_calorie_data(file_path, bucket=bucket_name)
                        elif file_name == "watch_Coordinates.data":
                            self._import_coordinates_data(file_path, bucket=bucket_name)
                        elif file_name == "watch_DyskineticSymptoms.data":
                            self._import_dyskinetic_symptoms_data(
                                file_path, bucket=bucket_name
                            )
                        elif file_name == "watch_GPS.data":
                            self._import_gps_data(file_path, bucket=bucket_name)
                        elif file_name == "watch_Gyroscope.data":
                            self._import_gyroscope_data(file_path, bucket=bucket_name)
                        elif file_name == "watch_Headings.data":
                            self._import_headings_data(file_path, bucket=bucket_name)
                        elif file_name == "watch_HealthKit.data":
                            self._import_healthkit_data(file_path, bucket=bucket_name)
                        elif file_name == "watch_HeartRate.data":
                            self._import_heart_rate_data(file_path, bucket=bucket_name)
                        elif file_name == "watch_Magnetometer.data":
                            self._import_magnetometer_data(
                                file_path, bucket=bucket_name
                            )
                        elif file_name == "watch_Pedometer.data":
                            self._import_pedometer_data(file_path, bucket=bucket_name)
                        elif file_name == "watch_RawAccelerometer.data":
                            self._import_raw_accelerometer_data(
                                file_path, bucket=bucket_name
                            )
                        elif file_name == "watch_Tremor.data":
                            self._import_tremor_data(file_path, bucket=bucket_name)

                        # TODO Do something with watch_logs.txt ?

                print(f"Session data loaded from {session_file}")
        except FileNotFoundError:
            print(f"Error: Session file {session_file} not found.")
            return
        except Exception as e:
            print(f"Error reading session file {session_file}: {e}")
            return

    def delete_data(self, bucket_name: str):
        """
        Delete all data from the specified InfluxDB bucket.
        """
        self.db_client.delete_bucket(bucket_name)

    def _import_activity_data(self, file_path: str, bucket: str):
        """
        Import activity data from the specified file path.

        • time: UInt64–8bytes: time (Unix format) with milliseconds precision
        • Detected Activities: UInt8– 1byte: Detected activitie sand confidence level:
            • Bits 0-1: Confidence level:
                – 00: low
                – 01: medium
                – 10: high
            • Bit 2: Automative activity detected
            • Bit 3: Cycling activity detected
            • Bit 4: Running activity detected
            • Bit 5: Stationary activity detected
            • Bit 6: Walking activity detected
            • Bit 7: Unknown activity detected
        """
        with open(file_path, "rb") as file:
            # Read the binary data from
            try:
                header_info = self._read_header(file)
                if header_info["sensor_id"] != 13:
                    print(
                        f"Invalid sensor ID for activity data: {header_info['sensor_id']}"
                    )
                    return

                # Use Pandas to read the binary data
                # Create a structured array to hold the data
                dtype = np.dtype(
                    [
                        ("time", "uint64"),
                        ("detected_activities", "uint8"),
                    ]
                )
                data = np.fromfile(file, dtype=dtype)
                # Convert the structured array to a DataFrame
                df = pd.DataFrame(data)
                # Convert time to datetime
                df["time"] = pd.to_datetime(df["time"], unit="ms")
                # Set the time as the index
                df.set_index("time", inplace=True)
                # Extract activity information and confidence level
                # Set activity columns based on the detected_activities bitmask as boolean columns
                df["confidence_level"] = df["detected_activities"] & 0b00000011
                df["automotive_activity"] = (df["detected_activities"] & 0b00000100) > 0
                df["cycling_activity"] = (df["detected_activities"] & 0b00001000) > 0
                df["running_activity"] = (df["detected_activities"] & 0b00010000) > 0
                df["stationary_activity"] = (df["detected_activities"] & 0b00100000) > 0
                df["walking_activity"] = (df["detected_activities"] & 0b01000000) > 0
                df["unknown_activity"] = (df["detected_activities"] & 0b10000000) > 0
                # Drop the original detected_activities column
                df.drop(columns=["detected_activities"], inplace=True)

            except Exception as e:
                print(f"Error reading header from {file_path}: {e}")
                return

    def _import_battery_data(self, file_path: str, bucket: str):
        """
        Import battery data from the specified file path.

        • time: UInt64–8bytes: time (Unix format) with milliseconds precision
        • Battery level: UInt8 – 1 byte: Battery level in percentage (between 0 and 100, 0 is invalid / unknown state)
        • Battery state: UInt8 – 1 byte: Battery state
            – 0: Unknown
            – 1: Unplugged
            – 2: Charging
            – 3: Full
        """
        with open(file_path, "rb") as file:
            # Read the binary data from
            try:
                header_info = self._read_header(file)
                if header_info["sensor_id"] != 1:
                    print(
                        f"Invalid sensor ID for battery data: {header_info['sensor_id']}"
                    )
                    return

                check_interval = header_info.get("settings", {}).get(
                    "check_interval", 1
                )

                # Use Pandas to read the binary data
                # Create a structured array to hold the data
                dtype = np.dtype(
                    [
                        ("time", "uint64"),
                        ("battery_level", "uint8"),
                        ("battery_state", "uint8"),
                    ]
                )
                data = np.fromfile(file, dtype=dtype)
                # Convert the structured array to a DataFrame
                df = pd.DataFrame(data)
                # Convert time to datetime
                df["time"] = pd.to_datetime(df["time"], unit="ms")
                # Set the time as the index
                df.set_index("time", inplace=True)
                pass

            except Exception as e:
                print(f"Error reading header from {file_path}: {e}")
                return

    def _import_beacons_data(self, file_path: str, bucket: str):
        """
        Import beacons data from the specified file path.
        """
        pass

    def _import_calorie_data(self, file_path: str, bucket: str):
        """
        Import calorie data from the specified file path.
        """
        pass

    def _import_coordinates_data(self, file_path: str, bucket: str):
        """
        Import coordinates data from the specified file path.
        """
        pass

    def _import_dyskinetic_symptoms_data(self, file_path: str, bucket: str):
        """
        Import dyskinetic symptoms data from the specified file path.
        """
        pass

    def _import_gps_data(self, file_path: str, bucket: str):
        """
        Import GPS data from the specified file path.
        """
        pass

    def _import_gyroscope_data(self, file_path: str, bucket: str):
        """
        Import gyroscope data from the specified file path.
        """
        pass

    def _import_headings_data(self, file_path: str, bucket: str):
        """
        Import headings data from the specified file path.
        """
        pass

    def _import_heart_rate_data(self, file_path: str, bucket: str):
        """
        Import heart rate data from the specified file path.
        """
        pass

    def _import_magnetometer_data(self, file_path: str, bucket: str):
        """
        Import magnetometer data from the specified file path.
        """
        pass

    def _import_pedometer_data(self, file_path: str, bucket: str):
        """
        Import pedometer data from the specified file path.
        """
        pass

    def _import_tremor_data(self, file_path: str, bucket: str):
        """
        Import tremor data from the specified file path.
        """
        pass

    def _import_healthkit_data(self, file_path: str, bucket: str):
        """
        Import HealthKit data from the specified file path.
        """
        pass

    def _import_raw_accelerometer_data(self, file_path: str, bucket: str):
        """
        Binary file format for Raw Accelerometer data:
        time: UInt64 – 8 bytes: time (Unix format) with milliseconds precision
        Accelerometer x-data: Float32 – 4 bytes: Accelerometer data for x-axis (g)
        Accelerometer y-data: Float32 – 4 bytes: Accelerometer data for y-axis (g)
        Accelerometer z-data: Float32 – 4 bytes: Accelerometer data for z-axis (g)
        """
        with open(file_path, "rb") as file:
            # Read the binary data from
            try:
                header_info = self._read_header(file)

                if header_info["sensor_id"] != 9:
                    print(
                        f"Invalid sensor ID for raw accelerometer data: {header_info['sensor_id']}"
                    )
                    return

                frequency = header_info.get("settings", {}).get("frequency", 50)

                # Use Pandas to read the binary data
                # Create a structured array to hold the data
                dtype = np.dtype(
                    [
                        ("time", "uint64"),
                        ("x_acc", "float32"),
                        ("y_acc", "float32"),
                        ("z_acc", "float32"),
                    ]
                )
                data = np.fromfile(file, dtype=dtype)
                # Convert the structured array to a DataFrame
                df = pd.DataFrame(data)

                # Add metadata to the DataFrame
                df["frequency"] = frequency
                df["source"] = "Apple Watch"

                # Convert time to datetime
                df["time"] = pd.to_datetime(df["time"], unit="ms")
                # Set the time as the index
                df.set_index("time", inplace=True)

                # Write the DataFrame to the specified bucket
                self.write_data_frame(
                    bucket, "RawAccelerometer", df, tag_columns=["source", "frequency"]
                )

            except Exception as e:
                print(f"Error reading header from {file_path}: {e}")
                return

    def _read_header(self, file) -> dict:
        expected_header_id = 0xEAEA
        header = {}
        [file_header_id, version, participant_id, sensor_id] = struct.unpack(
            "<HBIB", file.read(8)
        )
        header["file_header_id"] = file_header_id

        if file_header_id != expected_header_id:
            raise ValueError(
                f"Invalid file header ID: {file_header_id} expected {expected_header_id}"
            )

        header["version"] = version
        header["participant_id"] = participant_id
        header["sensor_id"] = sensor_id

        if version >= 2:
            [json_data_size] = struct.unpack("<I", file.read(4))
            [json_data] = struct.unpack(
                "<{}s".format(json_data_size), file.read(json_data_size)
            )
            settings_json_str = json_data.decode("utf-8")

            # Sort settings values
            settings_json = json.loads(settings_json_str)
            settings_json = dict(sorted(settings_json.items()))
            header["settings"] = settings_json

            # Get end header tag
            [end_header_id] = struct.unpack("<H", file.read(2))
            if end_header_id != expected_header_id:
                raise ValueError(
                    f"Invalid end header ID: {end_header_id} expected {expected_header_id}"
                )

        return header


if __name__ == "__main__":
    from libactimetry.db.InfluxDBDataClient import InfluxDBDataClient

    # url = "http://influxdb:8086"
    # token = "my-super-token"
    # org = "my-org"
    # bucket = "my-bucket"

    # client = InfluxDBDataClient(
    #    host="influxdb", port=8086, token="my-super-token", org="my-org"
    # )
    """
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=timescaledb
    """

    client = TimescaleDBDataClient(
        host="timescaledb",
        port=5432,
        user="postgres",
        password="postgres",
        database="timescaledb",
    )

    buckets: list[str] = client.available_bucket_names()
    print("Available buckets:", buckets)

    # Example usage
    importer = AppleWatchImporter(
        data_directory="/actimetry-service/tools/influxdb/data/2025-06-09_11-54-11-0",
        db_client=client,
        bucket_name="my_bucket2",
    )

    importer.delete_data("my_bucket2")
    importer.import_data("my_bucket2")
    print("Data import completed.")
