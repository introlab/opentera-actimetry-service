import os
import json
from tests.API.BaseActimetryServiceAPITest import BaseActimetryServiceAPITest
from libactimetry.workers.WorkerManager import WorkerManager
from libactimetry.db.models.ActimetryWorkerLog import WorkerOwnerType


class UserAssetFileTest(BaseActimetryServiceAPITest):
    test_endpoint = '/api/user/assets'

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
            response = self._post_with_token_auth(self.test_client, token="invalid")
            self.assertEqual(response.status_code, 403)

    def test_delete_endpoint_with_invalid_token(self):
        with self.app_context():
            response = self._delete_with_token_auth(self.test_client, token="invalid")
            self.assertEqual(response.status_code, 403)

    def test_get_endpoint_with_user_admin_token_no_params(self):
        with self.app_context():
            response = self._get_with_token_auth(self.test_client, token=self.admin_user_token)
            self.assertEqual(response.status_code, 400)

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

    def test_import_assets_into_openimu(self):
        with self.app_context():
            # Create new session
            session_type = self._get_actimetry_session_type(self.admin_user_token)
            session = self._create_session(self.admin_user_token, id_session_type=session_type['id_session_type'], id_participant=1)

            # Create basic database
            response = self._service.get_from_opentera_with_token(
                token=self.admin_user_token, api_url="/api/user/participants", params={'id_participant': 1})
            self.assertEqual(response.status_code, 200)
            participant_uuid = response.json()[0]['participant_uuid']
            database_infos = {'database': {'id_database': 0,
                                           'database_participant_uuid': participant_uuid,
                                           'database_name': 'Test Database'}}
            response = self._post_with_token_auth(self.test_client, token=self.admin_user_token, json=database_infos,
                                                  endpoint='/api/user/databases')
            self.assertEqual(response.status_code, 200)

            # Import sample assets
            base_sample_dir = 'tests/sample_data/AppleWatch'
            samples = os.listdir(base_sample_dir)
            file_asset = {}
            for sample in samples:
                file_asset['id_session'] = session['id_session']
                file_asset['asset_name'] = sample
                file_asset['asset_type'] = 'application/octet-stream'
                with open(base_sample_dir + '/' + sample, 'rb') as f:
                    file = {'file': (f, sample),
                            'file_asset': json.dumps(file_asset)}
                    response = self._post_file_with_token_auth(self.test_client, token=self.admin_user_token,
                                                               files=file)
                    self.assertEqual(response.status_code, 200)

            # Import into database file
            worker_man = WorkerManager(self._service.flask_app)
            worker_man.start_openimu_importer_worker(participant_uuid=participant_uuid, base_assets_path='./files_test',
                                                     id_session=session['id_session'],
                                                     owner_uuid=self._service.service_uuid,
                                                     owner_type=WorkerOwnerType.OWNER_SERVICE)

            # Delete assets files
            os.removedirs('./files_test')

