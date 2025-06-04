from BaseModel import BaseModel
from sqlalchemy import Column, Integer, String, ForeignKey
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
