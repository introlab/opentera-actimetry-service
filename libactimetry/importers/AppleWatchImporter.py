import pandas as pd
import json
import struct
import numpy as np


class AppleWatchImporter:
    def __init__(self, data_directory):
        self.data_directory = data_directory

    def import_data(self):
        # Implement data import logic here
        # First, verify that the session.oimi JSON file exists
        session_file = f"{self.data_directory}/session.oimi"
        try:
            with open(session_file, "r") as file:
                # Load the session data from the JSON file
                session_info = json.load(file)

                for file_name in session_info.get("files", []):
                    file_path = f"{self.data_directory}/{file_name}"

                    # Reate HealthKit.data
                    if file_name == "watch_HealthKit.data":
                        self._import_healthkit_data(file_path)
                    elif file_name == "watch_RawAccelerometer.data":
                        self._import_raw_accelerometer_data(file_path)

                print(f"Session data loaded from {session_file}")
        except FileNotFoundError:
            print(f"Error: Session file {session_file} not found.")
            return
        except Exception as e:
            print(f"Error reading session file {session_file}: {e}")
            return

    def _import_healthkit_data(self, file_path):
        pass

    def _import_raw_accelerometer_data(self, file_path):
        """
        Binary file format for Raw Accelerometer data:
        Timestamp: UInt64 – 8 bytes: Timestamp (Unix format) with milliseconds precision
        Accelerometer x-data: Float32 – 4 bytes: Accelerometer data for x-axis (g)
        Accelerometer y-data: Float32 – 4 bytes: Accelerometer data for y-axis (g)
        Accelerometer z-data: Float32 – 4 bytes: Accelerometer data for z-axis (g)
        """
        with open(file_path, "rb") as file:
            # Read the binary data from
            try:
                header_info = self._read_header(file)

                frequency = header_info.get("settings", {}).get("frequency", 50)

                # Use Pandas to read the binary data
                # Create a structured array to hold the data
                dtype = np.dtype(
                    [
                        ("timestamp", "uint64"),
                        ("x", "float32"),
                        ("y", "float32"),
                        ("z", "float32"),
                    ]
                )
                data = np.fromfile(file, dtype=dtype)
                # Convert the structured array to a DataFrame
                df = pd.DataFrame(data)
                # Convert timestamp to datetime
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                # Set the timestamp as the index
                df.set_index("timestamp", inplace=True)

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
    # Example usage
    importer = AppleWatchImporter(
        data_directory="/actimetry-service/tools/influxdb/data/2025-06-09_11-54-11-0"
    )
    importer.import_data()
    print("Data import completed.")
