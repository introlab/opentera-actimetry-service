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
                self.assertIn("dataset_info", response.json)
