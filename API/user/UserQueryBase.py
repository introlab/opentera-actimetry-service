from flask_babel import gettext
from flask_restx import Resource
from opentera.modules.BaseModule import BaseModule


class UserQueryBase(Resource):

    def __init__(self, _api, *args, **kwargs):
        Resource.__init__(self, _api, *args, **kwargs)
        self.module: BaseModule = kwargs.get("flaskModule", None)
        self.test: bool = kwargs.get("test", False)
