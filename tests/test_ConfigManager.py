import unittest

from ConfigManager import ConfigManager


class ConfigManagerTest(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        # Clean up if necessary
        pass

    def test_default_config(self):
        config_manager = ConfigManager()
        config_manager.create_defaults()

        self.assertIsNotNone(config_manager.service_config.get("name", None))
        self.assertIsNotNone(config_manager.service_config.get("hostname", None))
        self.assertIsNotNone(config_manager.service_config.get("port", None))
        self.assertIsNotNone(config_manager.service_config.get("debug_mode", None))
        self.assertIsNotNone(config_manager.service_config.get("service_key", None))
        self.assertIsNotNone(config_manager.service_config.get("ServiceUUID", None))

        self.assertIsNotNone(config_manager.backend_config.get("hostname", None))
        self.assertIsNotNone(config_manager.backend_config.get("port", None))

        self.assertIsNotNone(config_manager.redis_config.get("hostname", None))
        self.assertIsNotNone(config_manager.redis_config.get("port", None))
        self.assertIsNotNone(config_manager.redis_config.get("username", None))
        self.assertIsNotNone(config_manager.redis_config.get("password", None))
        self.assertIsNotNone(config_manager.redis_config.get("db", None))

        self.assertIsNotNone(config_manager.db_config.get("name", None))
        self.assertIsNotNone(config_manager.db_config.get("port", None))
        self.assertIsNotNone(config_manager.db_config.get("url", None))
        self.assertIsNotNone(config_manager.db_config.get("username", None))
        self.assertIsNotNone(config_manager.db_config.get("password", None))
        self.assertIsNotNone(config_manager.db_config.get("db_type", None))

        self.assertIsNotNone(
            config_manager.actimetry_service_config.get("temp_directory", None)
        )
        self.assertIsNotNone(
            config_manager.actimetry_service_config.get("files_directory", None)
        )
