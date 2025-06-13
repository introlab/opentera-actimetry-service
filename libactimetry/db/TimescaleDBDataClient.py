from sqlalchemy import create_engine, text
import pandas as pd
from tools.timeit import timeit_class
import io


@timeit_class
class TimescaleDBDataClient:
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        """
        Initialize the TimescaleDB client.
        """
        self.engine = create_engine(
            f"postgresql://{user}:{password}@{host}:{port}/{database}"
        )

    # For compatiblity with BaseImporter interface
    def available_bucket_names(self) -> list[str]:
        return self.available_tables()

    # For compatibility with BaseImporter interface
    def delete_bucket(self, bucket_name: str) -> bool:
        return self.delete_table(bucket_name)

    def create_bucket(self, bucket_name: str, retention_policy: str = None) -> bool:
        """
        Create a new bucket (hypertable) in TimescaleDB.
        """
        return self.create_table(bucket_name, retention_policy)

    def available_tables(self) -> list[str]:
        """
        Retrieve a list of tables in the public schema.
        """
        query = "SELECT tablename FROM pg_tables WHERE schemaname = 'public';"
        with self.engine.connect() as con:
            result = con.execute(text(query))
            tables = [row[0] for row in result.fetchall()]
        return tables

    def create_hypertable_from_dataframe(
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
            # Delete database
            self.delete_table(table_name)

        # Prepare the DataFrame: make sure the time index is a proper column
        if data.index.name != "time":
            data = data.copy()
            data.index.name = "time"
        data.reset_index(inplace=True)

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

    def create_table(self, table_name: str, retention_policy: str = None) -> bool:
        return True

    def delete_table(self, table_name: str) -> bool:
        """
        Delete a specified table from TimescaleDB.
        """
        if table_name not in self.available_tables():
            print(f"Table '{table_name}' does not exist.")
            return False

        with self.engine.connect() as con:
            try:
                delete_stmt = f"""DROP TABLE "{table_name}";"""
                con.execute(text(delete_stmt))
                con.commit()
                print(f"Table '{table_name}' deleted successfully.")
            except Exception as e:
                print(f"Error deleting table '{table_name}': {e}")
        return True

    # For compatibility with BaseImporter interface
    def write_data(
        self,
        bucket_name: str,
        measurement_name: str,
        data: pd.DataFrame,
        tag_columns: list[str] = None,
    ) -> bool:
        """
        Write data from a pandas DataFrame to the specified hypertable.
        The DataFrame is expected to have a datetime index (which will be reset to a column "time")
        and columns for frequency, source, and any additional data. Additional data is stored in the
        'data' column using JSONB; adapt as needed.
        """
        # if bucket_name not in self.available_tables():
        #    raise ValueError(f"Table '{bucket_name}' does not exist.")

        table_name = bucket_name + "_" + measurement_name
        try:
            return self.create_hypertable_from_dataframe(table_name, data, None)
        except Exception as e:
            print(f"Error writing data to table '{table_name}': {e}")
            return False

    def query_data(self, bucket_name: str, measurement_name: str) -> pd.DataFrame:
        """
        Query data from a specified hypertable in TimescaleDB.
        """
        table_name = bucket_name + "_" + measurement_name
        if table_name not in self.available_tables():
            raise ValueError(f"Table '{table_name}' does not exist.")
        query = f"""SELECT * FROM "{table_name}";"""
        df = pd.read_sql(query, self.engine)
        return df

    def close(self):
        """
        Close the TimescaleDB client connection.
        """
        self.engine.dispose()
        print("TimescaleDB client connection closed.")
