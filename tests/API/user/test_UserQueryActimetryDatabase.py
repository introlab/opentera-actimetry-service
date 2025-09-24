import uuid

from tests.API.BaseActimetryServiceAPITest import BaseActimetryServiceAPITest
from libactimetry.db.models.ActimetryWorkerLog import ActimetryWorkerLog, WorkerOwnerType, WorkerType


class UserProcessingTest(BaseActimetryServiceAPITest):
    test_endpoint = "/api/user/databases"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_get_endpoint_with_invalid_token(self):
        with self.app_context():
            response = self._get_with_token_auth(self.test_client, token="invalid")
            self.assertEqual(response.status_code, 403)

    def test_post_endpoint_with_invalid_token(self):
        with self.app_context():
            response = self._post_with_token_auth(self.test_client, token="invalid", json={})
            self.assertEqual(response.status_code, 403)

    def test_delete_endpoint_with_invalid_token(self):
        with self.app_context():
            response = self._delete_with_token_auth(self.test_client, token="invalid")
            self.assertEqual(response.status_code, 405)

    def test_get_endpoint_with_participant_static_token_no_params(self):
        with self.app_context():
            response = self._get_with_token_auth(self.test_client, token=self.participant_static_token)
            self.assertEqual(response.status_code, 403)

    def test_get_endpoint_with_participant_dynamic_token_no_params(self):
        with self.app_context():
            response = self._get_with_token_auth(self.test_client, token=self.participant_dynamic_token)
            self.assertEqual(response.status_code, 403)

    def test_get_endpoint_with_device_static_token_no_params(self):
        with self.app_context():
            response = self._get_with_token_auth(self.test_client, token=self.device_token)
            self.assertEqual(response.status_code, 403)

    def test_get_endpoint_with_service_token_no_params(self):
        with self.app_context():
            response = self._get_with_token_auth(self.test_client, token=self._service.service_token)
            self.assertEqual(response.status_code, 403)

    def test_get_endpoint_without_parameters(self):
        with self.app_context():
            response = self._get_with_token_auth(self.test_client, token=self.admin_user_token)
            self.assertEqual(response.status_code, 400)

    def test_get_endpoint_with_invalid_parameters(self):
        with self.app_context():
            response = self._get_with_token_auth(
                self.test_client, token=self.admin_user_token, params={"invalid": "param"}
            )
            self.assertEqual(response.status_code, 400)

    def test_post_endpoint_with_valid_schema(self):
        with self.app_context():
            # Get session type
            session_type_info: dict = self._get_actimetry_session_type(self.admin_user_token)

            # Get participants from id_site = 1
            participants = self._get_participants(self.admin_user_token, id_site=1)

            for participant in participants:
                # Create a session to link the database to
                session = self._create_session(
                    user_token=self.admin_user_token,
                    id_session_type=session_type_info["id_session_type"],
                    id_participant=participant["id_participant"],
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
                        "database_participant_uuid": participant["participant_uuid"],
                        "id_session": session["id_session"],
                        "database_parameters": '{"param1": "value1", "param2": "value2"}',
                    }
                }

                response = self._post_with_token_auth(self.test_client, token=self.admin_user_token, json=database_info)
                self.assertEqual(response.status_code, 200)

                response_json = response.json
                self.assertIsNotNone(response_json)
                self.assertIn("id_database", response_json)
                self.assertGreater(response_json["id_database"], 0)
                self.assertIn("database_uuid", response_json)
                self.assertIsNotNone(response_json["database_uuid"])
                self.assertIn("database_creation_datetime", response_json)
                self.assertIsNotNone(response_json["database_creation_datetime"])
                self.assertIn("database_expiration_datetime", response_json)
