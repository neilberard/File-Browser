import time

from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import QObject, Signal, Slot
from libs.widgets import FileItem
import traceback
import sys
import os
from libs.consts import FULL_PATH


class WorkerSignals(QObject):
    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    progress = Signal(int)


class Thread(QtCore.QThread):
    def __init__(self,
                 max_results=100,
                 cache_index=False,
                 search_directory_list=None,
                 search_string="",
                 match_case=False,
                 search_file_contents=False,
                 file_content_types=None,
                 mutex=None,
                 ):
        """
        This thread is intended to always be running in the background and yield results when fed updates.
        Otherwise sit idle if nothing to do.

        :param max_results:
        :param cache_index: Precache file directries for faster searching.
        :param search_string:
        :param match_case:
        :param search_file_contents:
        :param file_content_types:
        :param mutex:
        """

        super().__init__()

        self._exiting = False
        self.signals = WorkerSignals()
        self._max_results = max_results
        self._mutex = mutex

        # OPTIONS
        self._search_file_contents = search_file_contents
        self._search_string = search_string
        self._match_case = match_case
        self._file_content_types = file_content_types

        self._search_list = search_directory_list
        self._iterable = iter(self._search_list)
        self._recursive = False
        self._return_count = 0

    def run(self, *args):
        print("Starting Thread")
        while not self._exiting:
            time.sleep(.03)
            if not self._search_string:
                continue
            try:
                item = next(self._iterable)
            except StopIteration:
                continue
            try:
                print(item.file_path())
            except:
                pass

            # self.match(item)
            #
            # if self._recursive and i.is_dir():
            #     for root, dirs, files in os.walk(i.file_path()):
            #         if self._exiting:
            #             self._exiting = False
            #             return
            #
            #         for d in dirs:
            #             item = FileItem({FULL_PATH: os.path.join(root, d)})
            #             self.match(item)
            #
            #         for f in files:
            #             item = FileItem({FULL_PATH: os.path.join(root, f)})
            #             self.match(item)


    def reset_search(self):
        """
        Reset the search iterable and start over.
        """
        self._iterable = iter(self._search_list)

    def set_search_string(self, search_string: str):
        """
        Update the current search string.

        """
        print("Updating Search String {}".format(search_string))
        self._search_string = search_string
        self.reset_search()

    def set_search_items(self, items):
        self._search_list = items
        self.reset_search()

    def set_search_recursive(self, recursive):
        self._recursive = recursive

    def match(self, file_item):
        match = False
        self._return_count += 1
        if self._return_count > self._max_results:
            self._exiting = True
        if match:
            self.signals.result.emit(file_item)

    def exit(self, *args):
        print("Exiting Thread")
        self._exiting = True
        super().exit(*args)




