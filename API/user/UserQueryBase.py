from flask_babel import gettext
from flask_restx import Resource
from requests import Response
from opentera.modules.BaseModule import BaseModule
from opentera.services.ServiceAccessManager import current_user_client


class UserQueryBase(Resource):

    def __init__(self, _api, *args, **kwargs):
        Resource.__init__(self, _api, *args, **kwargs)
        self.module: BaseModule = kwargs.get("flaskModule", None)
        self.test: bool = kwargs.get("test", False)

    def _verify_session_access(self, id_session: int) -> bool:
        if not current_user_client:
            return False

        if not self.module:
            return False

        if not id_session:
            return False

        # Call user api to get session information
        response: Response = current_user_client.do_get_request_to_backend(
            "/api/user/sessions", params={"id_session": id_session}
        )
        if response.status_code != 200:
            return False

        sessions = response.json()
        if not sessions or len(sessions) != 1:
            return False

        session = sessions[0]
        if "id_session" not in session or session["id_session"] != id_session:
            return False

        return True

    def _verify_participant_access(self, participant_uuid: str) -> bool:
        if not current_user_client:
            return False

        if not self.module:
            return False

        if not participant_uuid:
            return False

        # Call user api to get participant information
        response: Response = current_user_client.do_get_request_to_backend(
            "/api/user/participants", params={"participant_uuid": participant_uuid}
        )
        if response.status_code != 200:
            return False

        participants = response.json()
        if not participants or len(participants) != 1:
            return False

        participant = participants[0]
        if "participant_uuid" not in participant or participant["participant_uuid"] != participant_uuid:
            return False

        return True

    def _get_participant_info(self, participant_uuid: str) -> dict | None:
        if not current_user_client:
            return None

        if not self.module:
            return None

        if not participant_uuid:
            return None

        # Call user api to get participant information
        response: Response = current_user_client.do_get_request_to_backend(
            "/api/user/participants", params={"participant_uuid": participant_uuid}
        )
        if response.status_code != 200:
            return None

        participants = response.json()
        if not participants or len(participants) != 1:
            return None

        participant = participants[0]
        if "participant_uuid" not in participant or participant["participant_uuid"] != participant_uuid:
            return None

        return participant
