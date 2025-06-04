from BaseModel import BaseModel
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship


class ActimetryDatabase(BaseModel):
    """
    ActimetryDatabase model representing the database for the Actimetry system.
    This is related to the storage and management of all data assets from a collection.
    The database is a sqlite database that will be stored on the server.
    We need to store the database name, a description, and a date of creation.

    Algorithms will need to process data from the database.

    Should we use OpenIMU format for the database ?
    We could also have a timeseries database like InfluxDB or TimescaleDB for the data.
    Another option would be to use a mcap file format for the database, which is a binary format that is optimized for time series data.
    """

    __tablename__ = "t_actimetry_database"
