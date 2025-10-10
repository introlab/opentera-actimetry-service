import tempfile
import os
import shutil

from libactimetry.workers.BaseWorker import BaseWorker
from libopenimu.db.DBManager import DBManager as OpenIMUDBManager
from libopenimu.importers.AppleWatchImporter import AppleWatchImporter


class OpenIMUImporterWorker(BaseWorker):

    def __init__(self):
        BaseWorker.__init__(self)

    def init(self):
        print("OpenIMUImporterWorker: init")
        BaseWorker.init(self)
        # print(json.dumps(self._params))

    def run(self):
        print("OpenIMUImporterWorker: run")
        # Open OpenIMU database
        filename = os.path.join(self._params['database_path'], self._params['database'])
        print('** Using database at ' + str(filename))
        db_manager = OpenIMUDBManager(filename)

        # Find target participant
        db_participants = db_manager.get_all_participants()
        target_participant = None
        for participant in db_participants:
            if participant.name == self._params['participant']:
                target_participant = participant
                break

        if not target_participant:
            self.print_err("OpenIMUImporterWorker: participant not found. Aborting")
            exit(1)

        # Create temporary files to import
        with tempfile.TemporaryDirectory() as tmpdir:
            for asset in self._params['assets']:
                src_file = str(os.path.join(self._params['base_assets_path'], asset['uuid']))
                dest_file = str(os.path.join(tmpdir, asset['filename']))
                shutil.copy(src_file, dest_file)

            # Import files
            importer = AppleWatchImporter(db_manager, target_participant)
            for filename in os.listdir(tmpdir):
                full_filename = os.path.join(tmpdir, filename)
                print("-> Loading: " + full_filename)
                results = importer.load(full_filename)
                print('-> Importing...')
                importer.import_to_database(results)


if __name__ == '__main__':
    worker = OpenIMUImporterWorker()
    worker.init()
    worker.run()
