"""
@Author Neil Berard
Module for file browser widgets.

"""

import abc
import logging
import os
import shutil
import subprocess
from functools import partial

from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import Signal


ICON_PROVIDER = QtWidgets.QFileIconProvider()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)



class AbstractDockWindow:
    def __init__(self, main_window):
        self.main_window = main_window

    @abc.abstractmethod
    def add_widget(self, browser_window, path=None):
        pass

    @abc.abstractmethod
    def set_title(self, title):
        pass

    @abc.abstractmethod
    def get_title(self):
        pass

    @abc.abstractmethod
    def populate(self):
        pass

    @abc.abstractmethod
    def clear_widgets(self):
        pass

    @abc.abstractmethod
    def remove_widget(self, *args):
        pass


class TabWindow(AbstractDockWindow, QtWidgets.QTabWidget):

    def __init__(self, main_window):
        AbstractDockWindow.__init__(self, main_window)
        QtWidgets.QTabWidget.__init__(self)

        self.dir_path = ""

        self.setAcceptDrops(True)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_tab)
        self.currentChanged.connect(self.set_active)

    def set_title(self, title):
        idx = self.indexOf(self.main_window.get_active_browser())
        self.setTabText(idx, title)
        self.widget(idx).setWindowTitle(title)

    def get_title(self):
        idx = self.indexOf(self.main_window.get_active_browser())
        return self.tabText(idx)

    def add_widget(self, browser_window, path=None, set_current=True):
        self.addTab(browser_window, browser_window.windowTitle())
        if set_current:
            self.setCurrentWidget(browser_window)
            self.main_window.set_active_browser(browser_window)

    def populate(self):
        log.debug("Populating widgets {}".format(self.main_window.get_browser_list()))
        self.blockSignals(True)
        for w in self.main_window.get_browser_list():
            self.add_widget(w, set_current=False)
        self.setCurrentWidget(self.main_window.get_active_browser())
        self.blockSignals(False)

    def remove_widget(self, widget):
        self.removeTab(self.indexOf(widget))

    def close_tab(self, *args):
        self.main_window.remove_browser(self.widget(args[0]))

    def clear_widgets(self):
        self.blockSignals(True)
        self.clear()
        self.blockSignals(False)

    def set_active(self):
        self.main_window.set_active_browser(self.currentWidget())


class DockWindow(AbstractDockWindow, QtWidgets.QWidget):

    close_event = Signal(AbstractDockWindow)

    def __init__(self, main_window):
        QtWidgets.QWidget.__init__(self)
        AbstractDockWindow.__init__(self, main_window)

        self.splitter = QtWidgets.QSplitter()
        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().addWidget(self.splitter)
        self._active = None
        self.layout().setContentsMargins(0,0,0,0)


    def set_active(self, *args):
        pass

    def set_title(self, title):
        dock = self.main_window.get_active_browser()
        if dock:
            dock.parent().setWindowTitle(title)
            # TODO Redundant use of window title, clean this up.
            dock.setWindowTitle(title)

    def get_title(self):
        dock = self.main_window.get_active_browser()
        if dock:
            return dock.parent().windowTitle()
        pass

    def add_widget(self, browser_window, path=None, set_current=True):
        dock_widget = DockWidget(browser_window)
        dock_widget.closed_event.connect(partial(self.main_window.remove_browser, browser_window))
        self.splitter.addWidget(dock_widget)

    def remove_widget(self, dock_widget):
        self.main_window.remove_browser(dock_widget)

    def populate(self):
        log.debug("{} Populating widgets {}".format(self.__class__.__name__, self.main_window.get_browser_list()))
        for w in self.main_window.get_browser_list():
            self.add_widget(w)

    def clear_widgets(self):
        for dock in self.findChildren(DockWidget):
            dock.release_browser()

    def get_active(self, *args):
        return self._active


class DockWidget(QtWidgets.QDockWidget):
    closed_event = Signal(QtWidgets.QDockWidget)

    def __init__(self, browser_window):

        super().__init__()
        self.browser_window = browser_window
        self.setWidget(browser_window)
        self.setWindowTitle(browser_window._leaf)
        self.setFeatures(QtWidgets.QDockWidget.DockWidgetClosable)

    def closeEvent(self, event):
        self.browser_window.setParent(None)
        self.hide()
        self.setParent(None)
        self.setWidget(None)
        self.closed_event.emit(self.browser_window)
        super().closeEvent(event)

    def release_browser(self):
        self.browser_window.setParent(None)
        self.setWidget(None)
        self.deleteLater()


