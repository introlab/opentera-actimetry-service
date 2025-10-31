from libactimetry.workers.BaseWorker import BaseWorker
from libopenimu.db.DBManager import DBManager
from libopenimu.algorithms.Fraysse2021 import Fraysse2021, Fraysse2021Factory
import os
import json


class Fraysse2021Worker(BaseWorker):

    def __init__(self):
        self.db_manager = None
        self.to_process = {}
        BaseWorker.__init__(self)

    def init(self):
        print("Fraysse 2021 initializing...")
        BaseWorker.init(self)
        # Open database
        if not os.path.isfile(self._datapath):
            self.print_err('Database ' + self._datapath + ' does not exist')
            exit(1)

        self.db_manager = DBManager(self._datapath)

        # Get participant
        participants = self.db_manager.get_all_participants()
        if len(participants) == 0:
            self.print_err('Database doesn\'t have any participant')
            exit(1)

        # Prepare list of recordsets to process
        target_participant = participants[0]
        processed_recordsets = self.db_manager.get_all_processed_data(target_participant)
        processed_recordsets_ids = []
        for processed in processed_recordsets:
            for ref in processed.processed_data_ref:
                if ref.id_recordset not in processed_recordsets_ids:
                    processed_recordsets_ids.append(ref.id_recordset)

        recordsets = [recordset for recordset in self.db_manager.get_all_recordsets(target_participant)
                      if recordset.id_recordset not in processed_recordsets_ids]

        # Group recordsets by dates
        for recordset in recordsets:
            recordset_date = recordset.start_timestamp.date().strftime('%d-%m-%Y')
            if recordset_date not in self.to_process:
                self.to_process[recordset_date] = []
            self.to_process[recordset_date].append(recordset)

    def run(self):
        print("Fraysse 2021 running...")
        # Process algorithm once for each recordset that makes a day
        # Default params?
        algo_factory = Fraysse2021Factory()


        params = {}
        if not self._params:
            # Default parameters if none specified
            print("Using default parameters")
            default_params = algo_factory.params()
            for param_name in default_params:
                params[param_name] = default_params[param_name]["default_value"]
        else:
            params = json.loads(self._params)
        algorithm = Fraysse2021(params)

        for date in self.to_process:
            print("Processing " + date + "...")
            recordsets = self.to_process[date]
            results = algorithm.calculate(self.db_manager, recordsets)

            # Save to database
            name = date + "[" + algo_factory.name() + "]"
            self.db_manager.add_processed_data(algo_factory.unique_id(), name, results, recordsets, params)

        # All done now!
        print("All done!")



if __name__ == '__main__':
    worker = Fraysse2021Worker()
    worker.init()
    worker.run()
