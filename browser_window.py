from PySide2 import QtWidgets, QtCore, QtGui, QtSvg
from PySide2.QtCore import Signal
import shutil
import abc
import os
import sys
import json
import logging
import traceback
import subprocess


logging.basicConfig()
log = logging.getLogger(__name__)

TOOL_BAR_BUTTON_WIDTH = 40

DIRECTORY = os.path.split(os.path.dirname(__file__))[-1]
SETTINGS_PATH = os.path.join(os.environ['APPDATA'], DIRECTORY, 'data', 'save_data.json')
TEST_PATH = 'C:/Users/Neil/Desktop'

ICON_PATH = os.path.dirname(__file__) + "/icons"
print(ICON_PATH)

DOCK_WIDGET_VIEW_MODE = "Dock Widgets"
TAB_VIEW_MODE = "Tabs"


ACTIVE_STYLE = "QWidget { background-color: rgba(255, 255, 255, 128);}"
INACTIVE_STYLE = "QWidget { background-color: rgba(128, 128, 128, 50);}"


# Save Data keys
FULL_PATH = "_full_path"
BROWSERS = "browsers"
PIN_LISTS = "pin_lists"
PIN_LIST_DATA = "pin_list_data"
NAME = "name"
FAV_WIDGET_NAME = "fav_widget_name"
FAV_WIDGET_PINS = 'fav_widget_pins'



class AbstractDockWindow:
    @abc.abstractmethod
    def add_widget(self, browser_window, path=None):
        pass
    @abc.abstractmethod
    def set_title(self, title):
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
        super().__init__()

        self.dir_path = ""

        self.setAcceptDrops(True)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_tab)
        self.currentChanged.connect(self.set_active)

    def set_title(self, title):
        idx = self.indexOf(MainWindow().get_active_browser())
        self.setTabText(idx, title)

    def add_widget(self, browser_window, path=None, set_current=True):
        self.addTab(browser_window, browser_window.windowTitle())
        if set_current:
            self.setCurrentWidget(browser_window)
            MainWindow().set_active_browser(browser_window)

    def populate(self):
        self.blockSignals(True)
        for w in MainWindow().get_browser_list():
            self.add_widget(w, set_current=False)
        self.setCurrentWidget(MainWindow().get_active_browser())
        self.blockSignals(False)

    def remove_widget(self, widget):
        self.removeTab(self.indexOf(widget))

    def close_tab(self, *args):
        MainWindow().remove_browser(self.widget(args[0]))

    def clear_widgets(self):
        self.blockSignals(True)
        self.clear()
        self.blockSignals(False)

    def set_active(self):
        MainWindow().set_active_browser(self.currentWidget())


