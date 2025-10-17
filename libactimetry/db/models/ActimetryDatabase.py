import uuid
import os
import json
from datetime import datetime

from libactimetry.db.models.BaseModel import BaseModel


from sqlalchemy import (
    Column,
    Integer,
    String,
    Sequence,
    TIMESTAMP,
    func,
    exc,
    JSON,
)

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
    #id_session = Column(Integer, nullable=False)
    database_uuid = Column(String(36), nullable=False, unique=True)
    database_participant_uuid = Column(String(36), nullable=False)  # Participant to which the database is linked
    database_name = Column(String, nullable=False)
    database_type = Column(Integer, nullable=False, default=ActimetryDatabaseType.DATABASETYPE_OPENIMU.value)
    database_parameters = Column(
        JSON, nullable=True
    )  # Specific database parameter, such as connection settings, if needed
    database_creation_datetime = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    database_update_datetime = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    database_expiration_datetime = Column(TIMESTAMP(timezone=True), nullable=True)

    @staticmethod
    def get_for_participant(participant_uuid: str) -> "ActimetryDatabase | None":
        return ActimetryDatabase.query.filter_by(database_participant_uuid=participant_uuid).first()

    @staticmethod
    def get_by_uuid(database_uuid: str) -> "ActimetryDatabase | None":
        return ActimetryDatabase.query.filter_by(database_uuid=database_uuid).first()

    @staticmethod
    def get_by_id(id_database: int) -> "ActimetryDatabase | None":
        return ActimetryDatabase.query.filter_by(id_database=id_database).first()

    @staticmethod
    def create_openimu_database_file(filename: str, participant_info: dict):
        from libopenimu.db.DBManager import DBManager as OpenIMUDBManager
        from libopenimu.models.Participant import Participant as OpenIMUParticipant
        from libopenimu.models.DataSet import DataSet as OpenIMUDataSet
        manager: OpenIMUDBManager = OpenIMUDBManager(filename, overwrite=False, echo=False, newfile=True)
        # Create participant
        participant = OpenIMUParticipant()
        participant.name = participant_info["participant_name"]
        participant.description = json.dumps(participant_info)
        manager.session.add(participant)

        # Create dataset
        dataset = OpenIMUDataSet()
        dataset.name = "Main dataset"
        dataset.description = (
            f"Dataset for participant {participant.name} [{participant_info['participant_uuid']}]"
        )
        dataset.author = "Actimetry Service"
        dataset.creation_date = datetime.now()
        dataset.upload_date = datetime.now()
        manager.session.add(dataset)

        # Commit to DB
        manager.session.commit()
        manager.close()

    @classmethod
    def insert(cls, database: "ActimetryDatabase"):
        # Generate UUID
        database.database_uuid = str(uuid.uuid4())

        super().insert(database)

    # Delete this database. database_folder might be required to delete the file too.
    def delete_actimetry_database(self, database_folder: str | None) -> bool:
        # Delete related file from system
        file_name = os.path.join(database_folder, self.database_uuid)
        if os.path.exists(file_name):
            # print('ActimetryDatabase: Deleted ' + file_name)
            os.remove(file_name)
        else:
            # print('ActimetryDatabase: File not found: ' + file_name)
            return False

        # Delete self from database
        try:
            self.db().session.delete(self)
            self.commit()
        except exc.SQLAlchemyError:
            return False

        return True
