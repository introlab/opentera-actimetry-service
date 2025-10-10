import abc
import argparse
import json
import base64
import sys

from abc import ABC


class BaseWorker(ABC):

    def __init__(self):
        self._params = {}
        self._datapath = None
        self._job_id = None

    def init(self):
        # print("TestWorker: init")
        parser = argparse.ArgumentParser(description="Actimetry Worker")
        parser.add_argument("--datapath", help="Datapath to process data")
        parser.add_argument("--job_id", help="Job UUID")
        parser.add_argument("--params", help="Job parameters (Base64 encoded)", default = None)
        args = parser.parse_args()

        self._job_id = args.job_id
        self._datapath = args.datapath
        self._params = json.loads(base64.b64decode(args.params))
        # print(args)

    @abc.abstractmethod
    def run(self):
        pass

    @staticmethod
    def print_err(message):
        sys.stderr.write(message)
