import unittest
from flask import Flask
from libactimetry.db.DBManager import DBManager


class DBManagerTest(unittest.TestCase):
    def setUp(self):
        # Set Fake Flask app
        self._app = Flask(__name__)

    def tearDown(self):
        pass

    def test_create_defaults(self):
        db_manager = DBManager(self._app, test=True)
        self.assertIsNotNone(db_manager)
