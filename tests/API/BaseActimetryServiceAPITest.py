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
        cls._db_man.open_local(
            {"filename": os.path.join(os.getcwd(), "test.db")}, echo=True, ram=True
        )

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
        with self.app_context():
            pass

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

    def _login_user(
        self, username: str, password: str, endpoint: str = "/api/user/login"
    ) -> dict:
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

    def _get_participants(self, user_token: str, id_site: int):
        params = {"full": True, "id_site": id_site}
        response = self._service.get_from_opentera_with_token(
            token=user_token, api_url="/api/user/participants", params=params
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

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
