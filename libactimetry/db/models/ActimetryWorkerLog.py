import datetime

from libactimetry.db.models.BaseModel import BaseModel
from sqlalchemy import Column, Integer, String, Sequence, SmallInteger, TIMESTAMP, func, ForeignKey
from sqlalchemy.orm import relationship
from enum import Enum


class WorkerStatus(Enum):
    STATUS_READY = 0
    STATUS_PLANNED = 1
    STATUS_RUNNING = 2
    STATUS_COMPLETED = 3
    STATUS_ABORTED = 4

class WorkerType(Enum):
    TYPE_GENERAL = 0
    TYPE_ALGORITHM = 1
    TYPE_IMPORTER = 2
    TYPE_EXPORTER = 3

class WorkerOwnerType(Enum):
    OWNER_USER = 0
    OWNER_PARTICIPANT = 1
    OWNER_DEVICE = 2
    OWNER_SERVICE = 3


class ActimetryWorkerLog(BaseModel):
    """
    ActimetryWorkerLog model representing a worker process, its status and its results.
    """
    __tablename__ = "t_actimetry_workers_logs"
    id_worker_log = Column(Integer, Sequence('id_actimetry_worker_log'), primary_key=True, autoincrement=True)
    worker_uuid = Column(String(36), nullable=False, unique=True)
    worker_owner_uuid = Column(String(36), nullable=False)
    worker_owner_type = Column(SmallInteger, nullable=False)
    id_database = Column(Integer, ForeignKey('t_actimetry_databases', ondelete='cascade'), nullable=True)
    worker_type = Column(SmallInteger, nullable=False)
    worker_start_time = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    worker_end_time = Column(TIMESTAMP(timezone=True), nullable=True)
    worker_update_time = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now(), onupdate=lambda:datetime.datetime.now())
    worker_status = Column(SmallInteger, nullable=False, default=WorkerStatus.STATUS_READY.value)
    worker_parameters = Column(String, nullable=False, default="")
    worker_results = Column(String, nullable=False, default="")
    worker_logs = Column(String, nullable=False, default="")
    worker_errors = Column(String, nullable=False, default="")

    worker_database = relationship('ActimetryDatabase')

    @staticmethod
    def get_log_for_worker(uuid_worker: str):
        return ActimetryWorkerLog.query.filter_by(worker_uuid=uuid_worker).first()

    @staticmethod
    def get_logs_for_participant(uuid_participant: str):
        return (ActimetryWorkerLog.query.join(ActimetryWorkerLog.worker_database).
                filter_by(database_participant_uuid=uuid_participant).all())

    @staticmethod
    def get_status_description(status: WorkerStatus) -> str:
        if status == WorkerStatus.STATUS_READY:
            return "Ready"
        if status == WorkerStatus.STATUS_ABORTED:
            return "Aborted"
        if status == WorkerStatus.STATUS_COMPLETED:
            return "Completed"
        if status == WorkerStatus.STATUS_PLANNED:
            return "Planned"
        if status == WorkerStatus.STATUS_RUNNING:
            return "Running"
        return 'Unknown Status'