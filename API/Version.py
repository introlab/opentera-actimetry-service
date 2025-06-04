from flask import request
from flask_babel import gettext
from flask_restx import Resource


from FlaskModule import service_api_ns as api
import Globals as Globals


from opentera.services.ServiceOpenTeraWithAssets import ServiceOpenTeraWithAssets
from opentera.modules.BaseModule import BaseModule

# Parser definition(s)
get_parser = api.parser()


class Version(Resource):

    def __init__(self, _api, *args, **kwargs):
        Resource.__init__(self, *args, **kwargs)
        self.flask_module: BaseModule = kwargs.get("flask_module", None)
        self.service: ServiceOpenTeraWithAssets = kwargs.get("service", None)
        self.test: bool = kwargs.get("test", False)

    @api.expect(get_parser, validate=True)
    @api.doc(
        description="Get service version",
        responses={
            200: "Success",
            500: "Internal error - service not initialized",
        },
    )
    def get(self):
        args = get_parser.parse_args(strict=True)

        if not self.service:
            return {"error": gettext("Service not initialized")}, 500

        return {
            "service_name": "service name",
            "version": "service_version",
            "test": self.test,
        }, 200
