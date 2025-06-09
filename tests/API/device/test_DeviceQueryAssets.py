from tests.API.BaseActimetryServiceAPITest import BaseActimetryServiceAPITest
from opentera.db.models.TeraAsset import TeraAsset
from opentera.db.models.TeraUser import TeraUser
from opentera.db.models.TeraParticipant import TeraParticipant
from opentera.db.models.TeraDevice import TeraDevice
from opentera.db.models.TeraService import TeraService
from opentera.services.ServiceAccessManager import ServiceAccessManager


class DeviceQueryAssetsTest(BaseActimetryServiceAPITest):
    test_endpoint = '/api/device/assets'

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

    def test_get_endpoint_with_device_token_no_params(self):
        with self.app_context():
            response = self._get_with_token_auth(self.test_client, token=self.device_token)
            self.assertEqual(response.status_code, 400)

    def test_get_endpoint_with_participant_static_token_no_params(self):
        with self.app_context():
            response = self._get_with_token_auth(self.test_client, token=self.participant_static_token)
            self.assertEqual(response.status_code, 403)

    def test_get_endpoint_with_participant_dynamic_token_no_params(self):
        with self.app_context():
            response = self._get_with_token_auth(self.test_client, token=self.participant_dynamic_token)
            self.assertEqual(response.status_code, 403)
