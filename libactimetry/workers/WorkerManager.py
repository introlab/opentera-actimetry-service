import uuid
import threading
import sys
import subprocess
import datetime
import json
import os
import base64
import Globals as Globals

from sqlalchemy.orm import sessionmaker, scoped_session

from libactimetry.db.models.ActimetryWorkerLog import ActimetryWorkerLog, WorkerType, WorkerOwnerType, WorkerStatus
from libactimetry.db.models.ActimetryDatabase import ActimetryDatabase
from libactimetry.db.models.ActimetryAsset import ActimetryAsset
from opentera.db.models.TeraSessionEvent import TeraSessionEvent

class WorkerManager:
    def __init__(self, app):
        self._processes = {}
        if hasattr(app, 'flask_app'):
            self.flask_app = app.flask_app
        else:
            self.flask_app = app

    def worker_log_stdout(self, worker_uuid: uuid.UUID, text: str):
        with self.flask_app.app_context():
            print(self._processes[worker_uuid]['name'] + ' - ' + text)
            worker_log = ActimetryWorkerLog.get_log_for_worker(str(worker_uuid))
            if worker_log:
                worker_log.worker_logs += text
                worker_log.commit()

    def worker_log_stderr(self, worker_uuid: uuid.UUID, text: str):
        with self.flask_app.app_context():
            print(self._processes[worker_uuid]['name'] + ' - * ERROR * ' + text)
            worker_log = ActimetryWorkerLog.get_log_for_worker(str(worker_uuid))
            if worker_log:
                worker_log.worker_errors += text
                worker_log.commit()

    def worker_update_status(self, worker_uuid: uuid.UUID, status: WorkerStatus, ended: bool = False):
        source = str(self._processes[worker_uuid]['source'])
        id_session = int(source)

        with self.flask_app.app_context():
            worker_log = ActimetryWorkerLog.get_log_for_worker(str(worker_uuid))
            if worker_log:
                worker_log.worker_status = status.value
                if ended:
                    worker_log.worker_end_time = datetime.datetime.now()
                worker_log.commit()
                if worker_log.worker_type == WorkerType.TYPE_IMPORTER.value:
                    source = "Session ID " + source

        self.send_session_event(id_session=id_session,
                                id_session_event_type=TeraSessionEvent.SessionEventTypes.GENERAL_INFO.value,
                                session_event_context='ActimetryService.WorkerManager',
                                session_event_text=f'Import status {ActimetryWorkerLog.get_status_description(status)}')


        if status != WorkerStatus.STATUS_ABORTED:
            Globals.service.logger.log_info('ActimetryService.WorkerManager', self._processes[worker_uuid]['name'],
                                            self._processes[worker_uuid]['context'], source,
                                            ActimetryWorkerLog.get_status_description(status))
        else:
            Globals.service.logger.log_error('ActimetryService.WorkerManager', self._processes[worker_uuid]['name'],
                                             self._processes[worker_uuid]['context'], source,
                                             ActimetryWorkerLog.get_status_description(status))

        if ended:
            if worker_log.worker_type == WorkerType.TYPE_IMPORTER.value and status != WorkerStatus.STATUS_ABORTED:
                id_database = worker_log.id_database
                with self.flask_app.app_context():
                    # Check if already a worker planned
                    if not ActimetryWorkerLog.get_logs_for_database(id_database, WorkerStatus.STATUS_PLANNED):
                        database_infos = ActimetryDatabase.get_by_id(id_database)
                        database_path = (
                                Globals.service.config_man.actimetry_service_config[
                                    "databases_directory"] + os.sep + database_infos.database_uuid
                        )

                        process_worker = ActimetryWorkerLog()
                        process_worker.worker_uuid = str(uuid.uuid4())
                        process_worker.worker_owner_uuid = worker_log.worker_owner_uuid
                        process_worker.worker_owner_type = worker_log.worker_owner_type
                        # TODO: Configure specific processor and parameters to start
                        process_worker.worker_parameters = json.dumps({'script': "Fraysse2021",
                                                                       'script_name': "Fraysse2021Worker.py",
                                                                       'database_path': database_path,
                                                                       'params': None,
                                                                       'context': self._processes[worker_uuid]['context'] })
                        process_worker.worker_type = WorkerType.TYPE_ALGORITHM.value
                        process_worker.worker_status = WorkerStatus.STATUS_PLANNED.value
                        process_worker.worker_start_time = datetime.datetime.now() + datetime.timedelta(minutes=1)# + datetime.timedelta(days=1)
                        process_worker.id_database = id_database
                        ActimetryWorkerLog.insert(process_worker)

            del self._processes[worker_uuid]


    def worker_set_results(self, worker_uuid: uuid.UUID, results: str):
        with self.flask_app.app_context():
            worker_log = ActimetryWorkerLog.get_log_for_worker(str(worker_uuid))
            if worker_log:
                worker_log.worker_results = results
                worker_log.commit()

    def start_processing_worker(self, script: str, script_name: str, datapath: str, params: dict, owner_uuid: str,
                                owner_type: WorkerOwnerType, database_id: int, context: str = 'Unknown',
                                worker_log: ActimetryWorkerLog | None = None) -> dict:  # (uuid.UUID, WorkerStatus):
        rval = {'success': False, 'message': "", 'worker_uuid': None, 'status': WorkerStatus.STATUS_PLANNED}

        # Validate if path exists
        script_path = os.path.abspath(os.path.dirname(__file__) + os.sep + 'algorithms' + os.sep + script)
        if not os.path.isfile(script_path):
            rval['success'] = False
            rval['message'] = 'Unable to find script for ' + script_name
            return rval

        if not worker_log:
            # Not related worker log - create a new one
            # Create a job UUID
            rval['worker_uuid'] = str(uuid.uuid4())

            # Create worker log entry
            worker_log = ActimetryWorkerLog()
            worker_log.worker_uuid = rval['worker_uuid']
            worker_log.worker_owner_uuid = owner_uuid
            worker_log.worker_owner_type = owner_type.value
            worker_log.worker_parameters = json.dumps({'script': script, 'params': params})
            worker_log.worker_type = WorkerType.TYPE_ALGORITHM.value
            worker_log.id_database = database_id
            ActimetryWorkerLog.insert(worker_log)
        else:
            # Update related worker log
            worker_log.worker_parameters = json.dumps({'script': script, 'params': params})
            worker_log.worker_status = WorkerStatus.STATUS_READY.value
            ActimetryWorkerLog.db().session.commit()

        # Launch subprocess
        # TODO Validate if script exists
        command = [sys.executable, script_path, '--datapath', datapath,
                   '--job_id', rval['worker_uuid'], '--params', base64.b64encode(json.dumps(params).encode('utf-8'))]

        # Launch process, will be monitored by a thread
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self._processes[rval['worker_uuid']] = {'name': 'Processor',
                                                'context': context, 'source': script_name, 'process': process, 'params': params}

        thread = threading.Thread(target=self.process_monitor_thread, args=(process, rval['worker_uuid']))
        thread.start()

        rval['success'] = True
        rval['status'] = WorkerStatus.STATUS_RUNNING
        return rval

    def start_openimu_importer_worker(self, participant_uuid: str, participant_name: str,
                                      base_assets_path: str, id_collection: int, owner_uuid: str,
                                      owner_type: WorkerOwnerType) -> (uuid.UUID, WorkerStatus):

        # Check if database exists for participant
        database = ActimetryDatabase.get_for_participant(participant_uuid)
        if not database:
            print("No database for that participant - aborting import process")
            return uuid.UUID(int=0), WorkerStatus.STATUS_ABORTED

        # Check if we already have a import process for that session (collection)
        is_importing = len([job_uuid for job_uuid in self._processes
                            if self._processes[job_uuid]['source'] == id_collection]) > 0
        if is_importing:
            print("Already importing data for this session (" + str(id_collection) + ") - Ignoring new request.")
            return uuid.UUID(int=0), WorkerStatus.STATUS_ABORTED

        # Prepare assets mapping
        assets = ActimetryAsset.get_assets_for_collection(collection_id=id_collection)
        if not assets:
            return uuid.UUID(int=0), WorkerStatus.STATUS_ABORTED

        assets_list = [{'filename': asset.asset_original_filename, 'uuid': asset.asset_uuid} for asset in assets]

        # Create a job UUID
        job_uuid = str(uuid.uuid4())

        # Create worker log entry
        params = {'participant': participant_uuid, 'id_collection': id_collection}
        worker_log = ActimetryWorkerLog()
        worker_log.worker_uuid = job_uuid
        worker_log.worker_owner_uuid = owner_uuid
        worker_log.worker_owner_type = owner_type.value
        worker_log.worker_parameters = json.dumps(params)
        worker_log.worker_type = WorkerType.TYPE_IMPORTER.value
        worker_log.id_database = database.id_database
        ActimetryWorkerLog.insert(worker_log)

        params = {'base_assets_path': base_assets_path,
                  'database_path': Globals.config_man.actimetry_service_config["databases_directory"],
                  'assets': assets_list, 'database': database.database_uuid, 'participant': participant_name}
        # Launch subprocess
        command = [sys.executable, os.path.abspath(os.path.dirname(__file__) + os.sep + 'OpenIMUImporterWorker.py'),
                   '--job_id', job_uuid, '--params', base64.b64encode(json.dumps(params).encode('utf-8'))]

        # Launch process, will be monitored by a thread
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self._processes[job_uuid] = {'name': 'OpenIMU Importer',
                                     'context': participant_name,
                                     'source': id_collection, 'process': process}

        thread = threading.Thread(target=self.process_monitor_thread, args=(process, job_uuid))

        # Add event to session (on base server)
        self.send_session_event(id_session=id_collection,
                                id_session_event_type=TeraSessionEvent.SessionEventTypes.GENERAL_INFO.value,
                                session_event_context='ActimetryService.WorkerManager',
                                session_event_text=f'Importing actimetry data for participant {participant_name} with OpenIMUImporterWorker.')

        thread.start()

        return job_uuid, WorkerStatus.STATUS_RUNNING

    # Monitor process termination with callback
    def process_monitor_thread(self, monitored_processed: subprocess.Popen, worker_uuid: uuid.UUID):
        self.worker_update_status(worker_uuid, WorkerStatus.STATUS_RUNNING)
        while monitored_processed.poll() is None:
            output, error = monitored_processed.communicate()
            if output:
                str_output = output.decode("utf-8")
                if str_output.find('*** RESULTS ***: ') >= 0:
                    self.worker_set_results(worker_uuid, str_output.replace('*** RESULTS ***: ', ''))
                else:
                    self.worker_log_stdout(worker_uuid, str_output)
            if error:
                self.worker_log_stderr(worker_uuid, error.decode('utf-8'))

        monitored_processed.wait()
        # Get return code
        return_code = monitored_processed.returncode
        status = WorkerStatus.STATUS_COMPLETED
        if return_code != 0:
            status = WorkerStatus.STATUS_ABORTED
        self.worker_update_status(worker_uuid, status=status, ended=True)
        threading.main_thread().join()

    def send_session_event(self, id_session: int, id_session_event_type: int, session_event_context: str,
                           session_event_text: str) -> bool:
        """
        Send a session event to OpenTera server
        """
        event = {"session_event": {
            "id_session": id_session,
            "id_session_event": 0, # new event
            "id_session_event_type": id_session_event_type,
            "session_event_context": session_event_context,
            "session_event_datetime": datetime.datetime.now().isoformat(),
            "session_event_text": session_event_text
        }}
        response = Globals.service.post_to_opentera('/api/service/sessions/events', json_data=event)
        return response.status_code == 200
