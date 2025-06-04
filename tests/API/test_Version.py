import unittest
import uuid
import json
from datetime import date
import datetime
from tests.API.BaseActimetryServiceAPITest import BaseActimetryServiceAPITest
from typing import List


class VersionTest(BaseActimetryServiceAPITest):
    test_endpoint = "/api/version"

    def test_get_version(self):
        response = self.test_client.get(self.test_endpoint)
        self.assertEqual(response.status_code, 200)
        self.assertIn("service_name", response.json)
        self.assertIn("version", response.json)
        self.assertIn("test", response.json)
