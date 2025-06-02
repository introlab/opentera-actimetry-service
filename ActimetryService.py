import argparse
import sys
import json

# SQLAlchemy
from sqlalchemy.exc import OperationalError

# Twisted
from twisted.internet import reactor, defer
from twisted.python import log

from requests import get, post, delete, Response

# OpenTera
from opentera.redis.RedisClient import RedisClient
from opentera.redis.RedisVars import RedisVars
from opentera.services.ServiceOpenTeraWithTests import ServiceOpenTeraWithTests
import opentera.messages.python as messages


from FlaskModule import FlaskModule, flask_app

import Globals
from ConfigManager import ConfigManager
from libsurveyjs.db.DBManager import DBManager
from libsurveyjs.db.models.SurveyResults import SurveyResults
from libsurveyjs.db.models.ActiveSurvey import ActiveSurvey


class SurveyJSService(ServiceOpenTeraWithTests):
    def __init__(self, config_man: ConfigManager, this_service_info):
        # Not useful, BaseWebRTCService will initialize the service properly...
        ServiceOpenTeraWithTests.__init__(self, config_man, this_service_info)

        # Create REST backend
        self.flaskModule = FlaskModule(config_man, service=self)

        # Create twisted service
        self.flaskModuleService = self.flaskModule.create_service()

        self.init_service()

    def init_service(self):
        pass

    def notify_service_messages(self, pattern, channel, message):
        print('SurveyJSService - notify_service_message', pattern, channel, message)

    def test_event_received(self, event: messages.DatabaseEvent):
        """
        We receive an event from teraserver when a test is created / updated / deleted.
        Remove associated survey results if it exists.
        """
        if event.type == messages.DatabaseEvent.DB_DELETE:
            print('SurveyJSService - test_event_received - Test deleted:', event.object_type, event.object_value)
            test_info = json.loads(event.object_value)
            test_uuid = test_info['test_uuid']
            with flask_app.app_context():
                survey_results = SurveyResults.get_survey_results_by_test_uuid(test_uuid)
                if survey_results:
                    SurveyResults.delete(survey_results.id_survey_results)


    def test_type_event_received(self, event: messages.DatabaseEvent):
        """
        We receive an avent from teraserver when a test_type is created / updated / deleted
        Remove associated Active Survey if it exists.
        """
        if event.type == messages.DatabaseEvent.DB_DELETE :
            print('SurveyJSService - test_type_event_received - TestType deleted:', event.object_type, event.object_value)
            test_type_info = json.loads(event.object_value)
            test_type_uuid = test_type_info['test_type_uuid'] if 'test_type_uuid' in test_type_info else None
            with flask_app.app_context():
                active_survey: ActiveSurvey = ActiveSurvey.get_active_survey_by_test_type_uuid(test_type_uuid)
                if active_survey:
                    ActiveSurvey.delete(active_survey.id_active_survey)
        elif event.type == messages.DatabaseEvent.DB_UPDATE :
            print('SurveyJSService - test_type_event_received - TestType updated:', event.object_type, event.object_value)
            test_type_info = json.loads(event.object_value)
            test_type_uuid = test_type_info['test_type_uuid'] if 'test_type_uuid' in test_type_info else None
            with flask_app.app_context():
                active_survey : ActiveSurvey = ActiveSurvey.get_active_survey_by_test_type_uuid(test_type_uuid)
                if active_survey:
                    # Update the survey name if it exists
                    update_data = {}
                    if 'test_type_name' in test_type_info and active_survey.active_survey_name != test_type_info['test_type_name']:
                        update_data['active_survey_name'] = test_type_info['test_type_name']
                    if 'test_type_description' in test_type_info and active_survey.active_survey_description != test_type_info['test_type_description']:
                        update_data['active_survey_description'] = test_type_info['test_type_description']

                    if update_data:
                        # Modification date will be updated automatically
                        ActiveSurvey.update(active_survey.id_active_survey, update_data)


    def register_to_events(self):
        """
        ServiceOpenTeraWithTests registers to DB to events for test and test_types.
        test_event_received will be called when a test is created / updated / deleted
        test_type_event_received will be called when a testtype is created / updated / deleted
        """
        ServiceOpenTeraWithTests.register_to_events(self)

    def unregister_to_events(self):
        """
        ServiceOpenTeraWithTests unregisters to DB to events for test and test_types.
        """
        ServiceOpenTeraWithTests.unregister_to_events(self)

    def get_from_opentera_with_token(self, token: str, api_url: str, params: dict = {},
                                     additional_headers: dict = {}) -> Response:
        """
        TODO: Remove from this implementation and use the base class implementation when available in next release.
        """
        request_headers = {'Authorization': 'OpenTera ' + token}
        request_headers.update(additional_headers)
        backend_url = f"https://{self.config_man.backend_config['hostname']}:{self.config_man.backend_config['port']}"
        # TODO fix verify=False
        backend_response = get(url=backend_url + api_url, headers=request_headers, params=params, verify=False)
        return backend_response

    def post_to_opentera_with_token(self, token: str,  api_url: str, json_data: dict, params: dict = {},
                                    additional_headers: dict = {}) -> Response:
        """
        TODO: Remove from this implementation and use the base class implementation when available in next release.
        """
        request_headers = {'Authorization': 'OpenTera ' + token}
        request_headers.update(additional_headers)
        backend_url = f"https://{self.config_man.backend_config['hostname']}:{self.config_man.backend_config['port']}"
        # TODO fix verify=False
        backend_response = post(url=backend_url + api_url, headers=request_headers, json=json_data, params=params, verify=False)

    def delete_from_opentera_with_token(self, token: str, api_url: str, params: dict,
                                        additional_headers: dict = {}) -> Response:
        """
        TODO: Remove from this implementation and use the base class implementation when available in next release.
        """
        request_headers = {'Authorization': 'OpenTera ' + token}
        request_headers.update(additional_headers)
        backend_url = f"https://{self.config_man.backend_config['hostname']}:{self.config_man.backend_config['port']}"
        # TODO fix verify=False
        backend_response = delete(url=backend_url + api_url, headers=request_headers, params=params, verify=False)
        return backend_response


