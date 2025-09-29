import uuid

from tests.API.BaseActimetryServiceAPITest import BaseActimetryServiceAPITest
from libactimetry.db.models.ActimetryWorkerLog import ActimetryWorkerLog, WorkerOwnerType, WorkerType
from libactimetry.db.models.ActimetryDatabase import ActimetryDatabase


class UserProcessingTest(BaseActimetryServiceAPITest):
    test_endpoint = '/api/user/processing'

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

    def test_get_endpoint_with_invalid_worker_uuid(self):
        with self.app_context():
            response = self._get_with_token_auth(self.test_client, token=self.admin_user_token,
                                                 params={'uuid': 'invalid'})
            self.assertEqual(response.status_code, 403)

    def test_get_endpoint_with_valid_worker_uuid(self):
        with self.app_context():
            # Create sample worker in database
            log = ActimetryWorkerLog()
            log.worker_uuid = str(uuid.uuid4())
            log.worker_owner_type = WorkerOwnerType.OWNER_USER.value
            log.worker_owner_uuid = self._admin_user['user_uuid']
            log.worker_type = WorkerType.TYPE_GENERAL.value
            ActimetryWorkerLog.insert(log)
            response = self._get_with_token_auth(self.test_client, token=self.admin_user_token,
                                                 params={'uuid': log.worker_uuid})
            self.assertEqual(response.status_code, 200)

    def test_get_endpoint_with_forbidden_worker_uuid(self):
        with self.app_context():
            # Create sample worker in database
            log = ActimetryWorkerLog()
            log.worker_uuid = str(uuid.uuid4())
            log.worker_owner_type = WorkerOwnerType.OWNER_USER.value
            log.worker_owner_uuid = self._admin_user['user_uuid']
            log.worker_type = WorkerType.TYPE_GENERAL.value
            ActimetryWorkerLog.insert(log)
            response = self._get_with_token_auth(self.test_client, token=self.site_admin_token,
                                                 params={'uuid': log.worker_uuid})
            self.assertEqual(response.status_code, 403)

    def test_post_endpoint_worker(self):
        with self.app_context():
            # Get participant uuid to test
            response = self._service.get_from_opentera_with_token(token=self.admin_user_token,
                                                                  api_url='/api/user/participants',
                                                                  params={'id_project': 1})

            participant_uuid = response.json()[0]['participant_uuid']

            db = ActimetryDatabase()
            db.id_session = 1
            db.database_uuid = str(uuid.uuid4())
            db.database_participant_uuid = participant_uuid
            db.database_name = 'test_database'
            ActimetryDatabase.insert(db)

            params = {'worker': {'key': 'Test', 'participant_uuid': participant_uuid, 'parameters':
                {'parameter1': 1.234, 'parameter2': 'p2', 'parameter3': "false"}}}

            response = self._post_with_token_auth(self.test_client, token=self.admin_user_token,
                                                  json=params)
            self.assertEqual(response.status_code, 200)
