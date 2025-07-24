import uuid
from io import BytesIO
import json
import requests
from requests import Response

from flask import Response as FlaskResponse
from flask import Flask
from flask_babel import Babel
import redis

import opentera.messages.python as messages
from opentera.modules.BaseModule import BaseModule
from opentera.services.ServiceOpenTeraWithAssets import ServiceOpenTeraWithAssets
from opentera.redis.RedisVars import RedisVars
from opentera.services.ServiceAccessManager import ServiceAccessManager

import Globals
from FlaskModule import FlaskModule, get_locale, get_timezone
from FlaskModule import CustomAPI, authorizations
from ConfigManager import ConfigManager


class FakeFlaskModule(BaseModule):
    def __init__(self, config: ConfigManager, flask_app, service):
        BaseModule.__init__(self, "FakeFlaskModule", config)

        self.flask_app = flask_app
        self.service = service
        self.api = CustomAPI(
            self.flask_app,
            version="1.0.0",
            title="FakeActimetryService API",
            description="FakeActimetryService API Documentation",
            doc="/doc",
            prefix="/api",
            authorizations=authorizations,
        )
        self.api_ns = self.api.namespace("", description="FakeActimetryService API")

        self.babel = Babel(
            self.flask_app,
            locale_selector=get_locale,
            timezone_selector=get_timezone,
            default_domain="opentera-surveyjs-service",
        )

        self.flask_app.debug = False
        self.flask_app.testing = True
        self.flask_app.secret_key = str(uuid.uuid4())  # Normally service UUID
        self.flask_app.config.update({"SESSION_TYPE": "redis"})
        redis_url = redis.from_url(
            "redis://%(username)s:%(password)s@%(hostname)s:%(port)s/%(db)s"
            % self.config.redis_config
        )

        self.flask_app.config.update({"SESSION_REDIS": redis_url})
        self.flask_app.config.update({"BABEL_DEFAULT_LOCALE": "fr"})
        self.flask_app.config.update({"SESSION_COOKIE_SECURE": True})
        self.flask_app.config.update({"UPLOAD_FOLDER": "."})

        # Disable flask cache
        self.flask_app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

        self.user_api_namespace = self.api.namespace('user', description='Fake Actimetry User API')
        self.participant_api_namespace = self.api.namespace('participant',
                                                            description='Fake Actimetry Participant API')
        self.device_api_namespace = self.api.namespace('device', description='Fake Actimetry Device API')

        self.setup_fake_actimetry_service_api(flask_app)
        self.setup_fake_user_api(flask_app)
        self.setup_fake_participant_api(flask_app)
        self.setup_fake_device_api(flask_app)

    def setup_fake_actimetry_service_api(self, flask_app):
        with flask_app.app_context():
            # Setup Fake Service API
            additional_args = {
                "test": True,
                "service": self.service,
                "flask_module": self,
            }
            FlaskModule.init_api(self.service, self, self.api_ns, additional_args)

    def setup_fake_user_api(self, flask_app):
        with flask_app.app_context():
            # Setup Fake API
            additional_args = {
                "test": True,
                "service": self.service,
                "flask_module": self,
            }

            # The trick is to initialize main server api to the newly created namespace
            FlaskModule.init_user_api(self, self.user_api_namespace, additional_args)

    def setup_fake_participant_api(self, flask_app):
        with flask_app.app_context():
            # Setup Fake API
            additional_args = {
                "test": True,
                "service": self.service,
                "flask_module": self,
            }

            # The trick is to initialize main server api to the newly created namespace
            FlaskModule.init_participant_api(self, self.participant_api_namespace, additional_args)

    def setup_fake_device_api(self, flask_app):
        with flask_app.app_context():
            # Setup Fake API
            additional_args = {
                "test": True,
                "service": self.service,
                "flask_module": self,
            }

            # The trick is to initialize main server api to the newly created namespace
            FlaskModule.init_device_api(self, self.device_api_namespace, additional_args)


