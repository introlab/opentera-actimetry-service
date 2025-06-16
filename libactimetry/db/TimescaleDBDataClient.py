import uuid
from sqlalchemy import create_engine, text
import pandas as pd
from tools.timeit import timeit_class
import io

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import datetime
from sqlalchemy import event

Base = declarative_base()


class Bucket(Base):
    """
    Want to have a similar behavior as InfluxDB.
    Bucket which would be a table containing measurements with each measurement having
    a metadata column containing a JSON object with all the metadata and linking to an hypertable with all data.
    The hypertable is created from pandas DataFrame and will be dynamically created.
    """

    __tablename__ = "buckets"

    # Auto increment id
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.datetime.now(tz=datetime.timezone.utc),
        nullable=False,
    )

    description = Column(String, nullable=True)  # Optional description of the bucket

    # 36 character UUID for the bucket
    bucket_uuid = Column(
        String(36), nullable=False, unique=True, index=True
    )  # UUID for the bucket

    # Relationship to measurements
    measurements = relationship(
        "Measurement", back_populates="bucket", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Bucket(id={self.id}, name={self.name})>"


class Measurement(Base):
    __tablename__ = "measurements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bucket_id = Column(Integer, ForeignKey("buckets.id"), nullable=False)

    # Creation timestamp
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.datetime.now(tz=datetime.timezone.utc),
        nullable=False,
    )

    # Measurement name
    name = Column(String, nullable=False)

    # Metadata (TODO Use JSONB for better performance?)
    measurement_metadata = Column(JSON, nullable=True)

    hypertable_name = Column(
        String, nullable=False, unique=True
    )  # Name of the hypertable for this measurement

    # Relationship to parent bucket
    bucket = relationship("Bucket", back_populates="measurements")

    def __repr__(self):
        return f"<Measurement(bucket_id={self.bucket_id}, name={self.name}, metadata={self.metadata})>"


# Catch before_delete for Measurement to delete the hypertable
@event.listens_for(Measurement, "before_delete")
def before_delete_measurement(mapper, connection, target):
    """
    Before deleting a measurement, drop the associated hypertable.
    """
    hypertable_name = target.hypertable_name
    if hypertable_name:
        try:
            drop_stmt = f'DROP TABLE IF EXISTS "{hypertable_name}" CASCADE;'
            connection.execute(text(drop_stmt))
            print(f"Hypertable '{hypertable_name}' dropped successfully.")
        except Exception as e:
            print(f"Error dropping hypertable '{hypertable_name}': {e}")


