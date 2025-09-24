import unittest
from flask import Flask
from libactimetry.db.DBManager import DBManager
from libactimetry.db.models.ActimetryDatabase import ActimetryDatabase


class ActimetryDatabaseTest(unittest.TestCase):
    def setUp(self):
        # Set Fake Flask app
        self._app = Flask(__name__)
        self._app.debug = False
        self._app.testing = True
        self._db_manager = DBManager(self._app, test=True)
        self._db_manager.open_local(None, echo=False, ram=True)
        self.assertIsNotNone(self._db_manager)
        self._db_manager.create_defaults(None, test=True)

    def tearDown(self):
        self._db_manager.close()
        self._app = None

    def test_create_defaults(self):
        with self._app.app_context():
            dbs = ActimetryDatabase.query.all()
            self.assertIsNotNone(dbs)
            self.assertEqual(len(dbs), 0)

    def test_json_schema(self):
        schema = ActimetryDatabase.get_json_schema()
        self.assertIsNotNone(schema)
        self.assertIn("properties", schema)
        # First level is model name
        self.assertIn("database", schema["properties"])
        self.assertIn("required", schema)
        self.assertIn("database", schema["required"])
        self.assertIn("type", schema["properties"]["database"])

        self.assertEqual(schema["properties"]["database"]["type"], "object")
        self.assertIn("properties", schema["properties"]["database"])
        self.assertIn("required", schema["properties"]["database"])
        self.assertIn("id_database", schema["properties"]["database"]["required"])
        self.assertIn("id_database", schema["properties"]["database"]["properties"])
        self.assertIn("id_session", schema["properties"]["database"]["properties"])
        self.assertIn("database_uuid", schema["properties"]["database"]["properties"])
        self.assertIn("database_participant_uuid", schema["properties"]["database"]["properties"])
        self.assertIn("database_name", schema["properties"]["database"]["properties"])
        self.assertIn("database_type", schema["properties"]["database"]["properties"])
        self.assertIn("database_creation_datetime", schema["properties"]["database"]["properties"])
        self.assertIn("database_expiration_datetime", schema["properties"]["database"]["properties"])
