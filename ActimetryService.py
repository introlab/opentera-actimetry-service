import argparse
import sys
import os

# SQLAlchemy
from sqlalchemy.exc import OperationalError

# Twisted
from twisted.internet import reactor, defer
from twisted.python import log

# OpenTera
from opentera.redis.RedisClient import RedisClient
from opentera.redis.RedisVars import RedisVars
from opentera.services.ServiceOpenTeraWithAssets import ServiceOpenTeraWithAssets
import opentera.messages.python as messages


from FlaskModule import FlaskModule, flask_app

import Globals
from ConfigManager import ConfigManager
from libactimetry.db.DBManager import DBManager
from libactimetry.workers.WorkerManager import WorkerManager


class ActimetryService(ServiceOpenTeraWithAssets):
    def __init__(self, config_man: ConfigManager, this_service_info):
        ServiceOpenTeraWithAssets.__init__(self, config_man, this_service_info)

        # Create REST backend
        self.flaskModule = FlaskModule(config_man, service=self)

        # Create twisted service
        self.flaskModuleService = self.flaskModule.create_service()

        # Get upload and temp directories (will create them if they do not exist)
        self.upload_directory = self.verify_file_upload_directory(config_man)
        self.temp_directory = self.verify_temp_directory(config_man)
        self.databases_directory = self.verify_databases_directory(config_man)

        self.init_service()

    def verify_file_upload_directory(self, config_man: ConfigManager, create: bool = True) -> str:
        """
        Verify that the file upload directory exists and is writable.
        If not, create it.
        """
        file_upload_directory = config_man.actimetry_service_config.get("files_directory", None)
        if not file_upload_directory:
            raise ValueError("File upload directory is not set in configuration.")

        if not os.path.exists(file_upload_directory):
            if create:
                os.makedirs(file_upload_directory)
            else:
                raise ValueError("File upload directory does not exist.")
        if not os.access(file_upload_directory, os.W_OK):
            raise ValueError("File upload directory is not writable.")
        return file_upload_directory

    def verify_temp_directory(self, config_man: ConfigManager, create: bool = True) -> str:
        """
        Verify that the temp directory exists and is writable.
        If not, create it.
        """
        temp_directory = config_man.actimetry_service_config.get("temp_directory", None)
        if not temp_directory:
            raise ValueError("Temp directory is not set in configuration.")
        if not os.path.exists(temp_directory):
            if create:
                os.makedirs(temp_directory)
            else:
                raise ValueError("Temp directory does not exist.")
        if not os.access(temp_directory, os.W_OK):
            raise ValueError("Temp directory is not writable.")
        return temp_directory

    def verify_databases_directory(self, config_man: ConfigManager, create: bool = True) -> str:
        """
        Verify that the databases directory exists and is writable.
        If not, create it.
        """
        databases_directory = config_man.actimetry_service_config.get("databases_directory", None)
        if not databases_directory:
            raise ValueError("Databases directory is not set in configuration.")
        if not os.path.exists(databases_directory):
            if create:
                os.makedirs(databases_directory)
            else:
                raise ValueError("Databases directory does not exist.")
        if not os.access(databases_directory, os.W_OK):
            raise ValueError("Databases directory is not writable.")
        return databases_directory

    def init_service(self):
        pass

    def notify_service_messages(self, pattern, channel, message):
        print("ActimetryService - notify_service_message", pattern, channel, message)

    def asset_event_received(self, event: messages.DatabaseEvent):
        if event.object_type == "asset":
            if event.type == messages.DatabaseEvent.DB_DELETE:
                asset_info = json.loads(event.object_value)
                # TODO Do something with the asset deletion from local database


if __name__ == "__main__":
    # Very first thing, log to stdout
    log.startLogging(sys.stdout)

    parser = argparse.ArgumentParser(description="Actimetry Service")
    parser.add_argument("--enable_tests", help="Test mode for service.", default=True)
    parser.add_argument("--conf", help="Configuration file", default="ActimetryService.json")
    args = parser.parse_args()

    # Load configuration
    if not Globals.config_man.load_config(args.conf):
        sys.stderr.write("Invalid config")
        sys.exit(1)

    # Global redis client
    Globals.redis_client = RedisClient(Globals.config_man.redis_config)

    # Register service if in test mode
    if args.enable_tests:
        # Make sure we register the service to OpenTera server
        from tools.create_actimetry_service import create_service

        """
        def create_service(username: str, password: str, server_url: str, service_key: str) -> bool:
        """
        if not create_service(
            "admin",
            "admin",
            f"https://{Globals.config_man.backend_config['hostname']}:{Globals.config_man.backend_config['port']}",
            "ActimetryService",
        ):
            sys.stderr.write("Error: Unable to create service on OpenTera Server")
            sys.exit(1)

    # Get service UUID
    service_info = Globals.redis_client.redisGet(
        RedisVars.RedisVar_ServicePrefixKey + Globals.config_man.service_config["name"]
    )

    if service_info is None:
        sys.stderr.write(
            "Error: Unable to get service info from OpenTera Server - is the server running and config "
            "correctly set in this service?"
        )
        sys.exit(1)

    import json

    service_info = json.loads(service_info)
    if "service_uuid" not in service_info:
        sys.stderr.write("OpenTera Server didn't return a valid service UUID - aborting.")
        sys.exit(1)

    # Update service uuid
    Globals.config_man.service_config["ServiceUUID"] = service_info["service_uuid"]

    # Update port, hostname, endpoint
    Globals.config_man.service_config["port"] = service_info["service_port"]
    Globals.config_man.service_config["hostname"] = service_info["service_hostname"]

    # DATABASE CONFIG AND OPENING
    #############################

    Globals.db_man = DBManager(app=flask_app)
    try:
        if args.enable_tests:
            Globals.db_man.open_local(None, echo=True, ram=True)
        else:
            POSTGRES = {
                "user": Globals.config_man.db_config["username"],
                "pw": Globals.config_man.db_config["password"],
                "db": Globals.config_man.db_config["name"],
                "host": Globals.config_man.db_config["url"],
                "port": Globals.config_man.db_config["port"],
            }
            Globals.db_man.open(POSTGRES, Globals.config_man.service_config["debug_mode"])

    except OperationalError as e:
        print("Unable to connect to database - please check settings in config file!", e)
        quit()

    # WORKER MANAGER
    Globals.worker_man = WorkerManager()

    with flask_app.app_context():
        # Create the Service
        Globals.service = ActimetryService(Globals.config_man, service_info)

        # Start App / reactor events
        reactor.run()
