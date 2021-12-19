"""
@Author Neil Berard
Module for file browser widgets.


Class FileItem is how data for all items are stored.

"""

import abc
import logging
import os
import shutil
import subprocess
from functools import partial

from PySide2 import QtWidgets, QtCore, QtGui
from PySide2.QtCore import Signal

from libs.consts import *

ICON_PROVIDER = QtWidgets.QFileIconProvider()

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


_drop_message = None




class FileItem:
    """
    This is the (Model) class of storing information about all file paths in the file browsers and favwidgets.
    QTableWidgetItem, QTreeWidgetItem and QListWidgetItems (View) are only used for displaying this data.

    When dragging an item from the Browser or FavWidget, we pass the FileItem object and it is up to the
    receiving browser on how to display data from that object. A reference to the file item is stored in the
    (View) object's data property.


    For example:

        FILE_ITEM_DATA_ROLE = 1
        QTableWidgetItem.setData(FILE_ITEM_DATA_ROLE, FileItem)

    Note:
        In following with Qt design Patterns, it is preferable to get/set values via properties in this class.
    """

    _file_info = QtCore.QFileInfo()
    _full_path = None
    _icon = None
    _nice_name = ""
    _clicked_times = 0
    _sort_token = ""


    def __init__(self, item_data: dict):

        self._color = [1.0, 1.0, 1.0, 1.0]

        self.__dict__.update(item_data)
        self._file_info = QtCore.QFileInfo(self._full_path)
        self._file_name = self._file_info.fileName()
        self._suffix = self._file_info.completeSuffix()

        if self.is_dir():
            self._suffix = "0"

        if not self._sort_token:
            self._sort_token = self._suffix + self._file_name

    def file_path(self):
        return self._full_path

    def file_name(self):
        return self._file_name

    def is_dir(self):
        return self._file_info.isDir()

    def file_info(self):
        return self._file_info

    def suffix(self):
        return self._suffix

    def sort_token(self):
        return self._sort_token

    def icon(self):
        return ICON_PROVIDER.icon(self._file_info)

    def set_color(self, color):
        if isinstance(color, QtGui.QColor):
            print(color.getRgbF())
            self._color = list(color.getRgbF())
        else:
            self._color = color

    def color(self):
        return self._color


class AbstractDockWindow:
    is_closed = Signal(object)
    new_browser = Signal(str)

    def __init__(self):
        pass

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

    def __init__(self):
        AbstractDockWindow.__init__(self)
        QtWidgets.QTabWidget.__init__(self)

        self.dir_path = ""

        self.setAcceptDrops(True)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_tab)
        self.currentChanged.connect(self.set_active)

    def set_title(self, title):
        idx = self.indexOf(self.currentWidget())
        self.setTabText(idx, title)
        # self.widget(idx).setWindowTitle(title)

    # def get_title(self):
    #     idx = self.indexOf(self._main_window.get_active_browser())
    #     return self.tabText(idx)

    def add_widget(self, browser_window, path=None, set_current=True):
        self.addTab(browser_window, browser_window.windowTitle())
        if set_current:
            self.setCurrentWidget(browser_window)
            self.currentWidget().is_active.emit(self.currentWidget())

    def remove_widget(self, widget):
        self.removeTab(self.indexOf(widget))

    def close_tab(self, *args):
        self.is_closed.emit(self.currentWidget())

    def clear_widgets(self):
        self.blockSignals(True)
        self.clear()
        self.blockSignals(False)

    def set_active(self):
        self.currentWidget().is_active.emit(self.currentWidget())

