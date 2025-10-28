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
    current_user_client,
    LoginType,
)
from werkzeug.exceptions import BadRequest
from opentera.modules.BaseModule import BaseModule
from libopenimu.algorithms.BaseAlgorithm import BaseAlgorithmFactory
from libactimetry.db.models.ActimetryDatabase import ActimetryDatabase, ActimetryDatabaseType
from API.user.UserQueryBase import UserQueryBase
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


class UserQueryActimetryDatabaseInfos(UserQueryBase):
    """
    Query actimetry database informations
    """

    def __init__(self, _api, *args, **kwargs):
        UserQueryBase.__init__(self, _api, *args, **kwargs)

    @api.doc(
        description="Get available actimetry database informations or details about a specific one. If no database key is "
        "specified, returns all available actimetry databases.",
        responses={
            200: "Success - returns database informations.",
            403: "Forbidden access",
            404: "Not found",
            500: "Database error",
        },
    )
    @api.expect(get_parser)
    @ServiceAccessManager.token_required(allow_static_tokens=False, allow_dynamic_tokens=True)
    def get(self):
        """
        Get database informations
        """
        if not current_user_client or current_login_type not in [LoginType.USER_LOGIN]:
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
                participant_info = self._get_participant_info(args["database_participant_uuid"])
                if not participant_info:
                    return gettext("No access to participant"), 403
                database = ActimetryDatabase.get_for_participant(args["database_participant_uuid"])
                if not database:
                    return gettext("No database found for participant"), 404

            if not database:
                return gettext("No database found"), 404

            try:
                # Get information about the database, need to open the sqlite file
                database_folder = Globals.config_man.actimetry_service_config["databases_directory"]
                database_file = os.path.join(database_folder, database.database_uuid)
                if not os.path.exists(database_file):
                    return gettext("Database file not found"), 500

                # Get file size
                file_size = os.path.getsize(database_file)

                dbman = OpenIMUDBManager(database_file, overwrite=False, echo=False, newfile=False)

                # Dataset information
                dataset = dbman.get_dataset()
                """
                    name = Column(String, nullable=False, primary_key=True)
                    description = Column(String)
                    creation_date = Column(TIMESTAMP, nullable=False)
                    upload_date = Column(TIMESTAMP, nullable=False)
                    author = Column(String, nullable=False)
                """
                dataset_info = (
                    {
                        "name": dataset.name,
                        "description": dataset.description,
                        "creation_date": str(dataset.creation_date),
                        "upload_date": str(dataset.upload_date),
                        "author": dataset.author,
                    }
                    if dataset
                    else {}
                )

                # Recordsets information
                recordsets = dbman.get_all_recordsets()
                """
                id_recordset = Column(Integer, Sequence('id_recordset_sequence'), primary_key=True, autoincrement=True)
                id_participant = Column(Integer, ForeignKey('tabParticipants.id_participant', ondelete="CASCADE"), nullable=False)
                name = Column(String, nullable=False)

                '''
                A type for datetime.timedelta() objects.
                The Interval type deals with datetime.timedelta objects. In PostgreSQL, the native INTERVAL type is used;
                for others, the value is stored as a date which is relative to the “epoch” (Jan. 1, 1970).
                '''
                start_timestamp = Column(TIMESTAMP, nullable=False)
                end_timestamp = Column(TIMESTAMP, nullable=False)

                # Relationships
                participant = relationship("Participant")

                """
                recordsets_info = []
                for recordset in recordsets:
                    recordsets_info.append(
                        {
                            "id_recordset": recordset.id_recordset,
                            "id_participant": recordset.id_participant,
                            "name": recordset.name,
                            "start_timestamp": str(recordset.start_timestamp),
                            "end_timestamp": str(recordset.end_timestamp),
                        }
                    )
                dbman.close()

                return {"file_size": file_size, "dataset_info": dataset_info, "recordsets_info": recordsets_info}, 200

            except Exception as e:
                return gettext("Error opening database: ") + str(e), 500

        except BadRequest as e:
            return gettext("Invalid parameter: ") + str(e), 400
