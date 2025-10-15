import os

from libactimetry.db.models.BaseModel import BaseModel
from sqlalchemy import Column, Integer, String, Sequence, BigInteger, SmallInteger, exc, UUID
from sqlalchemy.orm import relationship
from enum import Enum


class ActimetryAssetStatus(Enum):
    STATUS_UNPROCESSED = 0
    STATUS_PROCESSED = 1
    STATUS_NOTPROCESSABLE = 2


class ActimetryAsset(BaseModel):
    """
    ActimetryAsset model representing an asset in the Actimetry system. This is related to a raw data that is uploaded to the server.
    """
    __tablename__ = "t_actimetry_assets"
    id_asset = Column(Integer, Sequence('id_asset_sequence'), primary_key=True, autoincrement=True)
    id_collection = Column(Integer, nullable=False)  # Collection ID, usually equal to id_session
    asset_uuid = Column(String, nullable=False, unique=True)
    asset_original_filename = Column(String, nullable=False)
    asset_file_size = Column(BigInteger, nullable=False)
    asset_status = Column(SmallInteger, nullable=False, default=ActimetryAssetStatus.STATUS_UNPROCESSED.value)

    @staticmethod
    def get_asset_for_uuid(uuid_asset: str):
        return ActimetryAsset.query.filter_by(asset_uuid=uuid_asset).first()

    @staticmethod
    def get_assets_for_uuids(uuids_asset: list):
        return ActimetryAsset.query.filter(ActimetryAsset.asset_uuid.in_(uuids_asset)).all()

    @staticmethod
    def get_assets_for_collection(collection_id: int):
        return ActimetryAsset.query.filter(ActimetryAsset.id_collection == collection_id).all()

    @staticmethod
    def collection_has_assets(collection_id: int) -> bool:
        return ActimetryAsset.query.filter(ActimetryAsset.id_collection == collection_id).first() is not None

    # Delete this asset. file_folder is required to delete the file too.
    def delete_actimetry_asset(self, file_folder: str) -> bool:
        # Delete related file from system
        file_name = os.path.join(file_folder, self.asset_uuid)
        if os.path.exists(file_name):
            # print('ActimetryAsset: Deleted ' + file_name)
            os.remove(file_name)
        else:
            # print('ActimetryAsset: File not found: ' + file_name)
            return False

        # Delete self from database
        try:
            self.db().session.delete(self)
            self.commit()
        except exc.SQLAlchemyError:
            return False

        return True