"""
@Author Neil Berard
Entry point for File-Browser. Create a MainWindow and show it.
"""
import functools
import json
import logging
import os
import sys
import time
import traceback


from PySide2 import QtWidgets, QtCore, QtGui
from PySide2.QtCore import Signal

from libs import utils
from libs.widgets import TabWindow, DockWindow, BrowserWidget, FavWidget, FileItem, SearchOptionsWidget
from libs.consts import *

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


DOCK_WIDGET_VIEW_MODE = "Dock Widgets"
TAB_VIEW_MODE = "Tabs"

ACTIVE_STYLE = "QWidget { background-color: rgba(255, 255, 255, 128); selection-background-color: rgba(255, 255, 255, 10}"
INACTIVE_STYLE = "QWidget { background-color: rgba(128, 128, 128, 50);selection-background-color: rgba(255, 255, 255, 50)}"


# Save Data keys
FULL_PATH = "_full_path"
BROWSERS = "browsers"
PIN_LISTS = "pin_lists"
PIN_LIST_DATA = "pin_list_data"
NAME = "name"
FAV_WIDGET_NAME = "fav_widget_name"
FAV_WIDGET_PINS = 'fav_widget_pins'

SEARCH_TAB_TITLE = "Search Results"
MAX_RESULTS = 200


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
    _filter = None

    cancel_search = Signal()
    start_search = Signal(object)
    update_search = Signal(object)     # Send filter to active thread.


    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()

        # Custom Signals



        # Prevent multiple widgets from entering a drag event.
        self.is_dragging = False

        # Style
        # self.setStyleSheet("QGroupBox {border: 0px;}\n"
        #                    "QWidget {background-color: #31363b;"
        #                    "padding: 0 0 0 0;"
        #                    "border-spacing: 0px 0px;"
        #                    "margin: 0px;}")

        # SETTINGS
        # ========================================
        self._settings_path = os.path.join(SETTINGS_DIR, "main_window.ini")
        self._settings = QtCore.QSettings(self._settings_path, QtCore.QSettings.IniFormat)
        self._settings.setFallbacksEnabled(False)

        self._data_path = os.path.join(DATA_DIR, "browser_data.json")


        self._browser_widgets_list = []
        self._active = None
        self._search_delay = 0.3
        self._search_text_entered_time = None

        self.setCentralWidget(QtWidgets.QWidget())
        self.centralWidget().setLayout(QtWidgets.QVBoxLayout())
        self.c_layout = self.centralWidget().layout()


        # Tab Widget
        self.tab_widget = TabWindow()
        self.tab_widget.is_closed.connect(self.remove_browser)
        self.tab_widget.hide()

        # Dock Widget
        self.dock_widget = DockWindow()
        self.dock_widget.is_closed.connect(self.remove_browser)
        self.dock_widget.hide()

        # Initial Context: Dock or Tabs
        self._browser_context = None

        # Tool Bar
        self.tool_bar = QtWidgets.QGroupBox()
        self.tool_bar.setLayout(QtWidgets.QHBoxLayout())
        self.c_layout.addWidget(self.tool_bar)
        self.tool_bar.setMaximumHeight(TOOL_BAR_BUTTON_WIDTH)

        # Back Button
        self.back_btn = QtWidgets.QPushButton()
        self.back_btn.setMaximumWidth(TOOL_BAR_BUTTON_WIDTH)
        self.back_btn.setIcon(QtGui.QIcon(os.path.join(ICON_PATH, "chevron-left.svg")))
        self.tool_bar.layout().addWidget(self.back_btn)
        self.back_btn.clicked.connect(lambda: self.get_active_browser().back())

        # Forward Button
        self.forward_btn = QtWidgets.QPushButton()
        self.forward_btn.setMaximumWidth(TOOL_BAR_BUTTON_WIDTH)
        self.forward_btn.setIcon(QtGui.QIcon(os.path.join(ICON_PATH, "chevron-right.svg")))
        self.tool_bar.layout().addWidget(self.forward_btn)
        self.forward_btn.clicked.connect(lambda: self.get_active_browser().forward())

        # Directory up button
        self.up_btn = QtWidgets.QPushButton()
        self.up_btn.setMaximumWidth(TOOL_BAR_BUTTON_WIDTH)
        self.up_btn.setIcon(QtGui.QIcon(os.path.join(ICON_PATH, "chevron-up.svg")))
        self.tool_bar.layout().addWidget(self.up_btn)
        self.up_btn.clicked.connect(lambda : self.get_active_browser().up())

        # View Toggle
        self.view_toggle_btn = QtWidgets.QPushButton()
        self.view_toggle_btn.setMaximumWidth(TOOL_BAR_BUTTON_WIDTH)
        self.view_toggle_btn.setIcon(QtGui.QIcon(os.path.join(ICON_PATH, "columns.svg")))
        self.tool_bar.layout().addWidget(self.view_toggle_btn)
        self.view_toggle_btn.clicked.connect(self.toggle_browser_context)

        # Add Tab
        self.add_tab_btn = QtWidgets.QPushButton()
        self.add_tab_btn.setMaximumWidth(TOOL_BAR_BUTTON_WIDTH)
        self.add_tab_btn.setIcon(QtGui.QIcon(os.path.join(ICON_PATH, "plus-circle.svg")))
        self.tool_bar.layout().addWidget(self.add_tab_btn)
        self.add_tab_btn.clicked.connect(self.add_browser)


        # Search Bar
        self.search_ln_edit = QtWidgets.QLineEdit()
        self.tool_bar.layout().addWidget(self.search_ln_edit)
        self.search_ln_edit.textChanged.connect(self.run_search)
        self.search_ln_edit.setFixedWidth(300)

        # Search Cancel Button
        self.search_cancel_btn = QtWidgets.QPushButton()
        self.search_cancel_btn.setIcon(QtGui.QIcon(os.path.join(ICON_PATH, "x-circle.svg")))
        self.tool_bar.layout().addWidget(self.search_cancel_btn)
        self.search_cancel_btn.hide()
        self.cancel_search.connect(self.search_cancel_btn.hide)
        self.start_search.connect(self.search_cancel_btn.show)


        # Search Status Label
        self.search_status_lbl = QtWidgets.QLabel()
        self.search_status_lbl.setMinimumWidth(30)
        self.tool_bar.layout().addWidget(self.search_status_lbl)
        self.search_status_lbl.hide()
        self.tool_bar.layout().addStretch()

        # Search Options
        self._search_options = SearchOptionsWidget(self)

        # Search Results Tab
        self.search_results_window = BrowserWidget(self)

        # Hamburger btn
        self.hamburger_btn = QtWidgets.QPushButton()
        self.hamburger_btn.setMaximumWidth(TOOL_BAR_BUTTON_WIDTH)
        self.hamburger_btn.setIcon(QtGui.QIcon(os.path.join(ICON_PATH, "menu.svg")))
        self.tool_bar.layout().addWidget(self.hamburger_btn)
        self.options_menu = QtWidgets.QMenu()
        self.hamburger_btn.setMenu(self.options_menu)
        search = self.options_menu.addAction("Search Options")
        search.triggered.connect(self._search_options.show)

        open_settings = self.options_menu.addAction("Open Settings Folder")
        open_settings.triggered.connect(lambda: os.startfile(SETTINGS_DIR))

        self.lower_grp = QtWidgets.QGroupBox()
        self.c_layout.addWidget(self.lower_grp)
        self.lower_grp.setLayout(QtWidgets.QHBoxLayout())
        self.lower_grp.layout().setContentsMargins(0,0,0,0)
        self.lower_grp.layout().setMargin(2)
        self.lower_grp.layout().setSpacing(0)

        # Pin Group
        self.fav_grp = QtWidgets.QGroupBox()
        self.fav_grp.setLayout(QtWidgets.QVBoxLayout())
        self.fav_grp.layout().setContentsMargins(0, 0, 0, 0)
        self.pin_tool_bar = QtWidgets.QGroupBox()
        self.pin_tool_bar.setLayout(QtWidgets.QHBoxLayout())
        self.fav_grp.layout().addWidget(self.pin_tool_bar)

        # Pin Combo
        self.fav_combo = QtWidgets.QComboBox()
        self.fav_combo.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.fav_combo.customContextMenuRequested.connect(self.show_pin_combo_context_menu)
        self._pin_combo_context_menu = QtWidgets.QMenu()
        self.add_fav_combo_menu_actions()
        self.pin_tool_bar.layout().addWidget(self.fav_combo)
        self.pin_tool_bar.layout().setContentsMargins(0,0,0,0)
        func = lambda: self.set_active_pin_tray(self.fav_combo.itemData(self.fav_combo.currentIndex()))
        self.fav_combo.currentIndexChanged.connect(func)


        # Pin List
        self.fav_grp.setMaximumWidth(200)
        self.fav_grp.setMinimumWidth(200)

        self.lower_grp.layout().addWidget(self.fav_grp)
        self.lower_grp.layout().addWidget(self.tab_widget)
        self.lower_grp.layout().addWidget(self.dock_widget)

        # Signals

        # init
        self._initialized = True

        # Data
        self._filter = None

        # Threading
        test_dirs = ['C:/Users/neilb/Pictures/Hikes', 'C:/Users/neilb/Pictures/ref']
        self._thread = utils.Thread(search_directory_list=test_dirs)
        self._thread.start()


    def search_progess(self, progress):
        print("Progress {}".format(progress))


    def search_started(self):
        while self._active_threads:
            pass


    def show_hamburger_menu(self, pos):
        self._context_menu.exec_(self.mapToGlobal(pos))
        pass

    def progress_function(self, n):
        self.search_status_lbl.setText(n)
        # print("Running thread")

    def print_output(self, s):
        print(s)

    def search_complete(self):
        log.info("Search Completed")

    def run_search(self):
        """

        :return:
        """
        if not self.search_ln_edit.text():
            return

        if not self._thread:
            # TEST DIRECTORIES TO FEED IT
            test_dirs = ['C:/Users/neilb/Pictures/Hikes', 'C:/Users/neilb/Pictures/ref']

            self._thread = utils.Thread(search_directory_list=test_dirs)
            self.cancel_search.connect(self._thread.exit)
            self.update_search.connect(self._thread.set_search_items)
            self._thread.start()

            # self._thread.finished.connect(self._thread.deleteLater)

        items = self.get_file_items()
        self._thread.set_search_items(items)
        self._thread.set_search_string(self.search_ln_edit.text())





    def kill_active_threads(self):
        self._can_search = False
        while self.active_threads > 0:
            print("Waiting for threads to exit")
            time.sleep(0.1)

    def show_pin_combo_context_menu(self, pos):
        self._pin_combo_context_menu.exec_(self.fav_combo.mapToGlobal(pos))

    def add_fav_combo_menu_actions(self):
        add_tray = self._pin_combo_context_menu.addAction("Add Pin List")
        add_tray.triggered.connect(self.new_fav_list_dialog)

        rename_tray = self._pin_combo_context_menu.addAction("Rename Pin List")
        rename_tray.triggered.connect(self.rename_fav_list_dialog)

        delete_tray = self._pin_combo_context_menu.addAction("Delete Pin List")
        delete_tray.triggered.connect(self.remove_fav_list_dialog)

    def remove_fav_list_dialog(self):
        dialog = QtWidgets.QMessageBox(self)
        dialog.setWindowTitle("Delete pin list")

        tray_name = self.fav_combo.currentText()
        dialog.setText("Are you sure you want to delete list {}. \n"
                            "This is not undoable.".format(tray_name))
        func = lambda : self.remove_fav_list()
        dialog.accepted.connect(func)
        dialog.show()

    def new_fav_list_dialog(self):
        dialog = QtWidgets.QInputDialog(self)
        dialog.setWindowTitle("New pin list")
        dialog.setLabelText("List name")
        func = lambda: self.add_fav_list(widget_data={NAME: dialog.textValue()})
        dialog.accepted.connect(func)
        dialog.move(self.fav_combo.mapToGlobal(self.fav_combo.pos()))
        dialog.show()

    def rename_fav_list_dialog(self):
        dialog = QtWidgets.QInputDialog(self)
        dialog.setWindowTitle("Rename pin list")
        dialog.setLabelText("New name")
        dialog.setTextValue(self.fav_combo.currentText())

        func = lambda: self.set_fav_list_name(self.fav_combo.currentIndex(), dialog.textValue())
        dialog.accepted.connect(func)

        dialog.move(self.fav_combo.mapToGlobal(self.fav_combo.pos()))
        dialog.show()

    def set_fav_context(self, pin_list):
        """
        Set active pin list
        :return:
        """
        self._pin_context.hide()
        self._pin_context = pin_list
        self._pin_context.show()

    def set_fav_list_name(self, idx, name):
        self.fav_combo.setItemText(idx, name)
        fav_widget = self.fav_combo.itemData(idx)
        fav_widget.setObjectName(name)


    def save_fav_lists(self):
        save_data = {}
        browser_data = {}
        for num, b in enumerate(self._browser_widgets_list):
            browser_data["browser_" + str(num)] = serialize(b)
            print(browser_data)

        pin_list_data = []

        for num in range(self.fav_combo.count()):
            fav_list = self.fav_combo.itemData(num)
            assert isinstance(fav_list, FavWidget)

            pin_list_items = []
            for i in fav_list.get_items():

                pin_list_items.append(serialize(i))

            pin_list_data.append({FAV_WIDGET_NAME: self.fav_combo.itemText(num),
                                  FAV_WIDGET_PINS: pin_list_items})

        if not os.path.exists(os.path.dirname(self._data_path)):
            os.makedirs(os.path.dirname(self._data_path))

        save_data[PIN_LISTS] = pin_list_data
        save_data[BROWSERS] = browser_data
        log.debug("Saving Pin List data {}".format(self._data_path))
        log.debug(save_data)

        with open(self._data_path, 'w') as f:
            json.dump(save_data, f, indent=4, sort_keys=True)

    def set_browser_context(self, context=DOCK_WIDGET_VIEW_MODE):
        log.debug("Setting view context {}".format(context))
        log.debug("Browser Widget list {}".format(len(self._browser_widgets_list)))
        refresh = False

        if context == DOCK_WIDGET_VIEW_MODE and self._browser_context is not self.dock_widget:
            if self._browser_context:
                self._browser_context.clear_widgets()
                self._browser_context.hide()
            self._browser_context = self.dock_widget
            refresh = True
        elif context == TAB_VIEW_MODE and self._browser_context is not self.tab_widget:
            if self._browser_context:
                self._browser_context.clear_widgets()
                self._browser_context.hide()
            self._browser_context = self.tab_widget
            refresh = True

        if refresh:
            self._browser_context.show()

            for b in self._browser_widgets_list:
                b.is_closed.connect(self.remove_browser)
                self._browser_context.add_widget(b)

        else:
            log.info("Browser context has not changed. Skipping refresh.")

    def toggle_browser_context(self):
        if self._browser_context is self.tab_widget:
            self.set_browser_context(DOCK_WIDGET_VIEW_MODE)
        elif self._browser_context is self.dock_widget:
            self.set_browser_context(TAB_VIEW_MODE)

    def load_saved_data(self):

        if os.path.exists(self._data_path):
            with open(self._data_path, 'r') as f:
                self._save_data = json.load(f)

        if not self._save_data:
            return

        # Load browsers
        # for k, v in self._save_data[BROWSERS].items():
        #     self.add_browser(v)

        for i in self._save_data[PIN_LISTS]:
            print("loading fav list {}".format(i))
            self.add_fav_list(items=i[FAV_WIDGET_PINS], name=i[FAV_WIDGET_NAME])

        # Make sure we have at least one pin list
        if not self.fav_combo.count():
            self.add_fav_list()



        # for k in self._save_data.keys():
        #     self._pin_widgets_list.append(PinListWidget(self._save_data[k]))

    def remove_fav_list(self):
        idx = self.fav_combo.currentIndex()
        widget = self.fav_combo.itemData(idx)
        self.fav_combo.removeItem(idx)
        widget.deleteLater()

    def add_fav_list(self, items=None, widget_data=None, name=""):
        """
        :param items: list
        :param widget_data: Serialized class data
        :param name: str
        :return:
        """

        # fav_widget = createView(QtWidgets.QListWidget, FavWidget, self, items, name)
        fav_widget = FavWidget(items, name)
        fav_widget.path_changed.connect(self.set_active_browser_path)
        fav_widget.new_tab.connect(self.add_browser_from_item)

        if not name:
            if widget_data and NAME in widget_data.keys():
                name = widget_data[NAME]
            else:
                name = "Pin List {}".format(self.fav_combo.count())

        self.fav_combo.addItem(name, fav_widget)
        self.fav_grp.layout().addWidget(fav_widget)
        self.fav_combo.setCurrentIndex(self.fav_combo.count() - 1)

    def add_fav_pin(self, item):
        fav_widget = self.fav_combo.currentData()
        assert isinstance(fav_widget, FavWidget)
        fav_widget.add_item(item)


    def set_active_pin_tray(self, tray):
        for idx in range(self.fav_combo.count()):
            i = self.fav_combo.itemData(idx)
            if i == tray:
                i.show()
            else:
                i.hide()


    def set_active_browser_title(self, title):
        self._browser_context.set_title(title)

    def add_browser_from_item(self, item: FileItem):
        self.add_browser()
        self.set_active_browser_path(item)


    def add_browser(self, browser_data=None, set_path=True, browser_window=None):

        if not browser_window:
            browser_window = BrowserWidget(self, browser_data=browser_data)

        browser_window.is_active.connect(self.set_active_browser)  # Signal
        browser_window.list_view.path_changed.connect(self.set_active_browser_path)
        browser_window.table_view.path_changed.connect(self.set_active_browser_path)

        browser_window.table_view.new_tab.connect(self.add_browser_from_item)
        browser_window.table_view.new_pin.connect(self.add_fav_pin)

        # PATH EDIT
        browser_window.path_line_edit.new_tab.connect(self.add_browser_from_item)
        browser_window.path_line_edit.new_pin.connect(self.add_fav_pin)

        self._browser_widgets_list.append(browser_window)
        self._browser_context.add_widget(browser_window)
        self.set_active_browser(browser_window)

        if set_path:
            if browser_data:
                self.get_active_browser().set_path(browser_data[FULL_PATH])
            else:
                self.get_active_browser().set_path(TEST_PATH)

            self.set_active_browser_title(self.get_active_browser()._leaf)

        return browser_window

    def get_browser(self, browser):
        """
        Test Code for checking if Signal object works.
        :param browser:
        :return:
        """
        log.debug("Signal Browser instance found {}".format(browser))

    def remove_browser(self, browser_widget):
        log.debug("{} Removing widget {}".format(self.__class__.__name__, browser_widget))
        if browser_widget in self._browser_widgets_list:
            self._browser_widgets_list.remove(browser_widget)
            self._browser_context.remove_widget(browser_widget)

        if self._active == browser_widget:
            if self._browser_widgets_list:
                self.set_active_browser(self._browser_widgets_list[0])
            else:
                self.set_active_browser(None)

    def get_browser_list(self):
        # Call on the MainWindow Singleton to ensure that it has been instantiated.
        return self._browser_widgets_list

    def get_active_browser(self):
        return self._active

    def set_active_browser(self, browser):
        if browser is None:
            print(traceback.print_stack())
            raise TypeError("")

        log.debug("Main Window setting active browser {}".format(browser.windowTitle()))

        for w in self._browser_widgets_list:
            assert isinstance(w, BrowserWidget)
            w.list_view.setStyleSheet(INACTIVE_STYLE)
            w.table_view.setStyleSheet(INACTIVE_STYLE)
        self._active = browser
        if browser:
            browser.list_view.setStyleSheet(ACTIVE_STYLE)
            browser.table_view.setStyleSheet(ACTIVE_STYLE)

    def set_active_browser_path(self, file_item: FileItem):
        log.debug("Setting Active Browser Path {}".format(file_item._full_path))
        browser = self.get_active_browser()
        line_edit = browser.path_line_edit

        assert isinstance(browser, BrowserWidget)
        browser.set_path(file_item)
        p = line_edit.palette()
        color = file_item.color()
        if isinstance(color, list):
            new_color = QtGui.QColor()
            new_color.setRgbF(*color)
            color = new_color


        p.setColor(line_edit.backgroundRole(), color)
        line_edit.setPalette(p)


    def get_file_items(self):
        all_items = []
        for b in self._browser_widgets_list:
            assert isinstance(b, BrowserWidget)
            if b.windowTitle() == SEARCH_TAB_TITLE:
                continue
            for i in b._view_context.get_items():
                all_items.append(i)
        # fav widgets
        for i in range(self.fav_combo.count()):
            widget = self.fav_combo.itemData(i)
            assert isinstance(widget, FavWidget)
            all_items.extend(widget.get_items())

        return all_items

    def closeEvent(self, *args):

        try:
            self._thread.exit()
        except Exception as ex:
            log.error(ex)

        if CAN_SAVE_SETTINGS:
            self._settings.setValue('size', self.size())
            self._settings.setValue('pos', self.pos())
            self.save_fav_lists()
        else:
            log.warning("Cannot save fav list!")

    def showEvent(self, *args):
        self.resize(self._settings.value('size', QtCore.QSize(500, 500)))

        self.load_saved_data()

def serialize_rercursive(obj, serialized):
    if not isinstance(obj, dict):
        obj = obj.__dict__

    for k, v in obj.items():
        if isinstance(v, dict):
            serialized[k] = {}
            serialized[k] = serialize_rercursive(v, serialized[k])
        else:
            item = serialize(v)
            if item:
                serialized[k] = serialize(item)


def serialize(obj):
    if hasattr(obj, 'toJSON'):
        return obj.toJSON()

    if not isinstance(obj, dict):
        return None

    serializable_types = [int, list, dict, float, str]

    obj_data = {}
    for k, v in obj.items():
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
    window.set_browser_context(DOCK_WIDGET_VIEW_MODE)
    window.show()

    window.set_browser_context(context=DOCK_WIDGET_VIEW_MODE)
    window.add_browser({FULL_PATH: TEST_PATH})
    if not window.fav_combo.count():
        window.add_fav_list({}, name="Fav Stuffs")


    STYLE_SHEET_PATH = "./stylesheets/light_theme.css"
    # set_theme(app, STYLE_SHEET_PATH)


    sys.exit(app.exec_())