class DockWindow(AbstractDockWindow, QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        AbstractDockWindow.__init__(self)

        self.splitter = QtWidgets.QSplitter()
        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().addWidget(self.splitter)
        self._active = None
        self.layout().setContentsMargins(0,0,0,0)

    def add_widget(self, browser_window, path=None, set_current=True):
        dock_widget = DockWidget(browser_window)
        # dock_widget.closed_event.connect(partial(self._main_window.remove_browser, browser_window))
        self.splitter.addWidget(dock_widget)

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
        bar = self.titleBarWidget()
        color = QtGui.QColor("red")


        # self.browser_window.path_changed.connect(self.path_changed)
        self.setWidget(browser_window)
        # self.titleBarWidget().setBackgroundColor(color)
        self.setWindowTitle(browser_window._leaf)
        self.setFeatures(QtWidgets.QDockWidget.DockWidgetClosable)

    def closeEvent(self, event):
        self.browser_window.setParent(None)
        self.hide()
        self.setParent(None)
        self.setWidget(None)
        self.browser_window.is_closed.emit(self.browser_window)
        super().closeEvent(event)

    def release_browser(self):
        self.browser_window.setParent(None)

        self.setWidget(None)
        self.deleteLater()

    def path_changed(self, path):
        log.debug("Dock Widget Path Changed {}".format(path))
        leaf = os.path.split(path)[-1]
        self.setWindowTitle(leaf)

        pass


# CONTEXT WIDGETS
class PathLineEdit(QtWidgets.QLineEdit):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragEnabled(True)

    # def dragEnterEvent(self, event):
    #     print("Dragging! {}".format(type(self).__name__))


# BROWSER WIDGET TYPES TODO: Consolidate this into one class.


class BrowserWidget(QtWidgets.QWidget):
    _view_context = None
    is_active = Signal(object)
    is_closed = Signal(object)
    # path_changed = Signal(str)  # Path

    def __init__(self, main_window, browser_data=None):
        super().__init__()
        # self._main_window = main_window
        # Data
        self._leaf = ""
        self._full_path = ""
        self._items = []

        self._active = False

        # History
        self.history = []
        self.history_idx = 0

        self.central_layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.central_layout)
        self.layout().setContentsMargins(0, 5, 0, 0)

        # BROWSER PATH
        self.path_line_edit = PathLineEdit()
        self.central_layout.addWidget(self.path_line_edit)

        # VIEW CONTEXT
        # self.table_view = createView(QtWidgets.QTableWidget, FileTableWidget, main_window, ["file_name", "file_path"])
        self.table_view = FileViewWidget([FILE_NAME, FILE_PATH])
        self.table_view.is_active.connect(self.set_active)  # Signal

        self.list_view = FileViewWidget([FILE_NAME, FILE_PATH])
        # self.list_view = createView(QtWidgets.QListWidget, FileListWidget, main_window)
        self.list_view.is_active.connect(self.set_active)  # Signal

        self.central_layout.addWidget(self.list_view)
        self.central_layout.addWidget(self.table_view)
        self.set_view_context(TABLE_VIEW_MODE)

        # SIGNAL
        self.path_line_edit.textEdited.connect(self.set_path_edit)

        # Additional
        self.path_line_edit.setAutoFillBackground(True)
        self.table_view.setAutoFillBackground(True)
        self.list_view.setAutoFillBackground(True)

        if browser_data:
            self.__dict__.update(browser_data)

    def set_view_context(self, context: str):
        """
        Switch view context- Table, List or *Tree(might be supported in the future.)
        :param context: const IE: TABLE_VIEW_MODE
        """

        # TABLE
        if context == TABLE_VIEW_MODE and self._view_context is not self.table_view:
            self.list_view.hide()
            self.table_view.show()
            self._view_context = self.table_view

        # LIST
        elif context == LIST_VIEW_MODE and self._view_context is not self.list_view:
            self.table_view.hide()
            self.list_view.show()
            self._view_context = self.list_view

        if self._full_path:
            self.set_path(self._full_path, is_dir=True, history=False, set_text=False)

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
            # self.path_changed.emit(path)
            self._view_context.set_root_directory(path)
            if set_text:
                self.path_line_edit.setText(path)


            # TODO: This is ugly, make it clean.
            if history and not self.history or history and self.history[-1] != path:
                self.history.append(path)
                self.history_idx = len(self.history) -1


            # self._main_window.set_active_browser_title(self._leaf)

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

    def set_dir(self):
        item = self._view_context.currentItem()
        self.set_path(item.file_path(), is_dir=item.file_info.isDir())

    def mouseDoubleClickEvent(self, event):
        self.set_dir()
        self.set_active(True)

    def set_active(self, active=True):
        log.debug("Setting active Browser {}".format(self.windowTitle()))
        self.is_active.emit(self)
        # self._main_window.set_active_browser(self)

    # def mouseMoveEvent(self, event):
    #     print("Move!")


