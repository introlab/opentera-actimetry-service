from BaseModel import BaseModel
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship


class ActimetryCollection(BaseModel):
    """
    ActimetryCollection model representing a collection of raw assets in the Actimetry system. This is related to a set of raw data that is uploaded to the server.

    A Collection needs to have a name, a description, and a date of creation.
    It can also have a date of last modification and a user / device / service that created it.

    The collection need to have a state to indicate if it is complete or ongoing.

    Once the collection is complete, it can be processed by an algorithm to generate results.

    All assets in a collection are related to the same session.

    We need to worry about the collection size and the number of assets in the collection.

    """

    __tablename__ = "t_actimetry_collections"
