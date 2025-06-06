from BaseModel import BaseModel
from sqlalchemy import Column, Integer, String, ForeignKey, Sequence, TIMESTAMP, func, JSON
from sqlalchemy.orm import relationship


class ActimetryResults(BaseModel):
    """
    ActimetryResults model representing the results of an actimetry analysis in the Actimetry system.

    This needs to be related to a database

    We need to store the date of the results

    We need to store the processing time

    TODO :

    """

    __tablename__ = "t_actimetry_results"
    id_result = Column(Integer, Sequence('id_algorithm_results'), primary_key=True, autoincrement=True)
    id_algorithm = Column(Integer, ForeignKey('t_actimetry_algorithms.id_algorithm', ondelete='cascade'),
                           nullable=False)
    result_datetime = Column(TIMESTAMP, nullable=False, default=func.now())
    result_summary = Column(JSON, nullable=True)
    result_name = Column(String, nullable=True)  # Contains filename to use or database name or anything required to access data