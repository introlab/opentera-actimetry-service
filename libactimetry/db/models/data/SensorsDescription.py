from sqlalchemy import Table, Column, Integer, String, MetaData, text
from sqlalchemy.schema import CreateSchema
from sqlalchemy.orm import declarative_base, sessionmaker

"""
Create a table to store the description of sensors. This needs to be associated with a specific schema in the database.

"""

# Create a declarative base template with schame as a parameter
# This allows us to create models dynamically with a specific schema.
# This is useful for creating models that are not known at the time of writing the code.
Base = declarative_base()


def create_dynamic_table(metadata: MetaData):
    """
    Create a dynamic table with the specified metadata and table name.
    """
    return Table(
        "t_sensors_description",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("sensor_name", String(100), nullable=False),
    )


def create_dynamic_model(schema: str):
    """
    Create a dynamic model class for the sensors description table.
    """

    # class SensorsDescription(declarative_base(metadata=MetaData(schema=schema))):
    class SensorsDescription(Base):
        __tablename__ = "t_sensors_description"
        __tableargs__ = {"schema": schema}
        id = Column("id", Integer, primary_key=True, autoincrement=True)
        sensor_name = Column("sensor_name", String(100), nullable=False)

        def __repr__(self):
            return f"<SensorsDescription(id={self.id}, sensor_name={self.sensor_name})>"

    return SensorsDescription


# create main
if __name__ == "__main__":
    from sqlalchemy import create_engine

    user = "postgres"
    password = "postgres"
    host = "timescaledb"
    port = "5432"
    database = "timescaledb"

    engine = create_engine(f"postgresql://{user}:{password}@{host}:{port}/{database}")

    # Enable debugging on engine
    engine.echo = True

    # Example usage
    schema_name = "example_schema"
    SensorsDescriptionModel = create_dynamic_model(schema_name)

    # Create an instance of the model
    sensor_description = SensorsDescriptionModel(id=1, sensor_name="Accelerometer")

    # Create a session
    Session = sessionmaker(bind=engine)
    session = Session()

    with session.begin():
        try:
            # Create schema if it does not exist
            session.execute(CreateSchema(f"{schema_name}", if_not_exists=True))
            session.commit()
        except Exception as e:
            print(f"An error occurred: {e}")

    with session.begin():
        try:
            session.execute(text(f"ALTER SESSION SET CURRENT_SCHEMA={schema_name}"))

            # Create tables
            # SensorsDescriptionModel.metadata.create_all(engine)
            Base.create_all(engine)

            # Print the instance
            print(sensor_description)
        except Exception as e:
            print(f"An error occurred: {e}")
