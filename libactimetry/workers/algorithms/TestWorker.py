from libactimetry.workers.BaseWorker import BaseWorker
import time


class TestWorker(BaseWorker):

    def __init__(self):
        BaseWorker.__init__(self)

    def init(self):
        print("TestWorker: init")
        BaseWorker.init(self)

    def run(self):
        print("TestWorker: run")
        time.sleep(2)

if __name__ == '__main__':
    worker = TestWorker()
    worker.init()
    worker.run()
