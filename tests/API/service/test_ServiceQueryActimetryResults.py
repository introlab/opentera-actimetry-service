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
