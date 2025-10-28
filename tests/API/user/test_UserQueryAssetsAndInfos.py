import os
import io
import hashlib
import json
from tests.API.BaseActimetryServiceAPITest import BaseActimetryServiceAPITest
from libactimetry.db.models.ActimetryAsset import ActimetryAsset


class UserQueryAssetsAndInfosTest(BaseActimetryServiceAPITest):
    test_endpoint = '/api/user/assets/infos'
    asset_endpoint = '/api/user/assets'

    def setUp(self):
        super().setUp()
        # Create test file to stream
        self.test_file_size = 1024 * 1024 * 100
        with open('testfile', 'wb') as f:
            f.write(os.urandom(self.test_file_size))

        # Add this service to a test session type
        with self.app_context():
            params = {'id_user': 1}
            response = self._service.get_from_opentera_with_token(self.admin_user_token,
                                                                  api_url='/api/user/sessions',
                                                                  params=params)
            self.assertEqual(response.status_code, 200)
            self.id_target_session = response.json()[0]['id_session']
            id_session_type = response.json()[0]['id_session_type']

            params = {'id_session_type': id_session_type}
            response = self._service.get_from_opentera_with_token(self.admin_user_token,
                                                                  api_url='/api/user/sessiontypes/services',
                                                                  params=params)
            self.assertEqual(response.status_code, 200)
            additional_services_ids = [{'id_service': service['id_service']} for service in response.json()]
            additional_services_ids.append({'id_service': self._service.service_info['id_service']})

            params = {'session_type': {'id_session_type': id_session_type, 'services': additional_services_ids}}
            response = self._service.post_to_opentera_with_token(self.admin_user_token,
                                                                 api_url='/api/user/sessiontypes/services',
                                                                 json_data=params)
            self.assertEqual(response.status_code, 200)

    def tearDown(self):
        super().tearDown()
        if os.path.exists('testfile'):
            try:
                os.remove('testfile')
            except PermissionError:
                print("Can't remove testfile - permission denied")
                pass

    def test_get_endpoint_with_invalid_token(self):
        with self.app_context():
            response = self._get_with_token_auth(self.test_client, token="invalid")
            self.assertEqual(403, response.status_code)

    def test_post_endpoint_with_invalid_token(self):
        with self.app_context():
            response = self._post_with_token_auth(self.test_client, token="invalid")
            self.assertEqual(403, response.status_code)

    def test_delete_endpoint_with_invalid_token(self):
        with self.app_context():
            response = self._delete_with_token_auth(self.test_client, token="invalid")
            self.assertEqual(405, response.status_code)

    def test_get_endpoint_with_user_admin_token_no_params(self):
        with self.app_context():
            response = self._get_with_token_auth(self.test_client, token=self.admin_user_token)
            self.assertEqual(400, response.status_code)

    def test_get_endpoint_with_participant_static_token_no_params(self):
        with self.app_context():
            response = self._get_with_token_auth(self.test_client, token=self.participant_static_token)
            self.assertEqual(403, response.status_code)

    def test_get_endpoint_with_participant_dynamic_token_no_params(self):
        with self.app_context():
            response = self._get_with_token_auth(self.test_client, token=self.participant_dynamic_token)
            self.assertEqual(403, response.status_code)

    def test_get_endpoint_with_device_static_token_no_params(self):
        with self.app_context():
            response = self._get_with_token_auth(self.test_client, token=self.device_token)
            self.assertEqual(403, response.status_code)

    def test_get_endpoint_with_service_token_bad_param(self):
        with self.app_context():
            params = {'id_invalid': 1}
            response = self._get_with_token_auth(self.test_client, token=self._service.service_token, params=params)
            self.assertEqual(403, response.status_code)

    @staticmethod
    def calc_md5(data):
        hash_md5 = hashlib.md5()
        for chunk in iter(lambda: data.read(4096), b""):
            hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def delete_asset(self, asset_uuid: str):
        asset = ActimetryAsset.get_asset_for_uuid(asset_uuid)
        if asset:
            asset.delete_actimetry_asset('.')
            return True
        return False

    def test_full_as_user(self):
        with self.app_context():
            file_asset = {}
            with open('testfile', 'rb') as f:
                files = {'file': (f, 'testfile'),
                         'file_asset': json.dumps(file_asset)}

                response = self._post_file_with_token_auth(self.test_client, token=self.admin_user_token, files=files,
                                                           endpoint=self.asset_endpoint)
                self.assertEqual(400, response.status_code, 'Missing infos in file_asset')

            file_asset['id_session'] = 100
            file_asset['asset_name'] = "Test Asset"
            file_asset['asset_type'] = 'application/octet-stream'
            with open('testfile', 'rb') as f:
                files = {'file': (f, 'testfile'),
                         'file_asset': json.dumps(file_asset)}

                response = self._post_file_with_token_auth(self.test_client, token=self.admin_user_token, files=files,
                                                           endpoint=self.asset_endpoint)
                self.assertEqual(403, response.status_code, 'Forbidden access to session')

            file_asset['id_session'] = self.id_target_session

            with open('testfile', 'rb') as f:
                files = {'file': (f, 'testfile'),
                         'file_asset': json.dumps(file_asset)}

                response = self._post_file_with_token_auth(self.test_client, token=self.admin_user_token, files=files,
                                                           endpoint=self.asset_endpoint)
                self.assertEqual(200, response.status_code, 'Asset post OK')
                self.assertTrue(response.json.__contains__('asset_uuid'))
                self.assertTrue(response.json.__contains__('id_asset'))

            asset_uuid = response.json['asset_uuid']
            asset_id = response.json['id_asset']

            # Query asset information to make sure it was properly created
            params = {'asset_uuid': asset_uuid, 'with_urls': True}

            response = self._service.get_from_opentera_with_token(token=self.admin_user_token, params=params,
                                                 api_url=self.asset_endpoint)
            self.assertEqual(200, response.status_code)
            self.assertTrue(len(response.json()), 1)
            self.assertEqual(response.json()[0]['asset_uuid'], asset_uuid)
            self.assertTrue('access_token' in response.json()[0])

            access_token = response.json()[0]['access_token']

            # Get specific service information on that URL
            params = {'asset_uuid': asset_uuid}
            response = self._get_with_token_auth(self.test_client, token=self.admin_user_token, params=params)
            self.assertEqual(400, response.status_code, 'Missing access token')
            params['access_token'] = 'invalid'
            response = self._get_with_token_auth(self.test_client, token=self.admin_user_token, params=params)
            self.assertEqual(403, response.status_code, 'Forbidden - invalid token')

            params['access_token'] = access_token
            response = self._get_with_token_auth(self.test_client, token=self.admin_user_token, params=params)
            self.assertEqual(200, response.status_code)
            self.assertTrue(response.json.__contains__('asset_uuid'))
            self.assertEqual(response.json['asset_uuid'], asset_uuid)

            # Change original file name with a POST query
            json_data = {}
            response = self._post_with_token_auth(self.test_client, token=self.admin_user_token, json=json_data)
            self.assertEqual(400, response.status_code, 'Missing file asset info')

            json_data = {'access_token': access_token}
            response = self._post_with_token_auth(self.test_client, token=self.admin_user_token, json=json_data)
            self.assertEqual(400, response.status_code, 'Badly formatted request')

            json_data = {'file_asset': {}}
            response = self._post_with_token_auth(self.test_client, token=self.admin_user_token, json=json_data)
            self.assertEqual(400, response.status_code, 'Missing asset UUID')

            json_data = {'file_asset': {'asset_uuid': '1111111', 'access_token': access_token}}
            response = self._post_with_token_auth(self.test_client, token=self.admin_user_token, json=json_data)
            self.assertEqual(403, response.status_code, 'Forbidden access to UUID')

            json_data = {'file_asset': {'asset_uuid': asset_uuid, 'access_token': access_token}}
            response = self._post_with_token_auth(self.test_client, token=self.admin_user_token, json=json_data)
            self.assertEqual(400, response.status_code, 'No file name')

            json_data = {'file_asset': {'asset_uuid': asset_uuid, 'asset_original_filename': 'testfile2',
                                        'access_token': access_token}}
            response = self._post_with_token_auth(self.test_client, token=self.admin_user_token, json=json_data)
            self.assertEqual(200, response.status_code, 'Original file name changed')
            self.assertEqual(response.json['asset_original_filename'], 'testfile2')

            # Try to download that file now from the file URL
            params = {'asset_uuid': asset_uuid}
            response = self._get_with_token_auth(self.test_client, token=self.admin_user_token, params=params,
                                                 endpoint=self.asset_endpoint)
            self.assertEqual(400, response.status_code, 'Missing access token')

            params = {'asset_uuid': asset_uuid, 'access_token': 'invalid'}
            response = self._get_with_token_auth(self.test_client, token=self.admin_user_token, params=params,
                                                 endpoint=self.asset_endpoint)

            self.assertEqual(403, response.status_code, 'Forbidden access with invalid token')

            params = {'asset_uuid': asset_uuid, 'access_token': access_token}
            response = self._get_with_token_auth(self.test_client, token=self.admin_user_token, params=params,
                                                 endpoint=self.asset_endpoint)

            self.assertEqual(200, response.status_code, 'Forbidden access with invalid token')
            self.assertEqual(self.test_file_size, response.content_length)
            self.assertEqual('application/octet-stream', response.content_type)
            received_file = io.BytesIO(response.data)
            local_file = io.FileIO('testfile')
            md5_received_file = self.calc_md5(received_file)
            md5_local_file = self.calc_md5(local_file)
            self.assertEqual(md5_received_file, md5_local_file)
            local_file.close()
            received_file.close()

            # Delete asset from service as user
            params = {}
            response = self._delete_with_token_auth(self.test_client, token=self.admin_user_token, params=params,
                                                    endpoint=self.asset_endpoint)

            self.assertEqual(400, response.status_code, 'Missing access token and uuid')

            params = {'uuid': asset_uuid}
            response = self._delete_with_token_auth(self.test_client, token=self.admin_user_token, params=params,
                                                    endpoint=self.asset_endpoint)

            self.assertEqual(400, response.status_code, 'Missing access token')

            params = {'access_token': access_token}
            response = self._delete_with_token_auth(self.test_client, token=self.admin_user_token, params=params,
                                                    endpoint=self.asset_endpoint)

            self.assertEqual(400, response.status_code, 'Missing asset_uuid')

            params = {'uuid': asset_uuid, 'access_token': '1234'}
            response = self._delete_with_token_auth(self.test_client, token=self.admin_user_token, params=params,
                                                    endpoint=self.asset_endpoint)

            self.assertEqual(403, response.status_code, 'Invalid access_token')

            params = {'uuid': asset_uuid, 'access_token': access_token}
            response = self._delete_with_token_auth(self.test_client, token=self.admin_user_token, params=params,
                                                    endpoint=self.asset_endpoint)

            self.assertEqual(200, response.status_code, 'Delete OK')
            self.assertTrue(self.delete_asset(asset_uuid))