class DockWindow(AbstractDockWindow, QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.splitter = QtWidgets.QSplitter()
        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().addWidget(self.splitter)
        self._active = None
        self.layout().setContentsMargins(0,0,0,0)


    def set_active(self, *args):
        pass

    def set_title(self, title):
        dock = MainWindow().get_active_browser()
        if dock:
            dock.parent().setWindowTitle(title)

    def add_widget(self, browser_window, path=None, set_current=True):
        dock_widget = DockWidget(browser_window)
        dock_widget.closed_event.connect(MainWindow().remove_browser)
        self.splitter.addWidget(dock_widget)

    def remove_widget(self, dock_widget):
        MainWindow().remove_browser(dock_widget)

    def populate(self):
        for w in MainWindow().get_browser_list():
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


    # def dragEnterEvent(self, event):
    #     print("Doc Drag!")

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


class BaseListWidget(QtWidgets.QListWidget):
    name = ""
    _context_menu = None

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self._context_menu = QtWidgets.QMenu()
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

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
            MainWindow().get_active_browser().set_path(item.file_path(),
                                                       is_dir=item.file_info.isDir())
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
            MainWindow().add_browser({"_full_path": self.currentItem().file_path()})
        else:
            MainWindow().add_browser({"_full_path": os.path.dirname(item.file_path())})

    def show_context_menu(self, pos):
        self._context_menu.exec_(self.mapToGlobal(pos))


class FavWidget(QtWidgets.QTreeWidget):
    def __init__(self, items=None, name=""):
        super().__init__()

        # Serializable Data
        self._items = []
        self.setObjectName(name)

        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self._context_menu = QtWidgets.QMenu()
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)


        self.setColumnCount(2)
        self.header().resizeSection(0, 3)
        # self.setAlternatingRowColors(True)

        self.header().hide()
        self.setIndentation(0)


        self.add_menu_actions()

        if items:
            for i in items:
                self.add_pin(i)

    def add_pin(self, item_data):
        new_pin = FileTreeItemWidget(item_data)
        self._items.append(new_pin)
        self.addTopLevelItem(new_pin)
        self.setItemSelected(new_pin, True)

    def pins(self):
        return self._items

    def dropEvent(self, event):
        message = MainWindow().get_drag_message()
        if not message:
            return
        if not isinstance(message, list):
            message = [message]
        for i in message:
            self.add_pin(i.__dict__)

        for i in self._items:
            self.setItemSelected(i, False)

        # self.add_pin(message[0].__dict__)

        MainWindow().set_drag_message(None)
        MainWindow().is_dragging = False

    def add_menu_actions(self):
        rename_pin = self._context_menu.addAction("Rename Pin")
        rename_pin.triggered.connect(self.rename_pin)

        delete_pins = QtWidgets.QAction("Delete Pins", self)
        delete_pins.triggered.connect(self.delete_pins)
        self._context_menu.addAction(delete_pins)

    def delete_pins(self):
        for i in self.selectedItems():
            self._items.remove(i)
            self.takeTopLevelItem(self.indexOfTopLevelItem(i))

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        # self.setCurrentIndex(self.indexAt(event.pos))
        # print(self.currentIndex())

    def open(self):
        item = self.currentItem()
        if item.is_dir():
            MainWindow().get_active_browser().set_path(item.file_path(),
                                                       is_dir=item.file_info.isDir())
        else:
            os.startfile(item.file_path())

    def rename_pin(self):
        flags = self.currentItem().flags()
        self.currentItem().setFlags(flags | QtCore.Qt.ItemIsEditable)
        self.edit(self.currentIndex())

    def mouseDoubleClickEvent(self, event):
        self.open()

    def show_context_menu(self, pos):
        self._context_menu.exec_(self.mapToGlobal(pos))


class PinListWidget(BaseListWidget):
    name = ""

    def __init__(self, items=None, widget_data=None):
        super().__init__()

        # Context Menu
        self.add_menu_actions()

        if items:
            for i in items:
                self.add_pin(i)
        if widget_data:
            self.__dict__.update(widget_data)

    def open(self):
        item = self.currentItem()
        assert isinstance(item, FileItemWidget)

        if item.is_dir():
            MainWindow().get_active_browser().set_path(item.file_path(),
                                                       is_dir=item.file_info.isDir())
            MainWindow().set_active_browser_title(item.text())

        else:
            os.startfile(item.file_path())

    def dropEvent(self, event):
        # print("Dropped! {}".format(type(self).__name__))
        message = MainWindow().get_drag_message()
        if not message:
            return


        if not isinstance(message, list):
            message = [message]

        for i in message:
            print(i.__dict__.keys())
            self.add_pin(i)

        MainWindow().set_drag_message(None)
        MainWindow().is_dragging = False

    def add_pin(self, item_data):
        if isinstance(item_data, FileItemWidget):
            new_pin = FileItemWidget(item_data.__dict__)
        elif isinstance(item_data, dict):
            new_pin = FileItemWidget(item_data)
        else:
            raise TypeError

        self.addItem(new_pin)

    def add_menu_actions(self):
        rename_pin = self._context_menu.addAction("Rename Pin")
        rename_pin.triggered.connect(self.rename_pin)

        delete_pins = QtWidgets.QAction("Delete Pins", self)
        delete_pins.triggered.connect(self.delete_pins)
        self._context_menu.addAction(delete_pins)

    def delete_pins(self):

        for i in self.selectedItems():
            print(i)
            self.takeItem(self.row(i))

    def rename_pin(self):
        flags = self.currentItem().flags()
        self.currentItem().setFlags(flags | QtCore.Qt.ItemIsEditable)
        self.edit(self.currentIndex())



        # dialog = QtWidgets.QInputDialog(MainWindow())
        # dialog.setWindowTitle("Rename Pin")
        # dialog.setLabelText("This will NOT rename the file / folder.")
        # dialog.finished.connect(lambda x: print(dialog.textValue()))
        # dialog.show()
        # print(dialog.result())

        pass

    def open_new_tab(self):
        pass


