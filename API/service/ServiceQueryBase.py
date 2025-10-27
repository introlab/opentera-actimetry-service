from flask_babel import gettext
from flask_restx import Resource
from requests import Response
from opentera.modules.BaseModule import BaseModule
import Globals as Globals
from opentera.services.ServiceAccessManager import current_service_client


class ServiceQueryBase(Resource):

    def __init__(self, _api, *args, **kwargs):
        Resource.__init__(self, _api, *args, **kwargs)
        self.module: BaseModule = kwargs.get("flaskModule", None)
        self.test: bool = kwargs.get("test", False)

    def _verify_session_access(self, id_session: int) -> bool:
        # TODO implement proper access control
        return True

    def _verify_participant_access(self, participant_uuid: str) -> bool:
        participant = self._get_participant_info(participant_uuid)
        return participant is not None

    @staticmethod
    def _get_participant_info(participant_uuid: str) -> dict | None:
        response = Globals.service.get_from_opentera('/api/service/participants',
                                                     params={'participant_uuid': participant_uuid})
        if response.status_code == 200:
            return response.json()
        return None
