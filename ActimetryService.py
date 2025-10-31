import argparse
import sys
import os

from datetime import datetime, timedelta
from typing import List

# SQLAlchemy
from sqlalchemy.exc import OperationalError

# Twisted
from twisted.internet import reactor, defer
from twisted.python import log
from twisted.internet import task

# OpenTera
from opentera.redis.RedisClient import RedisClient
from opentera.redis.RedisVars import RedisVars
from opentera.services.ServiceOpenTeraWithAssets import ServiceOpenTeraWithAssets
from opentera.modules.BaseModule import ModuleNames, create_module_event_topic_from_name
from opentera.db.models.TeraSession import TeraSessionStatus

import opentera.messages.python as messages


from FlaskModule import FlaskModule, flask_app

import Globals
from ConfigManager import ConfigManager
from libactimetry.db.DBManager import DBManager
from libactimetry.db.models.ActimetryAsset import ActimetryAsset
from libactimetry.db.models.ActimetryWorkerLog import WorkerOwnerType
from libactimetry.db.models.ActimetryDatabase import ActimetryDatabase, ActimetryDatabaseType
from libactimetry.workers.WorkerManager import WorkerManager
from libactimetry.db.models.ActimetryWorkerLog import WorkerStatus, WorkerType, ActimetryWorkerLog



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

        self.workers_task = task.LoopingCall(self.process_scheduled_workers)

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
        print("ActimetryService - Initializing service...")

        # We wait until we are connected to redis
        # Every 30 minutes?
        self.workers_task.start(20)

    def shutdown_service(self):
        print("ActimetryService - Shutting down service...")
        self.workers_task.stop()

    def process_scheduled_workers(self):
        print("ActimetryService - process_scheduled_workers")
        # We already are in a app_context ?
        with flask_app.app_context():
            # Get all scheduled workers from DB
            scheduled_workers : List[ActimetryWorkerLog] = ActimetryWorkerLog.query.filter_by(worker_status=WorkerStatus.STATUS_PLANNED.value).all()

            for scheduled_worker in scheduled_workers:
                print(f"ActimetryService - Starting scheduled worker {scheduled_worker.worker_uuid}")

                # Verify sheduled time if we can start it now
                current_time = datetime.now()

                if scheduled_worker.worker_start_time <= current_time:
                    # Start the worker depending on type
                    if scheduled_worker.worker_type == WorkerType.TYPE_ALGORITHM.value:
                        # Importer worker
                        print("ActimetryService - Starting scheduled algorithm worker")
                        # Get Parameters
                        parameters = json.loads(scheduled_worker.worker_parameters)

                        results = Globals.worker_man.start_processing_worker(
                            script=parameters.get('script', ''),
                            script_name=parameters.get('script_name', ''),
                            datapath=parameters.get('database_path', ''),
                            params=parameters.get('params', None),
                            owner_uuid=scheduled_worker.worker_owner_uuid,
                            owner_type=WorkerOwnerType(scheduled_worker.worker_owner_type),
                            database_id=scheduled_worker.id_database,
                            context=parameters.get('context', 'Unknown'),
                            worker_log=scheduled_worker
                        )

                        print(f"ActimetryService - Scheduled algorithm worker started: {results}")


    def notify_service_messages(self, pattern, channel, message):
        print("ActimetryService - notify_service_message", pattern, channel, message)

    @defer.inlineCallbacks
    def register_to_events(self):
        print('ActimetryService - Registering to events...')
        # Always register to assets events
        yield self.subscribe_pattern_with_callback(create_module_event_topic_from_name(
            ModuleNames.DATABASE_MODULE_NAME, 'session'), self.database_event_received)

        # Need to register to events (base class)
        super().register_to_events()

    def handle_database_event(self, event: messages.DatabaseEvent):
        super().handle_database_event(event)
        if event.object_type == 'session':
            if event.type == messages.DatabaseEvent.DB_UPDATE:
                # Session update
                session_info = json.loads(event.object_value)
                if session_info['session_status'] == TeraSessionStatus.STATUS_COMPLETED.value:
                    # Check if we have assets for that session
                    if not ActimetryAsset.collection_has_assets(session_info['id_session']):
                        return  # No assets for that session, so nothing to do!
                    # Process session only if status is completed
                    # Query participants for that session
                    response = self.get_from_opentera('/api/service/sessions',
                                                      {'id_session': session_info['id_session'],
                                                       'with_session_typo': True})
                    if response.status_code == 200:
                        session_details = response.json()
                        if len(session_details) > 0:
                            session_details = session_details[0]
                        if session_details:
                            if session_details['session_participants']:
                                # We have a least one participant in the session, start the import process
                                participant_info = session_details['session_participants'][0] # Use only the first one

                                # Check if we need to create a new empty database or not
                                database = ActimetryDatabase.get_for_participant(participant_info['participant_uuid'])
                                if not database:
                                    # Create new database
                                    database = ActimetryDatabase()
                                    # new_database.id_session = database_info["id_session"]
                                    database.database_participant_uuid = participant_info['participant_uuid']
                                    database.database_name = "OpenIMU - " + participant_info['participant_name']
                                    # Force OpenIMU type for now
                                    database.database_type = ActimetryDatabaseType.DATABASETYPE_OPENIMU.value
                                    database.database_parameters = None
                                    ActimetryDatabase.insert(database)

                                    # Create database file
                                    filename = os.path.join(
                                        self.config_man.actimetry_service_config["databases_directory"],
                                        database.database_uuid
                                    )
                                    os.makedirs(os.path.dirname(
                                        Globals.config_man.actimetry_service_config["databases_directory"]),
                                                exist_ok=True)

                                    ActimetryDatabase.create_openimu_database_file(filename, participant_info)

                                Globals.worker_man.start_openimu_importer_worker(
                                    participant_uuid=participant_info['participant_uuid'],
                                    participant_name=participant_info['participant_name'],
                                    base_assets_path=self.config_man.actimetry_service_config['files_directory'],
                                    id_collection=session_info['id_session'], owner_uuid=self.service_uuid,
                                    owner_type=WorkerOwnerType.OWNER_SERVICE
                                )

    def asset_event_received(self, event: messages.DatabaseEvent):
        if event.object_type == "asset":
            if event.type == messages.DatabaseEvent.DB_DELETE:
                asset_info = json.loads(event.object_value)
                # TODO Do something with the asset deletion from local database


if __name__ == "__main__":
    # Very first thing, log to stdout
    log.startLogging(sys.stdout)

    parser = argparse.ArgumentParser(description="Actimetry Service")
    parser.add_argument("--enable_tests", help="Test mode for service.", default=False)
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
    Globals.worker_man = WorkerManager(app=flask_app)

    with flask_app.app_context():
        # Create the Service
        Globals.service = ActimetryService(Globals.config_man, service_info)

        # Configure before shutdown on reactor
        reactor.addSystemEventTrigger('before', 'shutdown', Globals.service.shutdown_service)

        # Start App / reactor events
        reactor.run()
