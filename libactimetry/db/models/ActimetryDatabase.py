from libactimetry.db.models.BaseModel import BaseModel
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Sequence,
    TIMESTAMP,
    func,
    exc,
    JSON,
)
from sqlalchemy.orm import relationship

from enum import Enum


# TODO: Enumerate types depending on what we support
class ActimetryDatabaseType(Enum):
    DATABASETYPE_TIMESERIES = 0
    DATABASETYPE_OPENIMU = 1


class ActimetryDatabase(BaseModel):
    """
    ActimetryDatabase model representing the database for the Actimetry system.
    This is related to the storage and management of all data assets from a collection.
    We need to store the database name, a description, and a date of creation.

    Algorithms will need to process data from the database.

    """

    __tablename__ = "t_actimetry_databases"
    id_database = Column(Integer, Sequence("id_database_sequence"), primary_key=True, autoincrement=True)
    id_session = Column(Integer, nullable=False)
    database_uuid = Column(String(36), nullable=False, unique=True)
    database_participant_uuid = Column(String(36), nullable=False)  # Participant to which the database is linked
    database_name = Column(String, nullable=False)
    database_type = Column(Integer, nullable=False, default=ActimetryDatabaseType.DATABASETYPE_OPENIMU)
    database_parameters = Column(
        JSON, nullable=True
    )  # Specific database parameter, such as connection settings, if needed
    database_creation_datetime = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    database_expiration_datetime = Column(TIMESTAMP(timezone=True), nullable=True)

    @staticmethod
    def get_for_participant(participant_uuid: str):
        return ActimetryDatabase.query.filter_by(database_participant_uuid=participant_uuid).first()

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
