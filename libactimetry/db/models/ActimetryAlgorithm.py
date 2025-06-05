from BaseModel import BaseModel
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship


class ActimetryAlgorithm(BaseModel):
    """
    ActimetryAlgorithm model representing an algorithm in the Actimetry system. This is related to the processing of raw data that is uploaded to the server.

    We need an algorithm name, a description and a version.
    We need to store the date of the algorithm creation and the date of the last modification.
    We need to store the author of the algorithm.

    TODO: Do we make a reference to a python script ?

    """

    __tablename__ = "t_actimetry_algorithm"
