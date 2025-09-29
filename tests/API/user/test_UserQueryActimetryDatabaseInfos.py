import uuid

from tests.API.BaseActimetryServiceAPITest import BaseActimetryServiceAPITest


class UserQueryActimetryDatabaseInfosTest(BaseActimetryServiceAPITest):
    test_endpoint = "/api/user/databases/infos"

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

    def test_get_endpoint_with_id_database_not_found(self):
        with self.app_context():
            response = self._get_with_token_auth(
                self.test_client,
                token=self.admin_user_token,
                params={"id_database": 99999},
            )
            self.assertEqual(response.status_code, 404)

    def test_get_endpoint_with_database_uuid_not_found(self):
        with self.app_context():
            response = self._get_with_token_auth(
                self.test_client,
                token=self.admin_user_token,
                params={"database_uuid": str(uuid.uuid4())},
            )
            self.assertEqual(response.status_code, 404)

    def test_get_endpoint_with_database_participant_uuid_no_access(self):
        with self.app_context():
            response = self._get_with_token_auth(
                self.test_client,
                token=self.admin_user_token,
                params={"database_participant_uuid": str(uuid.uuid4())},
            )
            self.assertEqual(response.status_code, 403)

    def test_get_endpoint_with_valid_token_and_id_database(self):
        with self.app_context():
            # Get participants from id_site = 1
            participants = self._get_participants(self.admin_user_token, id_site=1)

            for participant in participants:
                # Create database for that participant
                database = self._create_database_for_participant(participant)
                self.assertIsNotNone(database)
                self.assertIn("database_uuid", database)

                # Query the database info using id_database
                response = self._get_with_token_auth(
                    self.test_client,
                    token=self.admin_user_token,
                    params={"id_database": database["id_database"]},
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn("file_size", response.json)

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
