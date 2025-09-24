import abc
from abc import ABC


class BaseWorker(ABC):

    def __init__(self):
        self._params = {}

    @abc.abstractmethod
    def init(self):
        pass

    @abc.abstractmethod
    def run(self):
        pass

    def wait_for_parameters(self):
        print("Waiting for parameters")
        parameters = input()
        self._params = parameters
        print("Received parameters: {}".format(parameters))