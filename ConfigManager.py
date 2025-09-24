from opentera.services.ServiceConfigManager import ServiceConfigManager, DBConfig


class ActimetryServiceConfig:
    actimetry_service_config = {}

    def __init__(self):
        pass

    def validate_actimetry_service_config(self, config: dict):
        if "ActimetryService" in config:
            required_fields = ["temp_directory", "files_directory", "databases_directory"]
            for field in required_fields:
                if field not in config["ActimetryService"]:
                    print("ERROR: ActimetryService Config - missing field :" + field)
                    return False

            # Every field is present, update configuration
            self.actimetry_service_config = config["ActimetryService"]
            return True
        # Invalid
        return False


# Build configuration from base classes
class ConfigManager(ServiceConfigManager, ActimetryServiceConfig, DBConfig):
    def validate_config(self, config_json):
        return (
            super().validate_config(config_json)
            and self.validate_service_config(config_json)
            and self.validate_actimetry_service_config(config_json)
            and self.validate_database_config(config_json)
        )

    def create_defaults(self):
        # Default service config
        self.service_config["name"] = "ActimetryService"
        self.service_config["hostname"] = "127.0.0.1"
        self.service_config["port"] = 4088
        self.service_config["debug_mode"] = True
        self.service_config["service_key"] = "ActimetryService"
        self.service_config["ServiceUUID"] = "00000000-0000-0000-0000-000000000002"

        # Default backend configuration
        self.backend_config["hostname"] = "127.0.0.1"
        self.backend_config["port"] = 40075

        # Default redis configuration
        self.redis_config["hostname"] = "127.0.0.1"
        self.redis_config["port"] = 6379
        self.redis_config["username"] = ""
        self.redis_config["password"] = ""
        self.redis_config["db"] = 0

        # Default database configuration
        self.db_config["name"] = "opentera"
        self.db_config["port"] = 5432
        self.db_config["url"] = "localhost"
        self.db_config["username"] = "opentera"
        self.db_config["password"] = "opentera"
        self.db_config["db_type"] = "sqlite"

        # Default actimetry service configuration
        self.actimetry_service_config["temp_directory"] = "/tmp/actimetry"
        self.actimetry_service_config["files_directory"] = "files"
        self.actimetry_service_config["databases_directory"] = "files/databases"
