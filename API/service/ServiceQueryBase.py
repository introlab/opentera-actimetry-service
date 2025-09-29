from flask_babel import gettext
from flask_restx import Resource
from requests import Response
from opentera.modules.BaseModule import BaseModule
from opentera.services.ServiceAccessManager import current_service_client


class ServiceQueryBase(Resource):

    def __init__(self, _api, *args, **kwargs):
        Resource.__init__(self, _api, *args, **kwargs)
        self.module: BaseModule = kwargs.get("flaskModule", None)
        self.test: bool = kwargs.get("test", False)

    def _verify_session_access(self, id_session: int) -> bool:
        return False

    def _verify_participant_access(self, participant_uuid: str) -> bool:
        return False

    def _get_participant_info(self, participant_uuid: str) -> dict | None:
        return None