class FileItem:
    file_info = QtCore.QFileInfo()
    full_path = None
    clicked_times = 0
    sort_token = ""

    def __init__(self, item_data: dict):
        self.__dict__.update(item_data)

        self.file_info = QtCore.QFileInfo(self.full_path)
        self.file_name = self.file_info.fileName()
        self.suffix = self.file_info.completeSuffix()

        if self.is_dir():
            self.suffix = "0"

        if not self.sort_token:
            self.sort_token = self.suffix + self.file_name


    def file_path(self):
        return self.full_path

    def is_dir(self):
        return self.file_info.isDir()


class FileItemWidget(QtWidgets.QListWidgetItem, FileItem):
    """
    This widget stores all information on a file path.
    """

    def __init__(self, item_data: dict):
        QtWidgets.QListWidgetItem.__init__(self)
        FileItem.__init__(self, item_data)

        icon = ICON_PROVIDER.icon(self.file_info)
        self.setIcon(icon)
        self.setToolTip(self.full_path)
        self.setText(self.file_name)

    # Sorting
    def __lt__(self, other):
        return self.sort_token < other.sort_token


class FavItemWidget(QtWidgets.QListWidgetItem, FileItem):
    def __init__(self, item_data: dict):
        QtWidgets.QListWidgetItem.__init__(self)
        FileItem.__init__(self, item_data)

        if 'nice_name' not in self.__dict__.keys():
            self.nice_name = self.file_name
        self.setText(self.__dict__['nice_name'])

        icon = ICON_PROVIDER.icon(self.file_info)
        self.setIcon(icon)
        self.setToolTip(self.full_path)

    # Sorting
    def __lt__(self, other):
        return self.sort_token < other.sort_token


class BaseListWidget(QtWidgets.QListWidget):
    name = ""
    _context_menu = None


    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self._context_menu = QtWidgets.QMenu()
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # SORTING
        self.setSortingEnabled(True)

        # Base Menu Actions
        open_in_new_tab = self._context_menu.addAction("Open in new tab")
        open_in_new_tab.triggered.connect(self.open_in_new_tab)

        show_in_explorer = self._context_menu.addAction("Show in Explorer")
        show_in_explorer.triggered.connect(self.show_in_explorer)

        copy_path = self._context_menu.addAction("Copy Path")
        copy_path.triggered.connect(self.copy_path)

    def mouseDoubleClickEvent(self, event):
        self.open()

    def open(self):
        item = self.currentItem()
        assert isinstance(item, FileItemWidget)

        if item.is_dir():
            self.main_window.get_active_browser().set_path(item.file_path(), is_dir=item.file_info.isDir())
        else:
            os.startfile(item.file_path())

    def show_in_explorer(self):

        item = self.currentItem()
        if not item:
            os.startfile(self.parent().get_path())

        if item.is_dir():
            os.startfile(item.file_path())
        else:
            os.startfile(os.path.dirname(item.file_path()))

    def copy_path(self):
        subprocess.run("clip", universal_newlines=True, input=self.currentItem().file_path())

    def open_in_new_tab(self):
        item = self.currentItem()
        if item.is_dir():
            self.main_window.add_browser({"_full_path": self.currentItem().file_path()})
        else:
            self.main_window.add_browser({"_full_path": os.path.dirname(item.file_path())})

    def show_context_menu(self, pos):
        self._context_menu.exec_(self.mapToGlobal(pos))