class BaseFileListWidget:  # MIXIN CLASS
    _context_menu = None
    _can_set_active = True
    _display_keys = ["file_name"]


    is_active = Signal()
    path_changed = Signal(object)
    new_tab = Signal(object)

    def __init__(self, *args):
        log.debug("init BaseFileWidget []".format(args))

        self._items = []
        self.setAcceptDrops(True)
        self.setDragEnabled(True)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        if not self._context_menu:
            self.setup_context_menu()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.is_active.emit()

    def show_context_menu(self, pos):
        self._context_menu.exec_(self.mapToGlobal(pos))

    def dragEnterEvent(self, event):
        log.debug("BaseFileWidget Dagging!")
        global _drop_message
        if _drop_message:
            event.accept()
            return

        file_items = []
        for i in self.selectedItems():
            file_items.append(i.item)
        _drop_message = file_items
        event.accept()

    def dropEvent(self, event):
        log.debug("Base Widget Dropped!")
        global _drop_message
        if _drop_message:
            log.debug("Dropped Items, {}".format(_drop_message))
            for item in _drop_message:
                self.add_item(item)

        _drop_message = []

    def add_item(self, *args, **kwargs):
        raise NotImplementedError

    def get_items(self):
        return self._items


    def show_in_explorer(self):
        item = self.current_file_item()
        if not item:
            os.startfile(self.parent().get_path())
        if item.is_dir():
            os.startfile(item.file_path())
        else:
            os.startfile(os.path.dirname(item.file_path()))

    def setup_context_menu(self):
        self._context_menu = QtWidgets.QMenu()

        # Base Menu Actions
        open_in_new_tab = self._context_menu.addAction("Open in new tab")
        open_in_new_tab.triggered.connect(self.open_in_new_tab)

        show_in_explorer = self._context_menu.addAction("Show in Explorer")
        show_in_explorer.triggered.connect(self.show_in_explorer)

        copy_path = self._context_menu.addAction("Copy Path")
        # copy_path.triggered.connect(self.copy_path)

        select_view_submenu = self._context_menu.addMenu("View")
        set_table = select_view_submenu.addAction("Details")
        set_table.triggered.connect(partial(self.set_view, TABLE_VIEW_MODE))

        set_list = select_view_submenu.addAction("List")
        set_list.triggered.connect(partial(self.set_view, LIST_VIEW_MODE))

    def set_view(self, view: str):
        print("setting view: {}".format(view))
        browser = self._main_window.get_active_browser()
        browser.set_view_context(view)

    def open_in_new_tab(self):
        for i in self.selectedItems():
            item = i.item
            if item.is_dir():
                self.new_tab.emit(item)



    def mouseDoubleClickEvent(self, event):
        self.open()
        # self.currentItem().clicked_times -= 1
        # log.debug(self.currentItem().clicked_times)

    def open(self):
        item = self.current_file_item()
        print("got item {}".format(item))
        if item.is_dir():
            self.path_changed.emit(item)

            # browser = self._main_window.get_active_browser()
            # browser.set_path(item.file_path(), is_dir=item.is_dir())
        else:
            os.startfile(item.file_path())

    def current_file_item(self):
        item = self.currentItem()
        return item.item


