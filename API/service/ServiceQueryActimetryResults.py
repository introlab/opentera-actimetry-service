import os
import json
from flask_babel import gettext
from flask_restx import Resource, inputs
from flask import request
from FlaskModule import user_api_ns as api
from json import JSONDecodeError
from jsonschema import validate, ValidationError
from jsonschema.exceptions import SchemaError
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy import exc
from opentera.services.ServiceAccessManager import (
    ServiceAccessManager,
    current_login_type,
    current_service_client,
    LoginType,
)
from werkzeug.exceptions import BadRequest
from opentera.modules.BaseModule import BaseModule
from libopenimu.algorithms.BaseAlgorithm import BaseAlgorithmFactory
from libactimetry.db.models.ActimetryDatabase import ActimetryDatabase, ActimetryDatabaseType
from API.service.ServiceQueryBase import ServiceQueryBase
import Globals as Globals
from libopenimu.db.DBManager import DBManager as OpenIMUDBManager
from libopenimu.models.Participant import Participant as OpenIMUParticipant

# Parser definition(s)
get_parser = api.parser()
get_parser.add_argument("id_database", type=int, help="database id", required=False, default=None)
get_parser.add_argument("database_uuid", type=str, help="database uuid", required=False, default=None)
get_parser.add_argument(
    "database_participant_uuid", type=str, help="database participant uuid", required=False, default=None
)


class ServiceQueryActimetryResults(ServiceQueryBase):
    """
    Query actimetry database results
    """

    def __init__(self, _api, *args, **kwargs):
        ServiceQueryBase.__init__(self, _api, *args, **kwargs)

    @api.doc(
        description="Get all available result from DB for a specific participant.",
        responses={
            200: "Success - returns database results.",
            403: "Forbidden access",
            404: "Not found",
            500: "Database error",
        },
    )
    @api.expect(get_parser)
    @ServiceAccessManager.service_token_required
    def get(self):
        """
        Get database informations
        """
        if not current_service_client or current_login_type not in [LoginType.SERVICE_LOGIN]:
            return gettext("Access denied"), 403

        try:
            # Parse arguments
            args = get_parser.parse_args(strict=True)
            # Verify if any args were provided
            if not any(args.values()):
                return gettext("At least one parameter must be provided"), 400

            database = None

            # if id_database is provided, return that database
            if args["id_database"] is not None:
                database = ActimetryDatabase.get_by_id(args["id_database"])
                if not database:
                    return gettext("No database found"), 404
                if not self._verify_participant_access(database.database_participant_uuid):
                    return gettext("Access denied to that database"), 403
            # if database_uuid is provided, return that database
            elif args["database_uuid"] is not None:
                database = ActimetryDatabase.get_by_uuid(args["database_uuid"])
                if not database:
                    return gettext("No database found"), 404
                if not self._verify_participant_access(database.database_participant_uuid):
                    return gettext("Access denied to that database"), 403
            # if database_participant_uuid is provided, return the database for the participant
            elif args["database_participant_uuid"] is not None:
                database = ActimetryDatabase.get_for_participant(args["database_participant_uuid"])
                if not database:
                    return gettext("No database found for participant"), 404
                if not self._verify_participant_access(database.database_participant_uuid):
                    return gettext("Access denied to that database"), 403

            if not database:
                return gettext("No database found"), 404

            try:
                # Get information about the database, need to open the sqlite file
                database_folder = Globals.config_man.actimetry_service_config["databases_directory"]
                database_file = os.path.join(database_folder, database.database_uuid)
                if not os.path.exists(database_file):
                    return gettext("Database file not found"), 500

                # Open database file
                dbman = OpenIMUDBManager(database_file, overwrite=False, echo=False, newfile=False)

                # Get results
                all_processed_data = dbman.get_all_processed_data()
                """
                    id_processed_data = Column(Integer, Sequence('id_processed_data_sequence'), primary_key=True, autoincrement=True)
                    id_data_processor = Column(Integer, nullable=False)
                    name = Column(String, nullable=False)
                    data = Column(BLOB, nullable=False)
                    params = Column(String, nullable=True)
                    processed_time = Column(TIMESTAMP, nullable=False)
                """
                results = []

                # We assume here data is JSON encoded in the BLOB
                # We also assume params is JSON encoded in the string

                # TODO Validate data and params with JSON schema from the algorithm
                for processed_data in all_processed_data:
                    try:
                        result = {
                            "id_processed_data": processed_data.id_processed_data,
                            "id_data_processor": processed_data.id_data_processor,
                            "name": processed_data.name,
                            "data": json.loads(processed_data.data.decode("utf-8")),
                            "params": json.loads(processed_data.params) if processed_data.params else None,
                            "processed_time": (
                                processed_data.processed_time.isoformat() if processed_data.processed_time else None
                            ),
                        }
                        results.append(result)
                    except (JSONDecodeError, TypeError) as e:
                        # If data is not valid JSON, skip this entry
                        continue
                dbman.close()
                return results, 200

            except Exception as e:
                return gettext("Error opening database: ") + str(e), 500

        except BadRequest as e:
            return gettext("Invalid parameter: ") + str(e), 400
