import uuid
import threading
import sys
import subprocess
import pickle
import datetime
import json

import Globals as Globals
from libactimetry.db.models.ActimetryWorkerLog import ActimetryWorkerLog, WorkerType, WorkerOwnerType, WorkerStatus


class WorkerManager:
    def __init__(self, app):
        self._processes = {}
        self.flask_app = app

    def worker_log_stdout(self, worker_uuid: uuid.UUID, text: str):
        with self.flask_app.app_context():
            worker_log = ActimetryWorkerLog.get_log_for_worker(str(worker_uuid))
            if worker_log:
                worker_log.worker_logs.append(text)
                worker_log.commit()

    def worker_log_stderr(self, worker_uuid: uuid.UUID, text: str):
        with self.flask_app.app_context():
            worker_log = ActimetryWorkerLog.get_log_for_worker(str(worker_uuid))
            if worker_log:
                worker_log.worker_errors.append(text)
                worker_log.commit()

    def worker_update_status(self, worker_uuid: uuid.UUID, status: WorkerStatus, ended: bool = False):
        with self.flask_app.app_context():
            worker_log = ActimetryWorkerLog.get_log_for_worker(str(worker_uuid))
            if worker_log:
                worker_log.worker_status = status.value
                if ended:
                    worker_log.worker_end_time = datetime.datetime.now()
                worker_log.commit()

            if ended:
                del self._processes[worker_uuid]

    def worker_set_results(self, worker_uuid: uuid.UUID, results: str):
        with self.flask_app.app_context():
            worker_log = ActimetryWorkerLog.get_log_for_worker(str(worker_uuid))
            if worker_log:
                worker_log.worker_results = results
                worker_log.commit()

    def start_processing_worker(self, script: str, datapath: str, params: dict, owner_uuid: str,
                                owner_type: WorkerOwnerType, database_id: int) -> (uuid.UUID, WorkerStatus):
        # Create a job UUID
        job_uuid = str(uuid.uuid4())

        # Create worker log entry
        worker_log = ActimetryWorkerLog()
        worker_log.worker_uuid = job_uuid
        worker_log.worker_owner_uuid = owner_uuid
        worker_log.worker_owner_type = owner_type.value
        worker_log.worker_parameters = json.dumps({'script': script, 'params': params})
        worker_log.worker_type = WorkerType.TYPE_ALGORITHM.value
        worker_log.worker_id_database = database_id
        ActimetryWorkerLog.insert(worker_log)

        # Set worker parameters in redis with expiration
        job_id = f"actimetry.worker.{job_uuid}"
        # Globals.redis_client.redisSet(job_id, json.dumps(params), ex=60)

        # Launch subprocess
        # TODO Validate if script exists
        command = [sys.executable, script, '--datapath', datapath, '--job_id', job_id]

        # Launch process, will be monitored by a thread
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self._processes[job_uuid] = process

        # Send parameters to process
        try:
            process.communicate(input=pickle.dumps(params), timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            self.worker_update_status(job_uuid, WorkerStatus.STATUS_ABORTED)
            del self._processes[job_uuid]
            return job_uuid, WorkerStatus.STATUS_ABORTED

        # Monitor process termination with callback
        def process_monitor_thread(monitored_processed: subprocess.Popen, worker_uuid: uuid.UUID, worker_man: WorkerManager):
            self.worker_update_status(worker_uuid, WorkerStatus.STATUS_RUNNING)
            while monitored_processed.poll() is None:
                output, error = monitored_processed.communicate()
                if output:
                    str_output = output.decode("utf-8")
                    if str_output.find('*** RESULTS ***: '):
                        worker_man.worker_set_results(worker_uuid, str_output.replace('*** RESULTS ***: ', ''))
                    else:
                        worker_man.worker_log_stdout(worker_uuid, str_output)
                if error:
                    worker_man.worker_log_stderr(worker_uuid, error.decode('utf-8'))

            monitored_processed.wait()
            # Get return code
            return_code = monitored_processed.returncode
            status = WorkerStatus.STATUS_COMPLETED
            if return_code != 0:
                status = WorkerStatus.STATUS_ABORTED
            worker_man.worker_update_status(worker_uuid, status=status, ended=True)
            threading.current_thread().join()


        thread = threading.Thread(target=process_monitor_thread, args=(process, job_uuid, self))
        thread.start()

        return job_uuid, WorkerStatus.STATUS_RUNNING