class FakeActimetryService(ServiceOpenTeraWithAssets):
    """
    The only thing we want here is a way to simulate communication with the base server.
    We will simulate the service API with the database.
    """

    service_token = str()

    def __init__(self):
        self.flask_app = Flask("FakeActimetryService")
        self.config_man = ConfigManager()
        self.config_man.create_defaults()

        self.redis = redis.Redis(
            host=self.config_man.redis_config["hostname"],
            port=self.config_man.redis_config["port"],
            db=self.config_man.redis_config["db"],
            username=self.config_man.redis_config["username"],
            password=self.config_man.redis_config["password"],
            client_name=self.__class__.__name__,
        )

        # Will reinitialize the database and create the service
        self.reset_tera_server_database_and_create_service()
        self.setup_site_access_to_service(site_id=1)

        with self.flask_app.app_context():
            # In case we are running without opentera server running
            self.setup_service_access_manager()

            # Get service info from redis
            service_info = self.redis.get(
                RedisVars.RedisVar_ServicePrefixKey
                + self.config_man.service_config["service_key"]
            )

            # Create a fake uuid if not set in redis
            id_service = 1
            if service_info:
                service_info = json.loads(service_info)
                if "service_uuid" in service_info:
                    self.config_man.service_config["ServiceUUID"] = service_info[
                        "service_uuid"
                    ]
                    self.service_uuid = service_info["service_uuid"]
                if "id_service" in service_info:
                    id_service = service_info["id_service"]

            # Redis variables & db must be initialized before
            ServiceOpenTeraWithAssets.__init__(
                self,
                self.config_man,
                service_info
                # {
                #     "service_key": self.config_man.service_config["service_key"],
                #     "id_service": id_service,
                # },
            )
        # Setup modules
        self.flask_module = FakeFlaskModule(self.config_man, self.flask_app, self)

    def reset_tera_server_database_and_create_service(self):
        # Reset database
        server_url = f'https://{self.config_man.backend_config["hostname"]}:{self.config_man.backend_config["port"]}'
        response = requests.get(f"{server_url}/api/test/database/reset", verify=False)
        if response.status_code != 200:
            # TODO Raise exception
            pass

        # Create service
        from tools.create_actimetry_service import create_service

        service_infos = {}
        if not create_service(
            "admin", "admin", server_url, self.config_man.service_config["service_key"], service_infos
        ):
            # TODO Raise exception
            pass
        self.service_info = service_infos

    def setup_site_access_to_service(
        self, site_id: int, update_projects: bool = True
    ) -> bool:
        server_url = f'https://{self.config_man.backend_config["hostname"]}:{self.config_man.backend_config["port"]}'
        # Setup service for all sites and projects
        params = {"with_websocket": False}
        response = requests.get(
            f"{server_url}/api/user/login",
            auth=("admin", "admin"),
            params=params,
            verify=False,
        )
        if response.status_code == 200 and "user_token" in response.json():
            token = response.json()["user_token"]

            # Get Service id SurveyJSService
            params = {"service_key": "SurveyJSService"}
            response = self.get_from_opentera_with_token(
                token, "/api/user/services", params=params
            )
            if response.status_code == 200 and len(response.json()) > 0:
                service_info = response.json()[0]

                # Get site with site_id
                params = {"id_site": site_id}
                response = self.get_from_opentera_with_token(
                    token, "/api/user/sites", params=params
                )
                if response.status_code == 200 and len(response.json()) > 0:
                    site = response.json()[0]

                    # Add service to site
                    json_data = {
                        "service": {
                            "id_service": service_info["id_service"],
                            "sites": [site],
                        }
                    }
                    response = self.post_to_opentera_with_token(
                        token, "/api/user/services/sites", json_data=json_data
                    )
                    if response.status_code != 200:
                        # TODO Raise exception
                        pass

                    # Get all projects for this site
                    params = {"id_site": site_id}
                    response = self.get_from_opentera_with_token(
                        token, "/api/user/projects", params=params
                    )
                    if response.status_code == 200 and len(response.json()) > 0:
                        projects = response.json()

                        # Add service to all project (and sites...)
                        json_data = {
                            "service": {
                                "id_service": service_info["id_service"],
                                "projects": projects,
                            }
                        }
                        response = self.post_to_opentera_with_token(
                            token, "/api/user/services/projects", json_data=json_data
                        )
                        if response.status_code != 200:
                            # TODO Raise exception
                            pass

                        return True

        # Something went wrong
        return False

    def setup_service_access_manager(self):
        # Initialize service from redis, posing as FileTransferService
        # User token key (dynamic)
        if self.redis.get(RedisVars.RedisVar_UserTokenAPIKey) is None:
            ServiceAccessManager.api_user_token_key = str(uuid.uuid4())
            self.redis.set(
                RedisVars.RedisVar_UserTokenAPIKey,
                ServiceAccessManager.api_user_token_key,
            )

        # Participant token key from DB (static)
        if self.redis.get(RedisVars.RedisVar_ParticipantStaticTokenAPIKey) is None:
            ServiceAccessManager.api_participant_static_token_key = str(uuid.uuid4())
            self.redis.set(
                RedisVars.RedisVar_ParticipantStaticTokenAPIKey,
                ServiceAccessManager.api_participant_static_token_key,
            )

        # Participant token key (dynamic)
        if self.redis.get(RedisVars.RedisVar_ParticipantTokenAPIKey) is None:
            ServiceAccessManager.api_participant_token_key = str(uuid.uuid4())
            self.redis.set(
                RedisVars.RedisVar_ParticipantTokenAPIKey,
                ServiceAccessManager.api_participant_token_key,
            )

        # Device Token Key from DB (static)
        if self.redis.get(RedisVars.RedisVar_DeviceStaticTokenAPIKey) is None:
            ServiceAccessManager.api_device_static_token_key = str(uuid.uuid4())
            self.redis.set(
                RedisVars.RedisVar_DeviceStaticTokenAPIKey,
                ServiceAccessManager.api_device_static_token_key,
            )

        # Device Token Key (dynamic = static)
        if self.redis.get(RedisVars.RedisVar_DeviceTokenAPIKey) is None:
            ServiceAccessManager.api_device_token_key = str(uuid.uuid4())
            self.redis.set(
                RedisVars.RedisVar_DeviceTokenAPIKey,
                ServiceAccessManager.api_device_token_key,
            )

        # Service Token Key (dynamic)
        if self.redis.get(RedisVars.RedisVar_ServiceTokenAPIKey) is None:
            ServiceAccessManager.api_service_token_key = str(uuid.uuid4())
            self.redis.set(
                RedisVars.RedisVar_ServiceTokenAPIKey,
                ServiceAccessManager.api_service_token_key,
            )

    @staticmethod
    def convert_to_standard_request_response(flask_response: FlaskResponse):
        result = Response()
        result.status_code = flask_response.status_code
        result.headers = flask_response.headers
        result.encoding = flask_response.content_encoding
        result.raw = BytesIO(flask_response.data)
        return result

    def get_from_opentera_with_token(
        self, token: str, api_url: str, params: dict = {}, additional_headers: dict = {}
    ) -> Response:
        server_url = f'https://{self.config_man.backend_config["hostname"]}:{self.config_man.backend_config["port"]}'
        headers = {"Authorization": f"OpenTera {token}"}
        headers.update(additional_headers)
        return requests.get(
            f"{server_url}{api_url}", headers=headers, params=params, verify=False
        )

    def post_to_opentera_with_token(
        self,
        token: str,
        api_url: str,
        json_data: dict,
        params: dict = {},
        additional_headers: dict = {},
    ) -> Response:
        headers = {"Authorization": f"OpenTera {token}"}
        headers.update(additional_headers)
        server_url = f'https://{self.config_man.backend_config["hostname"]}:{self.config_man.backend_config["port"]}'
        return requests.post(
            f"{server_url}{api_url}",
            headers=headers,
            json=json_data,
            params=params,
            verify=False,
        )

    def delete_from_opentera_with_token(
        self, token: str, api_url: str, params: dict = None, additional_headers: dict = None
    ) -> Response:
        headers = {"Authorization": f"OpenTera {token}"}
        if additional_headers:
            headers.update(additional_headers)
        server_url = f'https://{self.config_man.backend_config["hostname"]}:{self.config_man.backend_config["port"]}'
        return requests.delete(
            f"{server_url}{api_url}", headers=headers, params=params, verify=False
        )

    def asset_event_received(self, event: messages.DatabaseEvent):
        pass


if __name__ == "__main__":
    service = FakeActimetryService()
    with service.flask_app.app_context():
        pass