class FileListWidget(BaseListWidget):

    def __init__(self):
        super().__init__()
        # self.setLayout(QtWidgets.QHBoxLayout())
        # self.additional_icon_widget = QtWidgets.QWidget()
        # self.layout().addWidget(self.additional_icon_widget)


        self.directory = ""
        self.icon_provider = QtWidgets.QFileIconProvider()
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
            self.addItem(item_widget)

    def add_drop_context_menu_options(self):
        copy_files = self._drop_menu.addAction("Copy")
        copy_files.triggered.connect(self.copy_files)
        move_files = self._drop_menu.addAction("Move")
        move_files.triggered.connect(self.move_files)
        self._drop_menu.addAction("Cancel")

    def copy_files(self):
        for i in MainWindow().get_drag_message():
            new_path = os.path.join(self.directory, i.file_name)
            if i.is_dir():
                shutil.copytree(i.file_path(), new_path)
            else:
                shutil.copy(i.file_path(), new_path)
        # TODO: hack to refresh, implement real refresh later.
        self.parent().set_path(self.directory, is_dir=True)

    def move_files(self):
        for i in MainWindow().get_drag_message():
            new_path = os.path.join(self.directory, i.file_name)
            if i.is_dir():
                shutil.move(i.file_path(), new_path)
            else:
                shutil.move(i.file_path(), new_path)

        # TODO: hack to refresh, implement real refresh later.
        self.parent().set_path(self.directory, is_dir=True)
        active_browser = MainWindow().get_active_browser()
        active_browser.set_path(active_browser.get_path(), is_dir=True)

    def delete_files(self):
        for i in self.selectedItems():
            if i.is_dir():
                shutil.rmtree(i.file_path())
            else:
                os.remove(i.file_path())
        self.parent().set_path(self.directory, is_dir=True)

    def dragMoveEvent(self, event):
        if MainWindow().is_dragging:
            return
        MainWindow().is_dragging = True

    def dropEvent(self, event):
        print("Dropped! {}".format(self.directory))
        self._drop_menu.exec_(self.mapToGlobal(event.pos()))
        MainWindow().is_dragging = False
        MainWindow().set_drag_message(None)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        MainWindow().set_active_browser(self.parent())

        # Set active selection
        MainWindow().set_drag_message(self.selectedItems())


class PathLineEdit(QtWidgets.QLineEdit):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragEnabled(True)

    # def dragEnterEvent(self, event):
    #     print("Dragging! {}".format(type(self).__name__))


class FileTreeItemWidget(QtWidgets.QTreeWidgetItem):
    file_info = QtCore.QFileInfo()

    def __init__(self, item_data: dict):
        super().__init__()
        # self.__dict__.update(item_data)
        self.full_path = item_data['full_path']


        self.file_info = QtCore.QFileInfo(self.full_path)
        self.file_name = self.file_info.fileName()


        if 'nice_name' not in self.__dict__.keys():
            self.nice_name = self.file_name
        self.setText(1, self.__dict__['nice_name'])

        icon_provider = QtWidgets.QFileIconProvider()
        icon = icon_provider.icon(self.file_info)
        self.setIcon(1, icon)
        self.setToolTip(1, self.full_path)

        self.setIcon(0, QtGui.QIcon(os.path.join(ICON_PATH, "circle-solid.svg")))


    def is_dir(self):
        return self.file_info.isDir()

    def file_path(self):
        return self.full_path


class FileItemWidget(QtWidgets.QListWidgetItem):
    """
    This widget stores all information on a file path.
    """

    file_info = QtCore.QFileInfo()


    def __init__(self, item_data: dict):
        super().__init__()

        self.__dict__.update(item_data)
        self.file_info = QtCore.QFileInfo(self.full_path)
        self.file_name = self.file_info.fileName()

        if 'nice_name' not in self.__dict__.keys():
            self.nice_name = self.file_name

        self.setText(self.__dict__['nice_name'])

        icon_provider = QtWidgets.QFileIconProvider()
        icon = icon_provider.icon(self.file_info)
        self.setIcon(icon)

        self.setToolTip(self.full_path)

    def file_path(self):
        return self.full_path

    def is_dir(self):
        return self.file_info.isDir()


