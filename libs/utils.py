import time

from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import QObject, Signal, Slot
import traceback
import sys



class WorkerSignals(QObject):
    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    progress = Signal(int)


class Thread(QtCore.QThread):
    def __init__(self, max_results=50):
        super().__init__()
        self._exiting = False
        self.signals = WorkerSignals()
        self._max_results = max_results

        self._search_list = []
        self._recursive = False


    def run(self):
        count = 0
        while not self._exiting and count < self._max_results:
            time.sleep(0.1)
            count += 1
            self.signals.progress.emit(count)
        self._exiting = False


    def exit(self):
        print("Exiting Thread")
        self._exiting = True