class FavWidget(QtWidgets.QListWidget):
    def __init__(self, main_window, items=None, name=""):
        super().__init__()
        global CAN_SAVE_SETTINGS
        self.main_window = main_window

        # Serializable Data
        self._items = []
        self.setObjectName(name)

        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self._context_menu = QtWidgets.QMenu()
        self._sort_context_menu = QtWidgets.QMenu()
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        try:
            self.add_menu_actions()
        except Exception as ex:
            log.error("FAV Widget failed to initialize! Will not save added pins.\n\n{}".format(ex))
            CAN_SAVE_SETTINGS = False

        if items:
            for i in items:
                self.add_pin(i)

    def add_pin(self, item_data):
        new_pin = FavItemWidget(item_data)
        self._items.append(new_pin)
        self.addItem(new_pin)
        self.setItemSelected(new_pin, True)

    def pins(self):
        return self._items

    def dropEvent(self, event):
        message = self.main_window.get_drag_message()
        if not message:
            return
        if not isinstance(message, list):
            message = [message]
        for i in message:
            self.add_pin(i.__dict__)

        for i in self._items:
            self.setItemSelected(i, False)

        # self.add_pin(message[0].__dict__)

        self.main_window.set_drag_message(None)
        self.main_window.is_dragging = False

    def add_menu_actions(self):
        rename_pin = self._context_menu.addAction("Rename Pin")
        rename_pin.triggered.connect(self.rename_pin)

        delete_pins = self._context_menu.addAction("Delete Pins")
        delete_pins.triggered.connect(self.delete_pins)

        set_pin_color = self._context_menu.addAction("Set Color")
        set_pin_color.triggered.connect(self.set_pin_color)



        def set_sort(sort_type):
            self.set_sort(sort_type)

        self._sort_context_menu = self._context_menu.addMenu("Sort by...")

        sort = self._sort_context_menu.addAction("File Type")
        sort.triggered.connect(partial(self.set_sort, sort.text()))

        sort = self._sort_context_menu.addAction("Usage")
        sort.triggered.connect(partial(self.set_sort, sort.text()))

        sort = self._sort_context_menu.addAction("Name")
        sort.triggered.connect(partial(self.set_sort, sort.text()))

        sort = self._sort_context_menu.addAction("Size")
        sort.triggered.connect(partial(self.set_sort, sort.text()))

        sort = self._sort_context_menu.addAction("Date Added")
        sort.triggered.connect(partial(self.set_sort, sort.text()))

    def set_pin_color(self):
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            print("yes!")
        pass

    def set_sort(self, sort_type):
        for i in range(self.count()):
            w = self.item(i)
            assert isinstance(w, FavItemWidget)

            if sort_type == "Name":
                w.sort_token = w.text()
            if sort_type == "File Type":
                w.sort_token = w.suffix + w.text()
            if sort_type == "Usage":
                w.sort_token = w.clicked_times

        self.sortItems()

    def delete_pins(self):
        for i in self.selectedItems():
            print(i)
            print(self._items)
            self._items.remove(i)
            self.indexFromItem(i)
            self.takeItem(self.row(i))
            # self.takeTopLevelItem(self.indexOfTopLevelItem(i))

    def mousePressEvent(self, event):
        super().mousePressEvent(event)

    def open(self):
        item = self.currentItem()
        if item.is_dir():
            self.main_window.get_active_browser().set_path(item.file_path(),
                                                       is_dir=item.file_info.isDir())
        else:
            os.startfile(item.file_path())

    def rename_pin(self):
        flags = self.currentItem().flags()
        self.currentItem().setFlags(flags | QtCore.Qt.ItemIsEditable)
        self.edit(self.currentIndex())

    def get_items(self):
        return self._items

    def mouseDoubleClickEvent(self, event):
        self.open()
        self.currentItem().clicked_times -= 1
        log.debug(self.currentItem().clicked_times)

    def show_context_menu(self, pos):
        self._context_menu.exec_(self.mapToGlobal(pos))


