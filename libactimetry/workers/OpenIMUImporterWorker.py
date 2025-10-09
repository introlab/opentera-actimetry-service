from libactimetry.workers.BaseWorker import BaseWorker


class OpenIMUImporterWorker(BaseWorker):

    def __init__(self):
        BaseWorker.__init__(self)

    def init(self):
        print("OpenIMUImporterWorker: init")
        BaseWorker.init(self)
        print("*** Params: " + self._params)

    def run(self):
        print("OpenIMUImporterWorker: run")

if __name__ == '__main__':
    worker = OpenIMUImporterWorker()
    worker.init()
    worker.run()