@timeit_class
class TimescaleDBDataClient:
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        """
        Initialize the TimescaleDB client.
        """
        self.engine = create_engine(
            f"postgresql://{user}:{password}@{host}:{port}/{database}"
        )

        # Init sqlalchemy, creating tables if necessary
        # Create tables
        Base.metadata.create_all(self.engine)

        # Create session factory
        self.session_factory = sessionmaker(bind=self.engine)

    # For compatiblity with BaseImporter interface
    def available_bucket_names(self) -> list[str]:
        with self.engine.connect() as conn:
            # Use sqlachemy to query the buckets
            query = text("SELECT name FROM buckets;")
            result = conn.execute(query)
            buckets = [row[0] for row in result.fetchall()]
        return buckets

    def available_buckets(self) -> list[Bucket]:
        """
        Return the list of available buckets as Bucket objects.
        """
        session = self.session_factory()
        try:
            buckets = session.query(Bucket).all()
            # Detach objects from session to avoid session issues
            for bucket in buckets:
                session.expunge(bucket)  # Detach from session
            return buckets
        except Exception as e:
            print(f"Error retrieving buckets: {e}")
            return []
        finally:
            session.close()

    # For compatibility with BaseImporter interface
    def delete_bucket(self, bucket_name: str) -> bool:
        with self.engine.connect() as conn:
            try:
                # Create session
                session = self.session_factory()
                bucket = session.query(Bucket).filter_by(name=bucket_name).first()
                if not bucket:
                    print(f"Bucket '{bucket_name}' does not exist.")
                    return False

                # Delete the bucket and all its measurements
                session.delete(bucket)
                session.commit()
            except Exception as e:
                print(f"Error deleting bucket '{bucket_name}': {e}")
                return False
        print(f"Bucket '{bucket_name}' deleted successfully.")
        return True

    def create_bucket(
        self, bucket_name: str, retention_policy: str = None
    ) -> Bucket | None:
        """
        Create a new bucket in TimescaleDB.
        A bucket is a table that contains measurements.
        The bucket will have a unique UUID and a name.
        The bucket will be created in the public schema.
        """
        session = self.session_factory()
        try:
            bucket = Bucket()
            bucket.name = bucket_name
            # TODO uuid should be the session uuid
            bucket.bucket_uuid = uuid.uuid4()
            session.add(bucket)
            session.commit()
            bucket_id = bucket.id

        except Exception as e:
            print(f"Error creating bucket '{bucket_name}': {e}")
            return None
        finally:
            session.close()

        # Get object back
        new_session = self.session_factory()
        try:
            bucket = new_session.query(Bucket).get(bucket_id)
            new_session.expunge(bucket)  # Detach from session
            return bucket
        except Exception as e:
            print(f"Error retrieving bucket '{bucket_name}': {e}")
            return None
        finally:
            new_session.close()

    def get_available_buckets(self) -> list[str]:
        """
        Return the list of buckets
        """
        with self.engine.connect() as conn:
            # Use sqlachemy to query the buckets
            query = text("SELECT name FROM buckets;")
            result = conn.execute(query)
            buckets = [row[0] for row in result.fetchall()]
        return buckets

    def create_measurement(
        self, bucket_name: str, measurement_name: str, measurement_metadata: dict = None
    ) -> Measurement | None:
        """
        Create a new measurement in the specified bucket.
        This will create a new hypertable for the measurement.
        """
        # Create session
        session = self.session_factory()
        try:
            bucket = session.query(Bucket).filter_by(name=bucket_name).first()
            if not bucket:
                print(f"Bucket '{bucket_name}' does not exist.")
                return None

            measurement = Measurement(
                name=measurement_name,
                bucket=bucket,
                hypertable_name=f"{bucket_name}_{measurement_name}",
                measurement_metadata=measurement_metadata or {},
            )
            session.add(measurement)
            session.commit()
            measurement_id = measurement.id

        except Exception as e:
            session.rollback()
            print(f"Error creating measurement: {e}")
            return None
        finally:
            session.close()

        # Get object back
        new_session = self.session_factory()
        try:
            measurement = new_session.query(Measurement).get(measurement_id)
            new_session.expunge(measurement)  # Detach from session
            return measurement
        finally:
            new_session.close()

    def available_tables(self) -> list[str]:
        """
        Retrieve a list of tables in the public schema.
        """
        query = "SELECT tablename FROM pg_tables WHERE schemaname = 'public';"
        with self.engine.connect() as con:
            result = con.execute(text(query))
            tables = [row[0] for row in result.fetchall()]
        return tables

    def _get_measurement_from_bucket(
        self, bucket_name: str, measurement_name: str
    ) -> Measurement | None:
        """
        Get a measurement from a bucket by name.
        This is a helper method to retrieve the measurement object.
        """
        session = self.session_factory()
        try:
            bucket = session.query(Bucket).filter_by(name=bucket_name).first()
            if not bucket:
                print(f"Bucket '{bucket_name}' does not exist.")
                return None

            measurement = (
                session.query(Measurement)
                .filter_by(name=measurement_name, bucket_id=bucket.id)
                .first()
            )
            # Detach the measurement from the session to avoid session issues
            if measurement:
                session.expunge(measurement)  # Detach from session
            else:
                print(
                    f"Measurement '{measurement_name}' does not exist in bucket '{bucket_name}'."
                )
            return measurement
        except Exception as e:
            print(f"Error retrieving measurement: {e}")
            return None
        finally:
            session.close()

    def _create_hypertable_from_dataframe(
        self,
        table_name: str,
        data: pd.DataFrame,
        retention_policy: str = None,
    ) -> bool:
        """
        Create a hypertable in TimescaleDB from a pandas DataFrame.
        The DataFrame is expected to have a datetime index (which will be reset to a column "time")
        Columns can contain any additional data, which will be stored separately in columns depending on their types.
        """
        if table_name in self.available_tables():
            print(f"Table '{table_name}' already exists.")
            return False

        if "time" not in data.columns:
            raise ValueError("DataFrame must contain a 'time' column.")

        # Step 1: Map Pandas dtypes to PostgreSQL types
        def map_dtype(dtype):
            if pd.api.types.is_datetime64_any_dtype(dtype):
                return "TIMESTAMP"
            elif pd.api.types.is_integer_dtype(dtype):
                return "INTEGER"
            elif pd.api.types.is_float_dtype(dtype):
                return "DOUBLE PRECISION"
            elif pd.api.types.is_bool_dtype(dtype):
                return "BOOLEAN"
            else:
                return "TEXT"

        columns = []
        for col in data.columns:
            col_type = map_dtype(data[col].dtype)
            if col == "time":
                col_type = "TIMESTAMPTZ NOT NULL"
            columns.append(f"{col} {col_type}")

        columns_sql = ", ".join(columns)

        with self.engine.connect() as con:
            # Step 2: Create the table
            create_stmt = f"""
            CREATE TABLE "{table_name}"(
                {columns_sql}
            );
            """
            con.execute(text(create_stmt))
            con.commit()

            try:
                hypertable_stmt = (
                    f"""SELECT create_hypertable('"{table_name}"', 'time');"""
                )
                con.execute(text(hypertable_stmt))
                print(f"Table '{table_name}' created successfully as a hypertable.")

                # Step 3: Set retention policy if specified
                if retention_policy:
                    policy_stmt = f"""
                    SELECT add_retention_policy('"{table_name}"', INTERVAL '{retention_policy}');
                    """
                    con.execute(text(policy_stmt))
                    print(
                        f"Retention policy of {retention_policy} set on table '{table_name}'."
                    )

                con.commit()
            except Exception as e:
                print(f"Error creating hypertable '{table_name}': {e}")
                con.rollback()
                return False
        # Step 4: Insert data into the hypertable
        # data.to_sql(
        #     table_name,
        #     con=self.engine,
        #     if_exists="append",
        #     index=False,
        #     method="multi",
        #     chunksize=1000,
        # )

        csv_buffer = io.StringIO()
        # For more precision use float_format='%.6f' or similar
        data.to_csv(csv_buffer, index=False, header=False)
        csv_buffer.seek(0)

        cols = ", ".join(data.columns)
        copy_sql = f"""COPY "{table_name}" ({cols}) FROM STDIN WITH (FORMAT CSV);"""
        # Utiliser une connexion brute pour exécuter COPY
        with self.engine.connect() as conn:
            raw_conn = conn.connection
            cursor = raw_conn.cursor()
            cursor.copy_expert(copy_sql, csv_buffer)
            raw_conn.commit()

        return True

    # def delete_table(self, table_name: str) -> bool:
    #     """
    #     Delete a specified table from TimescaleDB.
    #     """
    #     if table_name not in self.available_tables():
    #         print(f"Table '{table_name}' does not exist.")
    #         return False

    #     with self.engine.connect() as con:
    #         try:
    #             delete_stmt = f"""DROP TABLE "{table_name}";"""
    #             con.execute(text(delete_stmt))
    #             con.commit()
    #             print(f"Table '{table_name}' deleted successfully.")
    #         except Exception as e:
    #             print(f"Error deleting table '{table_name}': {e}")
    #     return True

    # For compatibility with BaseImporter interface
    def write_data(
        self,
        bucket_name: str,
        measurement_name: str,
        data: pd.DataFrame,
        metadata: dict = None,
    ) -> bool:
        """
        Write data from a pandas DataFrame to the specified hypertable.
        The DataFrame is expected to have a datetime index (which will be reset to a column "time")
        and columns for frequency, source, and any additional data. Additional data is stored in the
        'data' column using JSONB; adapt as needed.
        """

        if not isinstance(data, pd.DataFrame):
            raise ValueError("Data must be a pandas DataFrame.")

        # Ensure the DataFrame has a 'time' column
        if "time" not in data.columns and data.index.name != "time":
            raise ValueError("DataFrame must contain a 'time' column.")
        if data.index.name != "time":
            data = data.copy()
            data.index.name = "time"
        data.reset_index(inplace=True)

        # Ensure the bucket exists
        if bucket_name not in self.get_available_buckets():
            # Creat the bucket if it does not exist
            if not self.create_bucket(bucket_name):
                print(f"Failed to create bucket '{bucket_name}'.")
                return False

        # Create the measurement
        measurement = self.create_measurement(
            bucket_name, measurement_name, measurement_metadata=metadata
        )
        if not measurement:
            print(
                f"Failed to create measurement '{measurement_name}' in bucket '{bucket_name}'."
            )
            return False

        try:
            return self._create_hypertable_from_dataframe(
                measurement.hypertable_name, data, None
            )
        except Exception as e:
            print(f"Error writing data to table '{measurement.hypertable_name}': {e}")
            return False

    def query_data(self, bucket_name: str, measurement_name: str) -> pd.DataFrame:
        """
        Query data from a specified hypertable in TimescaleDB.
        """

        # Get measurement
        measurement = self._get_measurement_from_bucket(bucket_name, measurement_name)

        if not measurement:
            raise ValueError(
                f"Measurement '{measurement_name}' does not exist in bucket '{bucket_name}'."
            )

        table_name = measurement.hypertable_name
        if table_name not in self.available_tables():
            raise ValueError(f"Table '{table_name}' does not exist.")
        query = f"""SELECT * FROM "{table_name}";"""
        df = pd.read_sql(query, self.engine)
        print(f"Query executed successfully: {df.shape[0]} records retrieved.")
        return df

    def close(self):
        """
        Close the TimescaleDB client connection.
        """
        self.engine.dispose()
        print("TimescaleDB client connection closed.")


if __name__ == "__main__":
    # Example usage
    client = TimescaleDBDataClient(
        host="timescaledb",
        port=5432,
        user="postgres",
        password="postgres",
        database="timescaledb",
    )

    # Create a bucket
    bucket_name = "test_" + str(uuid.uuid4())
    client.create_bucket(bucket_name)

    # Get available buckets
    buckets = client.get_available_buckets()

    print("Available buckets:", buckets)

    # Create a measurement
    measurement_name = "measurement_" + str(uuid.uuid4())
    measurement = client.create_measurement(bucket_name, measurement_name)
    # print(f"Measurement '{measurement_name}' created in bucket '{bucket_name}'.")

    # # Create a measurement
    # data = pd.DataFrame(
    #     {
    #         "time": pd.date_range(start="2023-01-01", periods=10, freq="D"),
    #         "value": range(10),
    #     }
    # )
    # client.create_hypertable_from_dataframe("test_bucket_measurement", data)

    # # Query the data
    # queried_data = client.query_data(bucket_name, "measurement")
    # print(queried_data)

    # # Close the client
    # client.close()