class MainWindow(QtWidgets.QMainWindow):
    """
    Singleton Class
    """
    _instance = None
    _initialized = False

    # Context for the browser widgets, can be tabs or dock widgets or whatever layout we choose.
    _browser_context = None
    _pin_context = None
    _drag_message = None
    _save_data = None


    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()

        # Prevent multiple widgets from entering a drag event.
        self.is_dragging = False

        # Style
        # self.setStyleSheet("QGroupBox {border: 0px;}\n"
        #                    "QWidget {background-color: #31363b;"
        #                    "padding: 0 0 0 0;"
        #                    "border-spacing: 0px 0px;"
        #                    "margin: 0px;}")

        self._browser_widgets_list = []
        self._active = None

        self.setCentralWidget(QtWidgets.QWidget())
        self.centralWidget().setLayout(QtWidgets.QVBoxLayout())
        self.c_layout = self.centralWidget().layout()

        # Tab Widget
        self.tab_widget = TabWindow()
        self.tab_widget.hide()

        # Dock Widget
        self.dock_widget = DockWindow()
        self.dock_widget.hide()

        # Initial Context
        self._browser_context = self.dock_widget

        # Tool Bar
        self.tool_bar = QtWidgets.QGroupBox()
        self.tool_bar.setLayout(QtWidgets.QHBoxLayout())
        self.c_layout.addWidget(self.tool_bar)
        self.tool_bar.setMaximumHeight(TOOL_BAR_BUTTON_WIDTH)
        # self.centralWidget().layout().setContentsMargins(0,0,0,0)
        # self.tool_bar.layout().setContentsMargins(3,3,3,3)


        # Back Button
        self.back_btn = QtWidgets.QPushButton()
        self.back_btn.setMaximumWidth(TOOL_BAR_BUTTON_WIDTH)
        self.back_btn.setIcon(QtGui.QIcon(os.path.join(ICON_PATH, "chevron-left.svg")))
        self.tool_bar.layout().addWidget(self.back_btn)

        # Forward Button
        self.forward_btn = QtWidgets.QPushButton()
        self.forward_btn.setMaximumWidth(TOOL_BAR_BUTTON_WIDTH)
        self.forward_btn.setIcon(QtGui.QIcon(os.path.join(ICON_PATH, "chevron-right.svg")))
        self.tool_bar.layout().addWidget(self.forward_btn)

        # Directory up button
        self.up_btn = QtWidgets.QPushButton()
        self.up_btn.setMaximumWidth(TOOL_BAR_BUTTON_WIDTH)
        self.up_btn.setIcon(QtGui.QIcon(os.path.join(ICON_PATH, "chevron-up.svg")))
        self.tool_bar.layout().addWidget(self.up_btn)

        # View Toggle
        self.view_toggle_btn = QtWidgets.QPushButton()
        self.view_toggle_btn.setMaximumWidth(TOOL_BAR_BUTTON_WIDTH)
        self.view_toggle_btn.setIcon(QtGui.QIcon(os.path.join(ICON_PATH, "columns.svg")))
        self.tool_bar.layout().addWidget(self.view_toggle_btn)

        # View Mode
        # self.browser_context_combo = QtWidgets.QComboBox()
        # self.browser_context_combo.addItem(DOCK_WIDGET_VIEW_MODE)
        # self.browser_context_combo.addItem(TAB_VIEW_MODE)
        # self.tool_bar.layout().addWidget(self.browser_context_combo)

        # Open Tab
        self.open_tab_btn = QtWidgets.QPushButton()
        self.open_tab_btn.setMaximumWidth(TOOL_BAR_BUTTON_WIDTH)
        self.open_tab_btn.setIcon(QtGui.QIcon(os.path.join(ICON_PATH, "plus-circle.svg")))
        self.tool_bar.layout().addWidget(self.open_tab_btn)
        self.tool_bar.layout().addStretch()

        # Fav Toggle
        self.hamburger_btn = QtWidgets.QPushButton()
        self.hamburger_btn.setMaximumWidth(TOOL_BAR_BUTTON_WIDTH)
        self.hamburger_btn.setIcon(QtGui.QIcon(os.path.join(ICON_PATH, "menu.svg")))
        self.tool_bar.layout().addWidget(self.hamburger_btn)

        self.lower_grp = QtWidgets.QGroupBox()
        self.c_layout.addWidget(self.lower_grp)
        self.lower_grp.setLayout(QtWidgets.QHBoxLayout())
        self.lower_grp.layout().setContentsMargins(0,0,0,0)
        self.lower_grp.layout().setMargin(2)
        self.lower_grp.layout().setSpacing(0)

        # Pin Group
        self.pin_grp = QtWidgets.QGroupBox()
        self.pin_grp.setLayout(QtWidgets.QVBoxLayout())
        self.pin_grp.layout().setContentsMargins(0, 0, 0, 0)
        self.pin_tool_bar = QtWidgets.QGroupBox()
        self.pin_tool_bar.setLayout(QtWidgets.QHBoxLayout())
        self.pin_grp.layout().addWidget(self.pin_tool_bar)

        # Pin Combo
        self.pin_combo = QtWidgets.QComboBox()
        self.pin_combo.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.pin_combo.customContextMenuRequested.connect(self.show_pin_combo_context_menu)
        self._pin_combo_context_menu = QtWidgets.QMenu()
        self.add_pin_combo_menu_actions()
        self.pin_tool_bar.layout().addWidget(self.pin_combo)
        self.pin_tool_bar.layout().setContentsMargins(0,0,0,0)

        # Pin List
        self.pin_grp.setMaximumWidth(200)
        self.pin_grp.setMinimumWidth(200)

        self.lower_grp.layout().addWidget(self.pin_grp)
        self.lower_grp.layout().addWidget(self.tab_widget)
        self.lower_grp.layout().addWidget(self.dock_widget)

        # Signals
        self.back_btn.clicked.connect(lambda : self.get_active_browser().back())
        self.up_btn.clicked.connect(lambda : self.get_active_browser().up())
        self.forward_btn.clicked.connect(lambda : self.get_active_browser().forward())


        func = lambda : self.set_active_pin_tray(self.pin_combo.itemData(self.pin_combo.currentIndex()))
        self.pin_combo.currentIndexChanged.connect(func)


        self.open_tab_btn.clicked.connect(self.add_browser)
        # self.browser_context_combo.currentIndexChanged.connect(self.set_view_context)
        self.view_toggle_btn.clicked.connect(self.toggle_view_context)

        # init
        self._initialized = True

    def show_pin_combo_context_menu(self, pos):
        self._pin_combo_context_menu.exec_(self.pin_combo.mapToGlobal(pos))

    def add_pin_combo_menu_actions(self):
        add_tray = self._pin_combo_context_menu.addAction("Add Pin List")
        add_tray.triggered.connect(self.new_fav_list_dialog)

        rename_tray = self._pin_combo_context_menu.addAction("Rename Pin List")
        rename_tray.triggered.connect(self.rename_fav_list_dialog)


        delete_tray = self._pin_combo_context_menu.addAction("Delete Pin List")
        delete_tray.triggered.connect(self.remove_tray_dialog)

    def remove_tray_dialog(self):
        dialog = QtWidgets.QMessageBox(self)
        dialog.setWindowTitle("Delete pin list")

        tray_name = self.pin_combo.currentText()
        dialog.setText("Are you sure you want to delete list {}. \n"
                            "This is not undoable.".format(tray_name))
        func = lambda : self.remove_pin_tray()
        dialog.accepted.connect(func)
        dialog.show()

    def new_fav_list_dialog(self):
        dialog = QtWidgets.QInputDialog(self)
        dialog.setWindowTitle("New pin list")
        dialog.setLabelText("List name")
        func = lambda : self.add_fav_list(widget_data={NAME: dialog.textValue()})
        dialog.accepted.connect(func)
        dialog.move(self.pin_combo.mapToGlobal(self.pin_combo.pos()))
        dialog.show()

    def set_fav_list_name(self, idx, name):
        self.pin_combo.setItemText(idx, name)
        fav_widget = self.pin_combo.itemData(idx)
        fav_widget.setObjectName(name)


    def rename_fav_list_dialog(self):
        dialog = QtWidgets.QInputDialog(self)
        dialog.setWindowTitle("Rename pin list")
        dialog.setLabelText("New name")
        dialog.setTextValue(self.pin_combo.currentText())

        func = lambda: self.set_fav_list_name(self.pin_combo.currentIndex(),dialog.textValue())
        dialog.accepted.connect(func)

        dialog.move(self.pin_combo.mapToGlobal(self.pin_combo.pos()))
        dialog.show()

    def set_view_context(self, context=DOCK_WIDGET_VIEW_MODE):
        if self._browser_context:
            self._browser_context.clear_widgets()
            self._browser_context.hide()

        if context == DOCK_WIDGET_VIEW_MODE:
            self._browser_context = self.dock_widget
        elif context == TAB_VIEW_MODE:
            self._browser_context = self.tab_widget

        self._browser_context.show()
        self._browser_context.populate()

    def toggle_view_context(self):
        print("setting active browser! {}".format(self._active))
        # self.set_active_browser(self._active)

        if self._browser_context:
            self._browser_context.clear_widgets()
            self._browser_context.hide()

        print("Cleared widgets! {}".format(self._active))

        if self._browser_context == self.dock_widget:
            self._browser_context = self.tab_widget

        else:
            self._browser_context = self.dock_widget

        self._browser_context.show()
        self._browser_context.populate()

    def set_pin_context(self, pin_list):
        """
        Set active pin list
        :return:
        """
        self._pin_context.hide()
        self._pin_context = pin_list
        self._pin_context.show()

    def save_pin_lists(self):
        save_data = {}
        browser_data = {}
        for num, b in enumerate(self._browser_widgets_list):
            browser_data["browser_" + str(num)] = serialize(b)

        pin_list_data = {}

        for num in range(self.pin_combo.count()):
            fav_list = self.pin_combo.itemData(num)
            assert isinstance(fav_list, FavWidget)

            pin_list_items = []
            for i in fav_list.pins():
                pin_list_items.append(serialize(i))

            key = 'fav_list_' + fav_list.objectName() + str(num)
            pin_list_data[key] = {FAV_WIDGET_NAME : fav_list.objectName(),
                                  FAV_WIDGET_PINS : pin_list_items}


        if not os.path.exists(os.path.dirname(SETTINGS_PATH)):
            os.makedirs(os.path.dirname(SETTINGS_PATH))


        save_data[PIN_LISTS] = pin_list_data
        save_data[BROWSERS] = browser_data
        print("Saving Pin List data {} \n {}".format(SETTINGS_PATH, save_data))


        with open(SETTINGS_PATH, 'w') as f:
            json.dump(save_data, f)

    def load_saved_data(self):


        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, 'r') as f:
                self._save_data = json.load(f)

        if not self._save_data:
            return

        # Load browsers
        # for k, v in self._save_data[BROWSERS].items():
        #     self.add_browser(v)

        for k, v in self._save_data[PIN_LISTS].items():
            print("loading fav list {} \n {}".format(k, v))
            self.add_fav_list(items=v[FAV_WIDGET_PINS], name=v[FAV_WIDGET_NAME])

        # Make sure we have at least one pin list
        if not self.pin_combo.count():
            self.add_fav_list()



        # for k in self._save_data.keys():
        #     self._pin_widgets_list.append(PinListWidget(self._save_data[k]))

    def remove_pin_tray(self):
        idx = self.pin_combo.currentIndex()
        widget = self.pin_combo.itemData(idx)
        self.pin_combo.removeItem(idx)
        widget.deleteLater()

    def add_fav_list(self, items=None, widget_data=None, name=""):
        """
        :param items: list
        :param widget_data: Serialized class data
        :param name: str
        :return:
        """

        fav_widget = FavWidget(items, name=name)

        if not name:
            if widget_data and NAME in widget_data.keys():
                name = widget_data[NAME]
            else:
                name = "Pin List {}".format(self.pin_combo.count())

        self.pin_combo.addItem(name, fav_widget)
        self.pin_grp.layout().addWidget(fav_widget)
        self.pin_combo.setCurrentIndex(self.pin_combo.count() -1)

    def set_active_pin_tray(self, tray):
        for idx in range(self.pin_combo.count()):
            i = self.pin_combo.itemData(idx)
            if i == tray:
                i.show()
            else:
                i.hide()

    def set_active_browser_title(self, title):
        self._browser_context.set_title(title)

    def add_browser(self, browser_data=None):
        browser_window = BrowserWidget(browser_data)
        self._browser_widgets_list.append(browser_window)
        self._browser_context.add_widget(browser_window)
        self.set_active_browser(browser_window)
        if browser_data:
            self.get_active_browser().set_path(browser_data[FULL_PATH], is_dir=True)
        else:
            self.get_active_browser().set_path(TEST_PATH, is_dir=True)

    def remove_browser(self, browser_widget):
        print("Removing widget {}".format(id(browser_widget)))
        if browser_widget in self._browser_widgets_list:
            print("Removing widget {}")
            self._browser_widgets_list.remove(browser_widget)
            self._browser_context.remove_widget(browser_widget)
        if self._active == browser_widget:
            if self._browser_widgets_list:
                self.set_active_browser(self._browser_widgets_list[0])
            else:
                self.set_active_browser(None)

    def get_browser_list(self):
        return self._browser_widgets_list

    def get_active_browser(self):
        return self._active

    def set_active_browser(self, browser):
        if browser is None:
            print(traceback.print_stack())
            raise TypeError("")

        print("setting active browser {}".format(browser.windowTitle()))

        for w in self._browser_widgets_list:
            w.setStyleSheet(INACTIVE_STYLE)
        self._active = browser
        if browser:
            browser.setStyleSheet(ACTIVE_STYLE)

    def set_drag_message(self, message):
        self._drag_message = message

    def get_drag_message(self):
        return self._drag_message

    def closeEvent(self, *args):
        self.save_pin_lists()

    def showEvent(self, *args):
        self.load_saved_data()


