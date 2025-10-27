import tempfile
import os
import shutil

from libactimetry.workers.BaseWorker import BaseWorker

from libopenimu.importers.AppleWatchImporter import AppleWatchImporter
from libopenimu.models.DataSource import DataSource as OpenIMUDataSource


class OpenIMUImporterWorker(BaseWorker):

    def __init__(self):
        BaseWorker.__init__(self)

    def init(self):
        print("OpenIMUImporterWorker: init")
        BaseWorker.init(self)
        # print(json.dumps(self._params))

    def run(self):
        from libopenimu.db.DBManager import DBManager as OpenIMUDBManager
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
            importer = AppleWatchImporter(db_manager, target_participant)
            for asset in self._params['assets']:
                src_file = str(os.path.join(self._params['base_assets_path'], asset['uuid']))
                file_md5 = OpenIMUDataSource.compute_md5(src_file).hexdigest()
                if OpenIMUDataSource.datasource_exists_for_participant(asset['uuid'], target_participant, file_md5,
                                                                       importer.db.session):
                    print("-> Ignoring " + asset['uuid'] + " - Already imported.")
                    continue

                dest_file = str(os.path.join(tmpdir, asset['filename']))
                shutil.copy(src_file, dest_file)

                # Import files
                if ".data" in dest_file:
                    print("-> Loading: " + dest_file)
                    if not os.path.isfile(dest_file):
                        print("--> File not found, ignoring...")
                        continue

                    results = importer.load(dest_file)
                    print('-> Importing...')
                    importer.import_to_database(results)

                    # Add datasources for that file
                    for recordset in importer.recordsets:
                        if not OpenIMUDataSource.datasource_exists_for_recordset(
                                filename=asset['uuid'],
                                recordset=recordset,
                                md5=file_md5,
                                db_session=importer.db.session,
                        ):
                            ds = OpenIMUDataSource()
                            ds.recordset = recordset
                            ds.file_md5 = file_md5
                            ds.file_name = asset['uuid']
                            ds.update_datasource(
                                db_session=importer.db.session
                            )

                    importer.clear_recordsets()
        print("** OpenIMU import completed.")



if __name__ == '__main__':
    worker = OpenIMUImporterWorker()
    worker.init()
    worker.run()
