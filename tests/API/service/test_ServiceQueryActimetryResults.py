import uuid

from tests.API.BaseActimetryServiceAPITest import BaseActimetryServiceAPITest
from libactimetry.db.models.ActimetryWorkerLog import ActimetryWorkerLog, WorkerOwnerType, WorkerType


class ServiceQueryActimetryDatabaseTest(BaseActimetryServiceAPITest):
    test_endpoint = "/api/service/results"

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

    def test_get_endpoint_with_service_token_no_params(self):
        with self.app_context():
            response = self._get_with_token_auth(self.test_client, token=self._service.service_token)
            self.assertEqual(response.status_code, 400)

    def test_get_endpoint_with_service_token_but_invalid_param(self):
        with self.app_context():
            response = self._get_with_token_auth(
                self.test_client,
                token=self._service.service_token,
                params={"invalid_param": "invalid_value"},
            )
            self.assertEqual(response.status_code, 400)

    def test_get_endpoint_with_user_token_with_valid_param(self):
        with self.app_context():
            response = self._get_with_token_auth(
                self.test_client,
                token=self.admin_user_token,
                params={"id_database": 1},
            )
            self.assertEqual(response.status_code, 403)

    def test_get_endpoint_with_participant_token_with_valid_param(self):
        with self.app_context():
            response = self._get_with_token_auth(
                self.test_client,
                token=self.participant_dynamic_token,
                params={"id_database": 1},
            )
            self.assertEqual(response.status_code, 403)
            response = self._get_with_token_auth(
                self.test_client,
                token=self.participant_static_token,
                params={"id_database": 1},
            )
            self.assertEqual(response.status_code, 403)

    def test_get_endpoint_with_service_token_and_id_database_not_found(self):
        with self.app_context():
            response = self._get_with_token_auth(
                self.test_client,
                token=self._service.service_token,
                params={"id_database": 99999},
            )
            self.assertEqual(response.status_code, 404)

    def test_get_endpoint_with_service_token_and_database_uuid_not_found(self):
        with self.app_context():
            response = self._get_with_token_auth(
                self.test_client,
                token=self._service.service_token,
                params={"database_uuid": str(uuid.uuid4())},
            )
            self.assertEqual(response.status_code, 404)

    def test_get_endpoint_with_service_token_and_database_participant_uuid_not_found(self):
        with self.app_context():
            response = self._get_with_token_auth(
                self.test_client,
                token=self._service.service_token,
                params={"database_participant_uuid": str(uuid.uuid4())},
            )
            self.assertEqual(response.status_code, 404)

    def test_get_endpoint_with_service_token_and_valid_id_database(self):
        with self.app_context():
            # Get participants from id_site = 1
            participants = self._get_participants(self.admin_user_token, id_site=1)

            for participant in participants:
                # Create database for that participant
                database = self._create_database_for_participant(participant)
                self.assertIsNotNone(database)
                self.assertIn("id_database", database)

                response = self._get_with_token_auth(
                    self.test_client,
                    token=self._service.service_token,
                    params={"id_database": database["id_database"]},
                )
                self.assertEqual(response.status_code, 200)
                data = response.json
                self.assertIsInstance(data, list)
                # Empty for now
                self.assertGreaterEqual(len(data), 0)
