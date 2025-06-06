from BaseModel import BaseModel
from sqlalchemy import Column, Integer, String, ForeignKey, Sequence, TIMESTAMP, func, exc, JSON
from sqlalchemy.orm import relationship

from enum import Enum

# TODO: Enumerate types depending on what we support
class ActimetryDatabaseType(Enum):
    DATABASETYPE_TIMESERIES = 0


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

    __tablename__ = "t_actimetry_databases"
    id_database = Column(Integer, Sequence('id_database_sequence'), primary_key=True, autoincrement=True)
    id_collection = Column(Integer, ForeignKey('t_actimetry_assets.id_collection', ondelete='cascade'),
                           nullable=False)
    database_uuid = Column(String(36), nullable=False, unique=True)
    database_name = Column(String, nullable=False)
    database_type = Column(Integer, nullable=False, default=ActimetryDatabaseType.DATABASETYPE_TIMESERIES)
    database_parameters = Column(JSON, nullble=True)  # Specific database parameter, such as connection settings
    database_datetime = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    database_expiration_datetime = Column(TIMESTAMP(timezone=True), nullable=True)

    # Delete this database. file_folder might be required to delete the file too.
    def delete_actimetry_database(self, file_folder: str | None) -> bool:
        # Delete related file from system
        # TODO: Handle specific database type
        # file_name = os.path.join(file_folder, self.asset_uuid)
        # if os.path.exists(file_name):
        #     # print('ActimetryAsset: Deleted ' + file_name)
        #     os.remove(file_name)
        # else:
        #     # print('ActimetryAsset: File not found: ' + file_name)
        #     return False

        # Delete self from database
        try:
            self.db().session.delete(self)
            self.commit()
        except exc.SQLAlchemyError:
            return False

        return True