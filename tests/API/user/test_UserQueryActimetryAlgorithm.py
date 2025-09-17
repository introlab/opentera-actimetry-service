from tests.API.BaseActimetryServiceAPITest import BaseActimetryServiceAPITest


class UserAlgorithmTest(BaseActimetryServiceAPITest):
    test_endpoint = '/api/user/algorithms'

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
            self.assertEqual(response.status_code, 405)

    def test_delete_endpoint_with_invalid_token(self):
        with self.app_context():
            response = self._delete_with_token_auth(self.test_client, token="invalid")
            self.assertEqual(response.status_code, 405)

    def test_get_endpoint_with_user_admin_token_no_params(self):
        with self.app_context():
            response = self._get_with_token_auth(self.test_client, token=self.admin_user_token)
            self.assertEqual(response.status_code, 200)
            # TODO: Compare number and items with libopenimu algorithm list
            self.assertGreater(len(response.json), 0)
            for algo in response.json:
                self._validate_algo_definition(algo, False)

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

    def test_get_endpoint_with_list(self):
        with self.app_context():
            response = self._get_with_token_auth(self.test_client, token=self.admin_user_token, params={'list': True})
            self.assertEqual(response.status_code, 200)
            # TODO: Compare number and items with libopenimu algorithm list
            self.assertGreater(len(response.json), 0)
            for algo in response.json:
                self._validate_algo_definition(algo, True)

    def test_get_endpoint_with_specific_key(self):
        with self.app_context():
            response = self._get_with_token_auth(self.test_client, token=self.admin_user_token, params={'list': True})
            self.assertEqual(response.status_code, 200)
            self.assertGreater(len(response.json), 0)
            # Query the first one in the list
            algo_key = response.json[0]['key']
            response = self._get_with_token_auth(self.test_client, token=self.admin_user_token,
                                                 params={'key': algo_key})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.json), 1)
            self._validate_algo_definition(response.json[0], False)
            self.assertEqual(response.json[0]['key'], algo_key)

    def _validate_algo_definition(self, algo: dict, list: bool):
        self.assertTrue('name' in algo)
        self.assertTrue('key' in algo)
        self.assertTrue('version' in algo)
        if list:
            self.assertFalse('description' in algo)
            self.assertFalse('author' in algo)
            self.assertFalse('parameters' in algo)
            self.assertFalse('results' in algo)
        else:
            self.assertTrue('description' in algo)
            self.assertTrue('author' in algo)
            self.assertTrue('parameters' in algo)
            self.assertTrue('results' in algo)