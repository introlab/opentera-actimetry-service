from BaseModel import BaseModel
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship


class ActimetryAsset(BaseModel):
    """
    ActimetryAsset model representing an asset in the Actimetry system. This is related to a raw data that is uploaded to the server.
    """

    __tablename__ = "t_actimetry_assets"
