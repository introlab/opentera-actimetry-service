from flask import request
from flask_babel import gettext
from FlaskModule import user_api_ns as api
from opentera.services.ServiceAccessManager import (
    ServiceAccessManager,
    current_login_type,
    LoginType,
    current_user_client,
)
from libactimetry.db.models.ActimetryWorkerLog import ActimetryWorkerLog, WorkerOwnerType, WorkerStatus
from libactimetry.db.models.ActimetryDatabase import ActimetryDatabase

from libopenimu.algorithms.BaseAlgorithm import BaseAlgorithmFactory

import Globals as Globals
from API.user.UserQueryBase import UserQueryBase
import os

# Parser definition(s)
get_parser = api.parser()
get_parser.add_argument("uuid", type=str, help="UUID of the worker task to query", required=True)
# get_parser.add_argument('key', type=str, help='Unique key (identifier) of the processing algorithm to use')
# get_parser.add_argument('participant_uuid', type=str, help='Participant UUID to use algorithm on')
# get_parser.add_argument('parameters', type=str, help='Parameters to use with the processing algorithm')

post_schema = api.schema_model(
    "worker",
    {
        "properties": {
            "key": {"type": "string", "location": "json"},
            "participant_uuid": {"type": "string", "location": "json"},
            "parameters": {"type": "string", "location": "json"},
        }
    },
)


class UserQueryActimetryProcessing(UserQueryBase):

    def __init__(self, _api, *args, **kwargs):
        UserQueryBase.__init__(self, _api, *args, **kwargs)

    @api.doc(
        description="Get the status of a processing algorithm worker task",
        responses={200: "Success - returns status.", 403: "Forbidden access", 404: "Not found", 500: "Database error"},
    )
    @api.expect(get_parser)
    @ServiceAccessManager.token_required(allow_static_tokens=False, allow_dynamic_tokens=True)
    def get(self):
        """
        Get worker status for the specified id
        """
        if current_login_type != LoginType.USER_LOGIN:
            return gettext("Invalid login type"), 403

        args = get_parser.parse_args()

        # TODO Handle querying list of all worker logs

        # Query specific worker log
        log: ActimetryWorkerLog = ActimetryWorkerLog.get_log_for_worker(args["uuid"])

        if log is None:
            return gettext("Forbidden access to that worker"), 403

        # Check if current user can access the status of that log
        if not current_user_client.user_superadmin:
            # TODO Allow access to accessible participants logs
            # TODO Allow access to accessible device logs
            # TODO Allow access to accessible service logs
            if (
                log.worker_owner_type != WorkerOwnerType.OWNER_USER.value
                or log.worker_owner_uuid != current_user_client.user_uuid
            ):
                return gettext("Forbidden access to that worker"), 403

        # All good ! Return status
        return log.to_json(), 200

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
        if current_login_type != LoginType.USER_LOGIN:
            return gettext("Invalid login type"), 403

        json_worker = request.json["worker"]

        # Validate key against known algorithms
        known_algos = [factory.unique_key() for factory in BaseAlgorithmFactory.factories]
        # known_algos = ["evenson2008", "freedson1998"]
        if self.test:
            known_algos.append('Test')

        if json_worker["key"] not in known_algos:
            return gettext("Invalid algorithm key"), 400

        # Check if user has access to specific participant
        participant = current_user_client.do_get_request_to_backend(
            path="/api/user/participants", params={"participant_uuid": json_worker["participant_uuid"]}
        )
        if not participant.json():
            return gettext("Forbidden access to the participant"), 403

        # Check if there's already a database created for that participant.
        database = ActimetryDatabase.get_for_participant(json_worker["participant_uuid"])
        if database is None:
            return gettext("No database for specified participant"), 400

        # Ok, start worker now!
        script_name = (
            "workers/algorithms/" + json_worker["key"] + "Worker.py"
        )  # TODO: Another way to find algorithms scripts?
        database_path = (
            Globals.service.config_man.actimetry_service_config["databases_directory"] + os.sep + database.database_uuid
        )
        (work_uuid, worker_status) = Globals.worker_man.start_processing_worker(
            script=script_name,
            datapath=database_path,
            owner_type=WorkerOwnerType.OWNER_USER,
            owner_uuid=current_user_client.user_uuid,
            params=json_worker["parameters"],
            database_id=database.id_database,
        )

        return {"work_uuid": work_uuid, "status": worker_status.value}, 200
