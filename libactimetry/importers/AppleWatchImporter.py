import pandas as pd
import json
import struct
import numpy as np
import os
import uuid

from libactimetry.importers.BaseImporter import BaseImporter
from libactimetry.db.TimescaleDBDataClient import TimescaleDBDataClient


class AppleWatchImporter(BaseImporter):
    def __init__(
        self, data_directory: str, db_client: TimescaleDBDataClient, bucket_name: str
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
                        elif file_name == "watch_Gyroscope.data":
                            self._import_raw_gyrometer_data(
                                file_path, bucket=bucket_name
                            )
                        elif file_name == "watch_Headings.data":
                            self._import_headings_data(file_path, bucket=bucket_name)
                        elif file_name == "watch_HealthKit.data":
                            self._import_healthkit_data(file_path, bucket=bucket_name)
                        elif file_name == "watch_HeartRate.data":
                            self._import_heart_rate_data(file_path, bucket=bucket_name)
                        elif file_name == "watch_Magnetometer.data":
                            self._import_raw_magnetometer_data(
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

                # Extract activity information and confidence level
                # Set activity columns based on the detected_activities bitmask as boolean columns
                df["confidence_level"] = df["detected_activities"] & 0b00000011
                df["automotive_activity"] = (df["detected_activities"] & 0b00000100) > 0
                df["cycling_activity"] = (df["detected_activities"] & 0b00001000) > 0
                df["running_activity"] = (df["detected_activities"] & 0b00010000) > 0
                df["stationary_activity"] = (df["detected_activities"] & 0b00100000) > 0
                df["walking_activity"] = (df["detected_activities"] & 0b01000000) > 0
                df["unknown_activity"] = (df["detected_activities"] & 0b10000000) > 0
                # Drop the original detected_activities column ?
                df.drop(columns=["detected_activities"], inplace=True)

                # Write the DataFrame to the specified bucket
                self.write_data_frame(bucket, "Activity", df, metadata={})

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

                metadata = header_info.get("settings", {})

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

                # Write the DataFrame to the specified bucket
                self.write_data_frame(bucket, "Battery", df, metadata=metadata)

            except Exception as e:
                print(f"Error reading header from {file_path}: {e}")
                return

    def _import_beacons_data(self, file_path: str, bucket: str):
        """
        Import beacons data from the specified file path.
        • time: UInt64 8bytes: time (Unix format) with milliseconds precision
        • Beacon name : 4Bytes: 'XXXX' is for undefined beacons
        • RSSI: Int8 – 1 byte: Received Signal Strength Indicator (RSSI) in dBm
        """
        with open(file_path, "rb") as file:
            # Read the binary data from
            try:
                header_info = self._read_header(file)
                if header_info["sensor_id"] != 6:
                    print(
                        f"Invalid sensor ID for beacons data: {header_info['sensor_id']}"
                    )
                    return

                metadata = header_info.get("settings", {})

                # Use Pandas to read the binary data
                # Create a structured array to hold the data
                dtype = np.dtype(
                    [
                        ("time", "uint64"),
                        ("beacon_name", "S4"),
                        ("rssi", "int8"),
                    ]
                )
                data = np.fromfile(file, dtype=dtype)
                # Convert the structured array to a DataFrame
                df = pd.DataFrame(data)
                # Convert time to datetime
                df["time"] = pd.to_datetime(df["time"], unit="ms")

                # Write the DataFrame to the specified bucket
                self.write_data_frame(bucket, "Beacons", df, metadata=metadata)

            except Exception as e:
                print(f"Error reading header from {file_path}: {e}")
                return

    def _import_calorie_data(self, file_path: str, bucket: str):
        """
        Import calorie data from the specified file path.


        """
        pass

    def _import_coordinates_data(self, file_path: str, bucket: str):
        """
        Import coordinates data from the specified file path.
        • Timestamp: UInt64 – 8 bytes: Timestamp (Unix format) with milliseconds precision
        • Latitude: Float32 – 4 bytes: Latitude position
        • Longitude: Float32 – 4 bytes: Longitude position
        • Position accuracy: Float32 – 4 bytes: Accuracy (in meters) for lat/long
        • Altitude: Float32 – 4 bytes: Altitude (in meters) from sea level
        • Altitude accuracy: Float32 – 4 bytes: Accuracy (in meters) for altitude
        • Speed: Float32 – 4 bytes: Speed (meters per second)
        • Course: Float32 – 4 bytes: Degrees relative to true north
        """
        with open(file_path, "rb") as file:
            # Read the binary data from
            try:
                header_info = self._read_header(file)
                if header_info["sensor_id"] != 7:
                    print(
                        f"Invalid sensor ID for coordinates data: {header_info['sensor_id']}"
                    )
                    return

                metadata = header_info.get("settings", {})

                # Use Pandas to read the binary data
                # Create a structured array to hold the data
                dtype = np.dtype(
                    [
                        ("time", "uint64"),
                        ("latitude", "float32"),
                        ("longitude", "float32"),
                        ("position_accuracy", "float32"),
                        ("altitude", "float32"),
                        ("altitude_accuracy", "float32"),
                        ("speed", "float32"),
                        ("course", "float32"),
                    ]
                )
                data = np.fromfile(file, dtype=dtype)
                # Convert the structured array to a DataFrame
                df = pd.DataFrame(data)
                # Convert time to datetime
                df["time"] = pd.to_datetime(df["time"], unit="ms")

                # Write the DataFrame to the specified bucket
                self.write_data_frame(bucket, "Coordinates", df, metadata=metadata)

            except Exception as e:
                print(f"Error reading header from {file_path}: {e}")
                return

    def _import_dyskinetic_symptoms_data(self, file_path: str, bucket: str):
        """
        Import dyskinetic symptoms data from the specified file path. #19
        * Timestamp: UInt64 -- 8 bytes: Timestamp (Unix format) with milliseconds precision
        * Start Timestamp: Uint64 -- 8 bytes: Timestamp (Unix format) with milliseconds precision on which the measurement started
        * End Timestamp: Uint64 -- 8 bytes: Timestamp (Unix format) with milliseconds precision on which the measurement ended
        * Percent likely: Float32 -- 4 bytes: Percent likely that there is dyskinetic movements
        """
        with open(file_path, "rb") as file:
            # Read the binary data from
            try:
                header_info = self._read_header(file)
                if header_info["sensor_id"] != 19:
                    print(
                        f"Invalid sensor ID for dyskinetic symptoms data: {header_info['sensor_id']}"
                    )
                    return

                metadata = header_info.get("settings", {})

                # Use Pandas to read the binary data
                # Create a structured array to hold the data
                dtype = np.dtype(
                    [
                        ("time", "uint64"),
                        ("start_time", "uint64"),
                        ("end_time", "uint64"),
                        ("percent_likely", "float32"),
                    ]
                )
                data = np.fromfile(file, dtype=dtype)
                # Convert the structured array to a DataFrame
                df = pd.DataFrame(data)
                # Convert time to datetime
                df["time"] = pd.to_datetime(df["time"], unit="ms")
                df["start_time"] = pd.to_datetime(df["start_time"], unit="ms")
                df["end_time"] = pd.to_datetime(df["end_time"], unit="ms")

                # Write the DataFrame to the specified bucket
                self.write_data_frame(
                    bucket, "DyskineticSymptoms", df, metadata=metadata
                )

            except Exception as e:
                print(f"Error reading header from {file_path}: {e}")
                return

    def _import_raw_gyrometer_data(self, file_path: str, bucket: str):
        """
        Import raw gyrometer data from the specified file path. #10
        • Timestamp: UInt64 – 8 bytes: Timestamp (Unix format) with milliseconds precision
        • Gyroscope x-data: Float32 – 4 bytes: Gyroscope data for x-axis (deg/s)
        • Gyroscope y-data: Float32 – 4 bytes: Gyroscope data for y-axis (deg/s)
        • Gyroscope z-data: Float32 – 4 bytes: Gyroscope data for z-axis (deg/s)
        """
        with open(file_path, "rb") as file:
            # Read the binary data from
            try:
                header_info = self._read_header(file)
                if header_info["sensor_id"] != 10:
                    print(
                        f"Invalid sensor ID for raw gyrometer data: {header_info['sensor_id']}"
                    )
                    return

                metadata = header_info.get("settings", {})

                # Use Pandas to read the binary data
                # Create a structured array to hold the data
                dtype = np.dtype(
                    [
                        ("time", "uint64"),
                        ("x_gyro", "float32"),
                        ("y_gyro", "float32"),
                        ("z_gyro", "float32"),
                    ]
                )
                data = np.fromfile(file, dtype=dtype)
                # Convert the structured array to a DataFrame
                df = pd.DataFrame(data)
                # Convert time to datetime
                df["time"] = pd.to_datetime(df["time"], unit="ms")

                # Write the DataFrame to the specified bucket
                self.write_data_frame(bucket, "RawGyrometer", df, metadata=metadata)

            except Exception as e:
                print(f"Error reading header from {file_path}: {e}")
                return

    def _import_headings_data(self, file_path: str, bucket: str):
        """
        Import headings data from the specified file path. #16
        • Timestamp: UInt64 – 8 bytes: Timestamp (Unix format) with milliseconds precision
        • True Heading: Float32 – 4 bytes: Heading in degrees relative to true north (0 = North, 180 =
        South). Only valid if “True Heading Accuracy” is positive.
        • True Heading Accuracy: Float32 – 4 bytes: Accuracy in degrees of “True Heading”, with
        negative values representing unreliable or uncalibrated sensor.
        • Magnetic Heading: Float32 – 4 bytes: Heading in degrees relative to magnetic north.
        • Magnetometer x-data: Float32 – 4 bytes: x-value of magnetometer (microTeslas)
        • Magnetometer y-data: Float32 – 4 bytes: y-value of magnetometer (microTeslas)
        • Magnetometer z-data: Float32 – 4 bytes: z-value of magnetometer (microTeslas)
        """
        with open(file_path, "rb") as file:
            # Read the binary data from
            try:
                header_info = self._read_header(file)
                if header_info["sensor_id"] != 16:
                    print(
                        f"Invalid sensor ID for headings data: {header_info['sensor_id']}"
                    )
                    return

                metadata = header_info.get("settings", {})

                # Use Pandas to read the binary data
                # Create a structured array to hold the data
                dtype = np.dtype(
                    [
                        ("time", "uint64"),
                        ("true_heading", "float32"),
                        ("true_heading_accuracy", "float32"),
                        ("magnetic_heading", "float32"),
                        ("x_mag", "float32"),
                        ("y_mag", "float32"),
                        ("z_mag", "float32"),
                    ]
                )
                data = np.fromfile(file, dtype=dtype)
                # Convert the structured array to a DataFrame
                df = pd.DataFrame(data)
                # Convert time to datetime
                df["time"] = pd.to_datetime(df["time"], unit="ms")

                # Write the DataFrame to the specified bucket
                self.write_data_frame(bucket, "Headings", df, metadata=metadata)

            except Exception as e:
                print(f"Error reading header from {file_path}: {e}")
                return

    def _import_heart_rate_data(self, file_path: str, bucket: str):
        """
        Import heart rate data from the specified file path. #3
        • Timestamp: UInt64 – 8 bytes: Timestamp (Unix format) with milliseconds precision
        • Heart Rate: UInt8 – 1 byte: Heart rate in beats per minute (bpm)
        """
        with open(file_path, "rb") as file:
            # Read the binary data from
            try:
                header_info = self._read_header(file)
                if header_info["sensor_id"] != 3:
                    print(
                        f"Invalid sensor ID for heart rate data: {header_info['sensor_id']}"
                    )
                    return

                metadata = header_info.get("settings", {})

                # Use Pandas to read the binary data
                # Create a structured array to hold the data
                dtype = np.dtype(
                    [
                        ("time", "uint64"),
                        ("heart_rate", "uint8"),
                    ]
                )
                data = np.fromfile(file, dtype=dtype)
                # Convert the structured array to a DataFrame
                df = pd.DataFrame(data)
                # Convert time to datetime
                df["time"] = pd.to_datetime(df["time"], unit="ms")

                # Write the DataFrame to the specified bucket
                self.write_data_frame(bucket, "HeartRate", df, metadata=metadata)

            except Exception as e:
                print(f"Error reading header from {file_path}: {e}")
                return

    def _import_raw_magnetometer_data(self, file_path: str, bucket: str):
        """
        Import magnetometer data from the specified file path. #17
        • Timestamp: UInt64 – 8 bytes: Timestamp (Unix format) with milliseconds precision
        • Magnetometer x-data: Float32 – 4 bytes: x-value of magnetometer (microTeslas)
        • Magnetometer y-data: Float32 – 4 bytes: y-value of magnetometer (microTeslas)
        • Magnetometer z-data: Float32 – 4 bytes: z-value of magnetometer (microTeslas)
        """
        with open(file_path, "rb") as file:
            # Read the binary data from
            try:
                header_info = self._read_header(file)
                if header_info["sensor_id"] != 17:
                    print(
                        f"Invalid sensor ID for raw magnetometer data: {header_info['sensor_id']}"
                    )
                    return

                metadata = header_info.get("settings", {})

                # Use Pandas to read the binary data
                # Create a structured array to hold the data
                dtype = np.dtype(
                    [
                        ("time", "uint64"),
                        ("x_mag", "float32"),
                        ("y_mag", "float32"),
                        ("z_mag", "float32"),
                    ]
                )
                data = np.fromfile(file, dtype=dtype)
                # Convert the structured array to a DataFrame
                df = pd.DataFrame(data)
                # Convert time to datetime
                df["time"] = pd.to_datetime(df["time"], unit="ms")

                # Write the DataFrame to the specified bucket
                self.write_data_frame(bucket, "RawMagnetometer", df, metadata=metadata)

            except Exception as e:
                print(f"Error reading header from {file_path}: {e}")
                return

    def _import_pedometer_data(self, file_path: str, bucket: str):
        """
        Import pedometer data from the specified file path. 11

        • Timestamp: UInt64 – 8 bytes: Timestamp (Unix format) with milliseconds precision
        • Number of steps: UInt32 – 4 bytes: Current total step count from the start of the session
        • Distance: Float32 – 4 bytes: Current total estimated distance, in meters, from the start of the
        session. -1.0 if the value is not available on device
        • AverageActive Pace: Float32 – 4 bytes: Current average pace, in m/s, since the start of the session.
        -1.0 if the value is not available on device
        • Current Pace: Float32 – 4 bytes: Current estimated pace, in m/s. -1.0 if the value is not available
        on device
        • Current Cadence: Float32 – 4 bytes: Current cadence in steps per second. -1.0 if the value is not
        available on device
        • Floors Ascended: Int32 – 4 bytes: Total number of floor ascended since the start of the session.
        -1.0 if the value is not available on device
        • Floors Descended: Int32 – 4 bytes: Total number of floor descended since the start of the session.
        -1.0 if the value is not available on device
        """
        with open(file_path, "rb") as file:
            # Read the binary data from
            try:
                header_info = self._read_header(file)
                if header_info["sensor_id"] != 11:
                    print(
                        f"Invalid sensor ID for pedometer data: {header_info['sensor_id']}"
                    )
                    return

                metadata = header_info.get("settings", {})

                # Use Pandas to read the binary data
                # Create a structured array to hold the data
                dtype = np.dtype(
                    [
                        ("time", "uint64"),
                        ("steps", "uint32"),
                        ("distance", "float32"),
                        ("average_active_pace", "float32"),
                        ("current_pace", "float32"),
                        ("current_cadence", "float32"),
                        ("floors_ascended", "int32"),
                        ("floors_descended", "int32"),
                    ]
                )
                data = np.fromfile(file, dtype=dtype)
                # Convert the structured array to a DataFrame
                df = pd.DataFrame(data)
                # Convert time to datetime
                df["time"] = pd.to_datetime(df["time"], unit="ms")

                # Write the DataFrame to the specified bucket
                self.write_data_frame(bucket, "Pedometer", df, metadata=metadata)

            except Exception as e:
                print(f"Error reading header from {file_path}: {e}")
                return

    def _import_tremor_data(self, file_path: str, bucket: str):
        """
        Import tremor data from the specified file path.

        • Timestamp: UInt64 – 8 bytes: Timestamp (Unix format) with milliseconds precision
        • Start Timestamp: Uint64 – 8 bytes: Timestamp (Unix format) with milliseconds precision on
        which the measurement started
        • End Timestamp: Uint64 – 8 bytes: Timestamp (Unix format) with milliseconds precision on
        which the measurement ended
        • No Tremor Ratio: Float32 – 4 bytes: Ratio of time where no tremor where detected, between 0
        and 1
        • Slight Tremor Ratio: Float32 – 4 bytes: Ratio of time where slight tremors where detected,
        between 0 and 1
        • Mild Tremor Ratio: Float32 – 4 bytes: Ratio of time where mild tremors where detected, between
        0 and 1
        • Moderate Tremor Ratio: Float32 – 4 bytes: Ratio of time where moderate tremors where detected,
        between 0 and 1
        • Strong Tremor Ratio: Float32 – 4 bytes: Ratio of time where strong tremors where detected,
        between 0 and 1
        """
        with open(file_path, "rb") as file:
            # Read the binary data from
            try:
                header_info = self._read_header(file)
                if header_info["sensor_id"] != 18:
                    print(
                        f"Invalid sensor ID for tremor data: {header_info['sensor_id']}"
                    )
                    return

                metadata = header_info.get("settings", {})

                # Use Pandas to read the binary data
                # Create a structured array to hold the data
                dtype = np.dtype(
                    [
                        ("time", "uint64"),
                        ("start_time", "uint64"),
                        ("end_time", "uint64"),
                        ("no_tremor_ratio", "float32"),
                        ("slight_tremor_ratio", "float32"),
                        ("mild_tremor_ratio", "float32"),
                        ("moderate_tremor_ratio", "float32"),
                        ("strong_tremor_ratio", "float32"),
                    ]
                )
                data = np.fromfile(file, dtype=dtype)
                # Convert the structured array to a DataFrame
                df = pd.DataFrame(data)
                # Convert time to datetime
                df["time"] = pd.to_datetime(df["time"], unit="ms")
                df["start_time"] = pd.to_datetime(df["start_time"], unit="ms")
                df["end_time"] = pd.to_datetime(df["end_time"], unit="ms")

                # Write the DataFrame to the specified bucket
                self.write_data_frame(bucket, "Tremor", df, metadata=metadata)

            except Exception as e:
                print(f"Error reading header from {file_path}: {e}")
                return

    def _import_healthkit_data(self, file_path: str, bucket: str):
        """
        Import HealthKit data from the specified file path. #15
        • Timestamp: UInt64 – 8 bytes: Timestamp (Unix format) with milliseconds precision of the samples
        reception
        • Start Timestamp: UInt64 – 8 bytes: Sample start timestamp (Unix format) with milliseconds
        precision
        • End Timestamp: UInt64 – 8 bytes: Sample end timestamp (Unix format) with milliseconds precision
        • Type index: UInt16 – 2 byte: Index of the type of this sample in the list of types from the given
        settings list (see above)
        • Value: Float64 – 8 bytes: Value of the sample. Units are defined by the type of the sample (see
        above).
        """
        with open(file_path, "rb") as file:
            # Read the binary data from
            try:
                header_info = self._read_header(file)
                if header_info["sensor_id"] != 15:
                    print(
                        f"Invalid sensor ID for healthkit data: {header_info['sensor_id']}"
                    )
                    return

                metadata = header_info.get("settings", {})

                # Use Pandas to read the binary data
                # Create a structured array to hold the data
                dtype = np.dtype(
                    [
                        ("time", "uint64"),
                        ("start_time", "uint64"),
                        ("end_time", "uint64"),
                        ("type_index", "uint16"),
                        ("value", "float64"),
                    ]
                )
                data = np.fromfile(file, dtype=dtype)
                # Convert the structured array to a DataFrame
                df = pd.DataFrame(data)
                # Convert time to datetime
                df["time"] = pd.to_datetime(df["time"], unit="ms")
                df["start_time"] = pd.to_datetime(df["start_time"], unit="ms")
                df["end_time"] = pd.to_datetime(df["end_time"], unit="ms")

                # Write the DataFrame to the specified bucket
                self.write_data_frame(bucket, "HealthKit", df, metadata=metadata)

            except Exception as e:
                print(f"Error reading header from {file_path}: {e}")
                return

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

                metadata = header_info.get("settings", {})

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

                # Convert time to datetime
                df["time"] = pd.to_datetime(df["time"], unit="ms")

                # Write the DataFrame to the specified bucket
                self.write_data_frame(bucket, "RawAccelerometer", df, metadata=metadata)

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

    # Delete all buckets
    for bucket in buckets:
        print(f"Deleting bucket: {bucket}")
        client.delete_bucket(bucket)

    # Example usage
    importer = AppleWatchImporter(
        data_directory="/actimetry-service/tools/influxdb/data/2025-06-09_11-54-11-0",
        db_client=client,
        bucket_name="AWI_" + str(uuid.uuid4()),
    )

    importer.import_data(importer.bucket_name)
    print("Data import completed.")
