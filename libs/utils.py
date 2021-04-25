from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import QObject, Signal, Slot
import traceback
import sys

class WorkerSignals(QObject):
    finished = Signal()
    error = Signal(tuple)
    result = Signal(str)
    progress = Signal(int)


class Worker(QtCore.QRunnable):

    def __init__(self, fn, *args, **kwargs):
        super().__init__()

        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.kwargs['progress_callback'] = self.signals.progress


    @Slot()
    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()