class BrowserWidget(QtWidgets.QWidget):

    def __init__(self, browser_data=None):
        super().__init__()

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
        self.list_view = FileListWidget()
        self.central_layout.addWidget(self.list_view)

        # SIGNAL
        self.path_line_edit.textEdited.connect(self.set_path_edit)

        if browser_data:
            self.__dict__.update(browser_data)
        #     self.set_path(self._full_path, is_dir=True)
        # else:
        #     self.set_path("c:/", is_dir=True)

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

                print(self.history)
                self.history_idx = len(self.history) -1
            MainWindow().set_active_browser_title(self._leaf)

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
        MainWindow().pin_list.add_pin(item.file_path())

    def set_dir(self):
        item = self.list_view.currentItem()
        self.set_path(item.file_path(), is_dir=item.file_info.isDir())

    def mouseDoubleClickEvent(self, event):
        self.set_dir()
        self.set_active(True)

    def set_active(self, active:bool):
        MainWindow().set_active_browser(self)

    def mouseMoveEvent(self, event):
        print("Move!")


def serialize(obj):

    serializable_types = [int, list, dict, float, str]

    obj_data = {}
    for k, v in obj.__dict__.items():
        print(v)
        can_serialize = False
        for i in serializable_types:
           if isinstance(v, i):
               can_serialize = True

        if can_serialize:
            obj_data[k] = v

    return obj_data


def set_theme(app, stylesheet_path):
    file = QtCore.QFile(stylesheet_path)
    file.open(QtCore.QFile.ReadOnly | QtCore.QFile.Text)
    stream = QtCore.QTextStream(file)
    app.setStyleSheet(stream.readAll())



if __name__ == '__main__':


    app = QtWidgets.QApplication(sys.argv)

    window = MainWindow()
    window.resize(800, 500)

    window.setWindowTitle('File Browser')
    window.set_view_context(DOCK_WIDGET_VIEW_MODE)
    window.show()

    # window.set_view_context()
    window.add_browser({FULL_PATH: TEST_PATH})

    STYLE_SHEET_PATH = "./stylesheets/light_theme.css"
    # set_theme(app, STYLE_SHEET_PATH)

    sys.exit(app.exec_())