class FileTableWidget(BaseFileListWidget, QtWidgets.QTableWidget):

    def __init__(self, display_keys: list):
        """
        :param display_keys: Table Columns to display.
        IE:

        """
        print("Initialize FileTableWidget")
        QtWidgets.QTableWidget.__init__(self)
        BaseFileListWidget.__init__(self)

        # Cells we wish to display from FileItems in the list.
        self.directory = ""
        self._display_keys = display_keys
        self.setColumnCount(len(display_keys))
        self.setRowCount(1)

        # Setup table appearance
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)

        self.verticalHeader().hide()

    def set_display_keys(self):
        pass

    def clear(self):
        super().clear()
        self.setRowCount(0)

    def add_item(self, item: FileItem):
        """
        Create a row and populate it with values from the FileItem.__dict__
        base on self._display_keys that have been set.
        :param item:
        :return:
        """
        print("adding item {}".format(item))
        self._items.append(item)

        row = self.rowCount()
        self.setRowCount(row + 1)

        table_items = []

        for key in self._display_keys:
            if hasattr(item, key):
                attr = getattr(item, key)
                value = str(attr())
                table_item = QtWidgets.QTableWidgetItem(value)
                table_item.item = item
                if item.color():
                    color = QtGui.QColor()
                    color.setRgbF(*item.color())
                    table_item.setBackgroundColor(color)

                # table_item.setData(FILE_ITEM_DATA_ROLE, item)
            else:
                table_item = QtWidgets.QTableWidgetItem("NO DATA {}".format(key))

            table_items.append(table_item)

        # Set icon for first item in the list.
        table_items[0].setIcon(item.icon())

        # Add table_items to the row
        for col, table_item in enumerate(table_items):
            self.setItem(row, col, table_item)

class FileViewWidget(FileTableWidget):
    def __init__(self, display_keys: list):
        super(FileViewWidget, self).__init__(display_keys)

    def set_root_directory(self, directory):
        log.debug("Table Widget Setting Root {}".format(directory))

        self.clear()
        self.directory = directory
        items = os.listdir(directory)

        for row, path in enumerate(items):
            full_path = os.path.join(directory, path)
            full_path = full_path.replace('\\', '/')
            file_item = FileItem({'_full_path': full_path})
            self.add_item(file_item)
        # self.sortItems()

        self.setHorizontalHeaderLabels(self._display_keys)

class FavWidget(FileTableWidget):
    def __init__(self, items, name):
        super(FavWidget, self).__init__([FILE_NAME])
        self.setRowCount(0)
        self.horizontalHeader().hide()

        if items:
            for i in items:
                self.add_item(FileItem(i))

        self.setObjectName(name)

    def setup_context_menu(self):
        super().setup_context_menu()
        rename_pin = self._context_menu.addAction("Rename Pin")
        rename_pin.triggered.connect(self.rename_pin)

        delete_pins = self._context_menu.addAction("Delete Pins")
        delete_pins.triggered.connect(self.delete_pins)

        set_pin_color = self._context_menu.addAction("Set Color")
        set_pin_color.triggered.connect(self.set_pin_color)

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
    #
    def set_pin_color(self):
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            print("color is valid!")

        for widget in self.selectedItems():
            widget.setBackgroundColor(color)
            widget.item.set_color(color)

    def set_sort(self, sort_type):
        for i in range(self.count()):
            w = self.item(i)


            if sort_type == "Name":
                w.sort_token = w.text()
            if sort_type == "File Type":
                w.sort_token = w.suffix + w.text()
            if sort_type == "Usage":
                w.sort_token = w.clicked_times

        self.sortItems()

    def delete_pins(self):
        items = []

        while self.selectedItems():
            widget = self.selectedItems()[0]
            item = widget.item
            if item in self._items:
                self._items.remove(item)

            self.removeRow(self.row(widget))


        print("Deleted Pins, left {}".format(self.get_items()))

    def rename_pin(self):
        flags = self.currentItem().flags()
        self.currentItem().setFlags(flags | QtCore.Qt.ItemIsEditable)
        self.edit(self.currentIndex())


