from flask_babel import gettext
from flask_restx import Resource, inputs
from FlaskModule import user_api_ns as api
from opentera.services.ServiceAccessManager import (
    ServiceAccessManager,
    current_login_type,
    LoginType,
)
from libopenimu.algorithms.BaseAlgorithm import BaseAlgorithmFactory
from libactimetry.db.models.ActimetryDatabase import ActimetryDatabase

# Parser definition(s)
get_parser = api.parser()
get_parser.add_argument("key", type=str, help="Unique key (identifier) of the processing algorithm to query")
get_parser.add_argument(
    "list",
    type=inputs.boolean,
    help="Flag that limits the returned data to minimal information",
)
post_schema = api.schema_model("ActimetryDatabaseSchema", ActimetryDatabase.get_json_schema())


class UserQueryActimetryDatabase(Resource):
    """
    Query actimetry databases"""

    def __init__(self, _api, *args, **kwargs):
        Resource.__init__(self, _api, *args, **kwargs)
        self.module = kwargs.get("flaskModule", None)
        self.test = kwargs.get("test", False)

    @api.doc(
        description="Get available processing algorithms or details about a specific one. If no algorithm key is "
        "specified, returns all available processing algorithms.",
        responses={
            200: "Success - returns list of algorithms.",
            403: "Forbidden access",
            404: "Not found",
            500: "Database error",
        },
    )
    @api.expect(get_parser)
    @ServiceAccessManager.token_required(allow_static_tokens=False, allow_dynamic_tokens=True)
    def get(self):
        """
        Get processing algorithms information
        """
        args = get_parser.parse_args()

    @api.doc(
        description="Starts a new processing algorithm worker task",
        responses={
            200: "Success - Return information about started task",
            400: "Required parameter is missing",
            403: "Access denied to the requested task",
        },
    )
    @api.expect(post_schema, validate=True)
    @ServiceAccessManager.service_or_others_token_required(allow_dynamic_tokens=True, allow_static_tokens=False)
    def post(self):
        """
        Start a new worker task


        __tablename__ = "t_actimetry_databases"
        id_database = Column(Integer, Sequence('id_database_sequence'), primary_key=True, autoincrement=True)
        id_
        database_uuid = Column(String(36), nullable=False, unique=True)
        database_participant_uuid = Column(String(36), nullable=False)  # Participant to which the database is linked
        database_name = Column(String, nullable=False)
        database_type = Column(Integer, nullable=False, default=ActimetryDatabaseType.DATABASETYPE_OPENIMU)
        database_parameters = Column(JSON, nullable=True)  # Specific database parameter, such as connection settings, if needed
        database_datetime = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
        database_expiration_datetime = Column(TIMESTAMP(timezone=True), nullable=True)
        """
        pass
