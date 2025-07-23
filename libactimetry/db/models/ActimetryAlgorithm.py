from libactimetry.db.models.BaseModel import BaseModel
from sqlalchemy import Column, Integer, String, Sequence, TIMESTAMP, func, SmallInteger, JSON
from sqlalchemy.orm import relationship

from enum import Enum

class ActimetryAlgorithmType(Enum):
    ALGORITHMTYPE_PYTHON = 0
    ALGORITHMTYPE_EXE =1


class ActimetryAlgorithm(BaseModel):
    """
    ActimetryAlgorithm model representing an algorithm in the Actimetry system. This is related to the processing of raw data that is uploaded to the server.

    We need an algorithm name, a description and a version.
    We need to store the date of the algorithm creation and the date of the last modification.
    We need to store the author of the algorithm.

    TODO: Do we make a reference to a python script ?

    """

    __tablename__ = "t_actimetry_algorithms"
    id_algorithm = Column(Integer, Sequence('id_algorithm_sequence'), primary_key=True, autoincrement=True)
    algorithm_name = Column(String, nullable=False)
    algorithm_description = Column(String, nullable=True)
    algorithm_author = Column(String, nullable=True)
    algorithm_version = Column(String, nullable=False, default="1.0.0")
    algorithm_creation = Column(TIMESTAMP, nullable=False, default=func.now())
    algorithm_last_update = Column(TIMESTAMP, nullable=False, default=func.now())
    algorithm_type = Column(SmallInteger, nullable=False, default=ActimetryAlgorithmType.ALGORITHMTYPE_PYTHON)
    algorithm_script = Column(String, nullable=False)  # Script to run to execute that algorithm
    algorithm_parameters_list = Column(JSON, nullable=True)  # JSON list of parameters that the algorithm can use
