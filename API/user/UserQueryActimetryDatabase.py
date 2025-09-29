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

post_schema = api.schema_model("ActimetryDatabaseSchema", ActimetryDatabase.get_json_schema())


delete_parser = api.parser()
delete_parser.add_argument("id_database", type=int, help="database id", required=True)


class UserQueryActimetryDatabase(UserQueryBase):
    """
    Query actimetry databases"""

    def __init__(self, _api, *args, **kwargs):
        UserQueryBase.__init__(self, _api, *args, **kwargs)

    @api.doc(
        description="Get available actimetry databases or details about a specific one. If no database key is "
        "specified, returns all available actimetry databases.",
        responses={
            200: "Success - returns database information.",
            403: "Forbidden access",
            404: "Not found",
            500: "Database error",
        },
    )
    @api.expect(get_parser)
    @ServiceAccessManager.token_required(allow_static_tokens=False, allow_dynamic_tokens=True)
    def get(self):
        """
        Get database information
        """
        if not current_user_client or current_login_type not in [LoginType.USER_LOGIN]:
            return gettext("Access denied"), 403

        try:
            # Parse arguments
            args = get_parser.parse_args(strict=True)
            # Verify if any args were provided
            if not any(args.values()):
                return gettext("At least one parameter must be provided"), 400

            # if id_database is provided, return that database
            if args["id_database"] is not None:
                database = ActimetryDatabase.get_by_id(args["id_database"])
                if not database:
                    return gettext("No database found"), 404
                if not self._verify_session_access(database.id_session):
                    return gettext("Access denied to that database"), 403
                return database.to_json(), 200
            # if database_uuid is provided, return that database
            elif args["database_uuid"] is not None:
                database = ActimetryDatabase.get_by_uuid(args["database_uuid"])
                if not database:
                    return gettext("No database found"), 404
                if not self._verify_session_access(database.id_session):
                    return gettext("Access denied to that database"), 403
                return database.to_json(), 200
            # if database_participant_uuid is provided, return the database for the participant
            elif args["database_participant_uuid"] is not None:
                participant_info = self._get_participant_info(args["database_participant_uuid"])
                if not participant_info:
                    return gettext("No access to participant"), 403
                database = ActimetryDatabase.get_for_participant(args["database_participant_uuid"])
                if not database:
                    return gettext("No database found for participant"), 404
                return database.to_json(), 200
        except BadRequest as e:
            return gettext("Invalid parameter: ") + str(e), 400

    @api.doc(
        description="Create or update an actimetry database",
        responses={
            200: "Success - Return information about the database created or updated",
            400: "Required parameter is missing",
            403: "Access denied to the requested database",
        },
    )
    @api.expect(post_schema)
    @ServiceAccessManager.token_required(allow_dynamic_tokens=True, allow_static_tokens=False)
    def post(self):
        """
        Create or update an actimetry database


        __tablename__ = "t_actimetry_databases"
        id_database = Column(Integer, Sequence('id_database_sequence'), primary_key=True, autoincrement=True)
        id_session = Column(Integer, nullable=False)
        database_uuid = Column(String(36), nullable=False, unique=True)
        database_participant_uuid = Column(String(36), nullable=False)  # Participant to which the database is linked
        database_name = Column(String, nullable=False)
        database_type = Column(Integer, nullable=False, default=ActimetryDatabaseType.DATABASETYPE_OPENIMU)
        database_parameters = Column(JSON, nullable=True)  # Specific database parameter, such as connection settings, if needed
        database_datetime = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
        database_expiration_datetime = Column(TIMESTAMP(timezone=True), nullable=True)
        """
        if not current_user_client or current_login_type not in [LoginType.USER_LOGIN]:
            return gettext("Access denied"), 403

        try:
            # Validate JSON schema first
            post_schema.validate(request.json)

            # Validate access to session first
            database_info = request.json["database"]
            if "id_session" not in database_info:
                return gettext("Missing session ID"), 400
            if not self._verify_session_access(database_info["id_session"]):
                return gettext("Access denied to that session"), 403

            # Validate access to participant
            if "database_participant_uuid" not in database_info:
                return gettext("Missing participant UUID"), 400

            participant_info = self._get_participant_info(database_info["database_participant_uuid"])
            if not participant_info:
                return gettext("No access to participant"), 403

            # Check if we are creating a new database or updating an existing one
            if database_info["id_database"] == 0:
                # Create new database
                new_database = ActimetryDatabase()
                new_database.id_session = database_info["id_session"]
                new_database.database_participant_uuid = database_info["database_participant_uuid"]
                new_database.database_name = database_info["database_name"]
                # Force OpenIMU type for now
                new_database.database_type = ActimetryDatabaseType.DATABASETYPE_OPENIMU.value
                new_database.database_parameters = database_info.get("database_parameters", None)
                ActimetryDatabase.insert(new_database)

                # Create database file
                filename = os.path.join(
                    Globals.config_man.actimetry_service_config["databases_directory"], new_database.database_uuid
                )

                # OpenIMU database creation
                if new_database.database_type == ActimetryDatabaseType.DATABASETYPE_OPENIMU.value:
                    manager: OpenIMUDBManager = OpenIMUDBManager(filename, overwrite=False, echo=False, newfile=True)
                    # Create participant
                    participant = OpenIMUParticipant()
                    participant.name = participant_info["participant_name"]
                    participant.description = json.dumps(participant_info)
                    # Commit to DB
                    manager.session.add(participant)
                    manager.session.commit()

                else:
                    return gettext("Unsupported database type"), 400

                return new_database.to_json(), 200

        except KeyError as e:
            return gettext("Required parameter is missing"), 400
        except ValidationError as e:
            return gettext("Invalid JSON structure"), 400
        except SchemaError as e:
            return gettext("Invalid JSON schema"), 400
        except JSONDecodeError as e:
            return gettext("Invalid JSON"), 400
        except exc.SQLAlchemyError as e:
            if self.module:
                self.module.logger.log_error(
                    self.module.module_name, UserQueryActimetryDatabase.__name__, "post", 500, "Database error", str(e)
                )
            return gettext("Database error"), 500

        return {}, 200

    @api.doc(
        description="Delete an actimetry database",
        responses={
            200: "Success - Database deleted",
            400: "Required parameter is missing",
            403: "Access denied to the requested database",
        },
    )
    @api.expect(delete_parser)
    @ServiceAccessManager.token_required(allow_dynamic_tokens=True, allow_static_tokens=False)
    def delete(self):
        """
        Delete an actimetry database
        """
        if not current_user_client or current_login_type not in [LoginType.USER_LOGIN]:
            return gettext("Access denied"), 403

        try:
            # Parse arguments
            args = delete_parser.parse_args(strict=True)

            # Get database to delete
            database = ActimetryDatabase.get_by_id(args["id_database"])
            if not database:
                return gettext("No database found"), 404
            if not self._verify_session_access(database.id_session):
                return gettext("Access denied to that database"), 403

            # Delete database file and entry
            database_folder = Globals.config_man.actimetry_service_config["databases_directory"]
            if database.delete_actimetry_database(database_folder):
                return {}, 200
            else:
                return gettext("Error deleting database"), 500

        except KeyError as e:
            return gettext("Required parameter is missing"), 400
        except ValidationError as e:
            return gettext("Invalid JSON structure"), 400
        except SchemaError as e:
            return gettext("Invalid JSON schema"), 400
        except JSONDecodeError as e:
            return gettext("Invalid JSON"), 400
        except exc.SQLAlchemyError as e:
            if self.module:
                self.module.logger.log_error(
                    self.module.module_name,
                    UserQueryActimetryDatabase.__name__,
                    "delete",
                    500,
                    "Database error",
                    str(e),
                )
            return gettext("Database error"), 500