if __name__ == '__main__':
    # Very first thing, log to stdout
    log.startLogging(sys.stdout)

    parser = argparse.ArgumentParser(description='SurveyJS Service')
    parser.add_argument('--enable_tests', help='Test mode for service.', default=False)
    parser.add_argument('--conf', help='Configuration file', default='SurveyJSService.json')
    args = parser.parse_args()

    # Load configuration
    if not Globals.config_man.load_config(args.conf):
        sys.stderr.write('Invalid config')
        sys.exit(1)

    # Global redis client
    Globals.redis_client = RedisClient(Globals.config_man.redis_config)

    # Register service if in test mode
    if args.enable_tests:
        # Make sure we register the service to OpenTera server
        from tools.create_surveyjs_service import create_service
        """
        def create_service(username: str, password: str, server_url: str, service_key: str) -> bool:
        """
        if not create_service('admin', 'admin',
                              f"https://{Globals.config_man.backend_config['hostname']}:{Globals.config_man.backend_config['port']}",
                              'SurveyJSService'):
            sys.stderr.write('Error: Unable to create service on OpenTera Server')
            sys.exit(1)

    # Get service UUID
    service_info = Globals.redis_client.redisGet(RedisVars.RedisVar_ServicePrefixKey +
                                                 Globals.config_man.service_config['name'])

    if service_info is None:
        sys.stderr.write('Error: Unable to get service info from OpenTera Server - is the server running and config '
                         'correctly set in this service?')
        sys.exit(1)

    import json
    service_info = json.loads(service_info)
    if 'service_uuid' not in service_info:
        sys.stderr.write('OpenTera Server didn\'t return a valid service UUID - aborting.')
        sys.exit(1)

    # Update service uuid
    Globals.config_man.service_config['ServiceUUID'] = service_info['service_uuid']

    # Update port, hostname, endpoint
    Globals.config_man.service_config['port'] = service_info['service_port']
    Globals.config_man.service_config['hostname'] = service_info['service_hostname']

    # DATABASE CONFIG AND OPENING
    #############################

    Globals.db_man = DBManager(app=flask_app)
    try:
        if args.enable_tests:
            Globals.db_man.open_local(None, echo=True, ram=True)
        else:
            POSTGRES = {
                'user': Globals.config_man.db_config['username'],
                'pw': Globals.config_man.db_config['password'],
                'db': Globals.config_man.db_config['name'],
                'host': Globals.config_man.db_config['url'],
                'port': Globals.config_man.db_config['port']
            }
            Globals.db_man.open(POSTGRES, Globals.config_man.service_config['debug_mode'])

    except OperationalError as e:
        print("Unable to connect to database - please check settings in config file!", e)
        quit()

    with flask_app.app_context():
        # Create the Service
        Globals.service = SurveyJSService(Globals.config_man, service_info)

        # Start App / reactor events
        reactor.run()
