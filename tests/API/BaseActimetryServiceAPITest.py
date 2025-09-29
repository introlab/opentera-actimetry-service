import unittest
import time
import uuid
import jwt
import os
import json
import requests
from datetime import date, datetime, timedelta

from flask.testing import FlaskClient
from flask import Flask
from ConfigManager import ConfigManager
from opentera.services.ServiceAccessManager import ServiceAccessManager
from tests.API.FakeActimetryService import FakeActimetryService
from libactimetry.db.models.BaseModel import BaseModel
from libactimetry.db.DBManager import DBManager
import Globals


def infinite_jti_sequence():
    num = 0
    while True:
        yield num
        num += 1


# Initialize generator, call next(user_jti_generator) to get next sequence number
user_jti_generator = infinite_jti_sequence()
participant_jti_generator = infinite_jti_sequence()


class BaseActimetryServiceAPITest(unittest.TestCase):
    test_endpoint = ""

    @classmethod
    def setUpClass(cls):
        # Instance of Fake service API will create a new flask_app
        cls._service = FakeActimetryService()

        # API Need those variables to be set
        Globals.service = cls._service
        Globals.config_man = cls._service.config_man

        # Setup SurveyJS database
        cls._service.flask_app.debug = False
        cls._service.flask_app.testing = True
        cls._db_man = DBManager(app=cls._service.flask_app, test=True)
        # Setup DB in RAM
        # Create file in current directory
        cls._db_man.open_local({"filename": os.path.join(os.getcwd(), "test.db")}, echo=True, ram=True)

        # Creating default users / tests. Time-consuming, only once per test file.
        with cls._service.flask_app.app_context():
            cls._db_man.create_defaults(cls._service.config_man, test=True)
            cls.db = cls._db_man.db

    def app_context(self):
        self.assertIsNotNone(self._service)
        self.assertIsNotNone(self._service.flask_app)
        return self._service.flask_app.app_context()

    @classmethod
    def tearDownClass(cls):
        with cls._service.flask_app.app_context():
            BaseModel.metadata.drop_all(cls.db.engine)

    def setUp(self):
        self.assertIsNotNone(self._service)
        self.assertIsNotNone(self._service.flask_app)
        self.test_client = self._service.flask_app.test_client()
        self.assertIsNotNone(self.test_client)

        # Get tokens for tests
        self._admin_user = self._login_user("admin", "admin")
        self.admin_user_token = self._admin_user["user_token"]

        self.site_admin_token = self._login_user("siteadmin", "siteadmin")["user_token"]

        devices = self._service.get_from_opentera_with_token(token=self.admin_user_token, api_url="/api/user/devices")
        self.device_token = devices.json()[0]["device_token"]
        self.id_device = devices.json()[0]["id_device"]
        participants = self._service.get_from_opentera_with_token(
            token=self.admin_user_token, api_url="/api/user/participants", params={"id_project": 1}
        )
        self.participant_static_token = participants.json()[0]["participant_token"]
        participant = self._login_participant("participant1", "opentera")
        self.participant_dynamic_token = participant["participant_token"]

        self.service_token = self._service.service_token

    def tearDown(self):
        with self.app_context():
            pass

    @staticmethod
    def _generate_fake_user_token(
        name="FakeUser",
        user_uuid=str(uuid.uuid4()),
        role=[],
        superadmin=False,
        expiration=3600,
    ):
        # Creating token with user info
        now = time.time()
        token_key = ServiceAccessManager.api_user_token_key

        payload = {
            "iat": int(now),
            "exp": int(now) + expiration,
            "iss": "TeraServer",
            "jti": next(user_jti_generator),
            "user_uuid": user_uuid,
            "role": role,
            "id_user": 1,
            "user_fullname": name,
            "user_superadmin": superadmin,
            "service_access": {"SurveyJSService": role},  # roles of the user
        }

        return jwt.encode(payload, token_key, algorithm="HS256")

    @staticmethod
    def _generate_fake_user_role(name="FakeUser", superadmin=False, expiration=3600):
        # Creating token with user info
        now = time.time()
        token_key = ServiceAccessManager.api_user_token_key
        payload = {
            "iat": int(now),
            "exp": int(now) + expiration,
            "iss": "TeraServer",
            "jti": next(user_jti_generator),
            "id_user": 1,
            "user_fullname": name,
            "user_superadmin": superadmin,
            "service_access": {"SurveyJSService": []},
        }

        return jwt.encode(payload, token_key, algorithm="HS256")

    @staticmethod
    def _generate_fake_static_participant_token(participant_uuid=str(uuid.uuid4())):
        # Creating token with participant info
        token_key = ServiceAccessManager.api_participant_static_token_key
        payload = {
            "iss": "TeraServer",
            "jti": next(participant_jti_generator),
            "participant_uuid": participant_uuid,
            "id_participant": 1,
        }
        return jwt.encode(payload, token_key, algorithm="HS256")

    @staticmethod
    def _generate_fake_dynamic_participant_token(
        name="FakeParticipant", participant_uuid=str(uuid.uuid4()), expiration=3600
    ):
        # Creating token with participant info
        now = time.time()
        token_key = ServiceAccessManager.api_participant_static_token_key
        payload = {
            "iat": int(now),
            "exp": int(now) + expiration,
            "iss": "TeraServer",
            "jti": next(participant_jti_generator),
            "participant_uuid": participant_uuid,
            "id_participant": 2,
            "user_fullname": name,
        }

        return jwt.encode(payload, token_key, algorithm="HS256")

    def _login_user(self, username: str, password: str, endpoint: str = "/api/user/login") -> dict:
        # 2FA is disabled for tests
        # Websocket is disabled for tests
        # Use HTTPAuth to login
        server_url = f'https://{self._service.config_man.backend_config["hostname"]}:{self._service.config_man.backend_config["port"]}'
        params = {"with_websocket": False}
        response = requests.get(
            server_url + endpoint,
            auth=(username, password),
            params=params,
            verify=False,
        )
        self.assertTrue(response.status_code == 200)
        return response.json()

    def _login_participant(self, username: str, password: str, endpoint: str = "/api/participant/login") -> dict:
        server_url = f'https://{self._service.config_man.backend_config["hostname"]}:{self._service.config_man.backend_config["port"]}'
        params = {}
        response = requests.get(
            server_url + endpoint,
            auth=(username, password),
            params=params,
            verify=False,
        )
        self.assertTrue(response.status_code == 200)
        return response.json()

    def _get_participants(self, user_token: str, id_site: int):
        with self.app_context():
            params = {"full": True, "id_site": id_site}
            response = self._service.get_from_opentera_with_token(
                token=user_token, api_url="/api/user/participants", params=params
            )
            self.assertEqual(response.status_code, 200)
            return response.json()

    def _get_actimetry_session_type(self, user_token: str) -> dict:
        with self.app_context():
            params = {"list": True}
            response = self._service.get_from_opentera_with_token(
                token=user_token, api_url="/api/user/sessiontypes", params=params
            )
            self.assertEqual(response.status_code, 200)
            session_types = response.json()
            for session_type in session_types:
                if session_type["session_type_name"] == "Actimetry":
                    return session_type

        self.fail("No Actimetry session type found")

    def _create_session(self, user_token: str, id_session_type: int, id_participant: int) -> dict:
        with self.app_context():
            params = {}

            session_info = {
                "session": {
                    "id_creator_participant": id_participant,
                    "id_session": 0,  # New Session
                    "id_session_type": id_session_type,
                    "session_participants_ids": [id_participant],
                    "session_comments": "string",
                    "session_duration": 0,
                    "session_name": "string",
                    "session_parameters": "string",
                    "session_start_datetime": datetime.now().isoformat(),
                    "session_status": 0,
                }
            }
            response = self._service.post_to_opentera_with_token(
                token=user_token, api_url="/api/user/sessions", params=params, json_data=session_info
            )
            self.assertEqual(response.status_code, 200)
            self.assertGreater(len(response.json()), 0)
            return response.json()[0]

    def _create_database_for_participant(self, participant_info: dict) -> dict:
        with self.app_context():
            # Get session type
            session_type_info: dict = self._get_actimetry_session_type(self.admin_user_token)

            # Create a session to link the database to
            session = self._create_session(
                user_token=self.admin_user_token,
                id_session_type=session_type_info["id_session_type"],
                id_participant=participant_info["id_participant"],
            )

            self.assertIsNotNone(session)
            self.assertIn("id_session", session)
            self.assertGreater(session["id_session"], 0)

            # Create a database linked to that session
            database_info = {
                "database": {
                    "id_database": 0,
                    "database_name": "Test Database",
                    "database_description": "This is a test database",
                    "database_type": 1,  # SQLite
                    "database_participant_uuid": participant_info["participant_uuid"],
                    "id_session": session["id_session"],
                    "database_parameters": '{"param1": "value1", "param2": "value2"}',
                }
            }

            response = self._post_with_token_auth(
                self.test_client, token=self.admin_user_token, json=database_info, endpoint="/api/user/databases"
            )
            self.assertEqual(response.status_code, 200)
            return response.json

    def _get_with_token_auth(
        self,
        client: FlaskClient,
        token: str = "",
        params=None,
        language="fr",
        endpoint=None,
    ):
        if params is None:
            params = {}
        if endpoint is None:
            endpoint = self.test_endpoint
        headers = {"Authorization": "OpenTera " + token}
        headers["Accept-Language"] = language
        return client.get(endpoint, headers=headers, query_string=params)

    def _post_with_token_auth(
        self,
        client: FlaskClient,
        token: str = "",
        json: dict = None,
        params: dict = None,
        endpoint: str = None,
    ):
        if params is None:
            params = {}
        if endpoint is None:
            endpoint = self.test_endpoint
        headers = {"Authorization": "OpenTera " + token}
        return client.post(endpoint, headers=headers, query_string=params, json=json)

    def _post_file_with_token_auth(
        self, client: FlaskClient, token: str = "", files: dict = None, params: dict = None, endpoint: str = None
    ):
        if params is None:
            params = {}
        if endpoint is None:
            endpoint = self.test_endpoint
        headers = {"Authorization": "OpenTera " + token}

        return client.post(
            endpoint, headers=headers, query_string=params, data=files, content_type="multipart/form-data"
        )

    def _delete_with_token_auth(
        self,
        client: FlaskClient,
        token: str = "",
        params: dict = None,
        endpoint: str = None,
    ):
        if params is None:
            params = {}
        if endpoint is None:
            endpoint = self.test_endpoint
        headers = {"Authorization": "OpenTera " + token}
        return client.delete(endpoint, headers=headers, query_string=params)