class FileListWidget(BaseListWidget):

    def __init__(self, main_window):
        super().__init__(main_window)
        self._items = []
        self.directory = ""
        self._dragging = False

        # What do we want to do with the dropped file
        self._drop_menu = QtWidgets.QMenu()
        self.add_drop_context_menu_options()
        self.add_context_menu_options()

    def add_context_menu_options(self):
        delete_file = self._context_menu.addAction("Delete Files")
        delete_file.triggered.connect(self.delete_files)

    def set_root_directory(self, directory):
        self.clear()
        self.directory = directory
        items = os.listdir(directory)

        for path in items:
            full_path = os.path.join(directory, path)
            full_path = full_path.replace('\\', '/')
            item_widget = FileItemWidget({'full_path': full_path})
            self.add_item(item_widget)
        self.sortItems()

    def add_item(self, item_widget):
        self.addItem(item_widget)
        self._items.append(item_widget)



    def add_drop_context_menu_options(self):
        copy_files = self._drop_menu.addAction("Copy")
        copy_files.triggered.connect(self.copy_files)
        move_files = self._drop_menu.addAction("Move")
        move_files.triggered.connect(self.move_files)
        self._drop_menu.addAction("Cancel")

    def copy_files(self):
        for i in self.main_window.get_drag_message():
            new_path = os.path.join(self.directory, i.file_name)
            if i.is_dir():
                shutil.copytree(i.file_path(), new_path)
            else:
                shutil.copy(i.file_path(), new_path)
        # TODO: hack to refresh, implement real refresh later.
        self.parent().set_path(self.directory, is_dir=True)

    def move_files(self):
        for i in self.main_window.get_drag_message():
            new_path = os.path.join(self.directory, i.file_name)
            if i.is_dir():
                shutil.move(i.file_path(), new_path)
            else:
                shutil.move(i.file_path(), new_path)

        # TODO: hack to refresh, implement real refresh later.
        self.parent().set_path(self.directory, is_dir=True)
        active_browser = self.main_window.get_active_browser()
        active_browser.set_path(active_browser.get_path(), is_dir=True)

    def delete_files(self):
        for i in self.selectedItems():
            if i.is_dir():
                shutil.rmtree(i.file_path())
            else:
                os.remove(i.file_path())
        self.parent().set_path(self.directory, is_dir=True)

    def clear(self):
        self._items.clear()
        super().clear()

    def get_items(self):
        return self._items

    def dragMoveEvent(self, event):
        if self.main_window.is_dragging:
            return
        self.main_window.is_dragging = True

    def dropEvent(self, event):
        print("Dropped! {}".format(self.directory))
        self._drop_menu.exec_(self.mapToGlobal(event.pos()))
        self.main_window.is_dragging = False
        self.main_window.set_drag_message(None)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.main_window.set_active_browser(self.parent())

        # Set active selection
        self.main_window.set_drag_message(self.selectedItems())


class PathLineEdit(QtWidgets.QLineEdit):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragEnabled(True)

    # def dragEnterEvent(self, event):
    #     print("Dragging! {}".format(type(self).__name__))


class BrowserWidget(QtWidgets.QWidget):

    def __init__(self, main_window, browser_data=None):
        super().__init__()
        self.main_window = main_window

        # Data
        self._leaf = ""
        self._full_path = ""

        self._active = False

        # History
        self.history = []
        self.history_idx = 0

        self.central_layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.central_layout)
        self.layout().setContentsMargins(0,5,0,0)


        # BROWSER PATH
        self.path_line_edit = PathLineEdit()
        self.central_layout.addWidget(self.path_line_edit)
        self.list_view = FileListWidget(self.main_window)
        self.central_layout.addWidget(self.list_view)

        # SIGNAL
        self.path_line_edit.textEdited.connect(self.set_path_edit)

        if browser_data:
            self.__dict__.update(browser_data)


    def set_path_edit(self):
        path = self.path_line_edit.text()
        if os.path.isdir(self.path_line_edit.text()):
            self.set_path(path, is_dir=True, set_text=False)

    def set_path(self, path, is_dir=False, history=True, set_text=True):

        self._leaf = os.path.split(path)[-1]
        self._full_path = path
        if not self._leaf:
            self._leaf = self._full_path

        self.setWindowTitle(self._leaf)

        if is_dir:
            self.list_view.set_root_directory(path)
            if set_text:
                self.path_line_edit.setText(path)


            # TODO: This is ugly, make it clean.
            if history and not self.history or history and self.history[-1] != path:
                self.history.append(path)
                self.history_idx = len(self.history) -1
            self.main_window.set_active_browser_title(self._leaf)

    def get_path(self):
        return self._full_path

    def back(self):
        if self.history_idx > 0:
            self.history_idx -= 1
            self.set_path(self.history[self.history_idx], is_dir=True, history=False)

    def forward(self):
        if self.history_idx < (len(self.history) -1):
            self.history_idx += 1
            self.set_path(self.history[self.history_idx], is_dir=True, history=False)

    def up(self):
        new_dir = os.path.dirname(self._full_path)
        self.set_path(new_dir, is_dir=True)

    def pin_item(self):
        item = self.list_view.currentItem()
        self.main_window.pin_list.add_pin(item.file_path())

    def set_dir(self):
        item = self.list_view.currentItem()
        self.set_path(item.file_path(), is_dir=item.file_info.isDir())

    def mouseDoubleClickEvent(self, event):
        self.set_dir()
        self.set_active(True)

    def set_active(self, active:bool):
        self.main_window.set_active_browser(self)

    def mouseMoveEvent(self, event):
        print("Move!")