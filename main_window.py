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

from libs import utils
from libs.widgets import TabWindow, DockWindow, BrowserWidget, FavWidget, FileItem
from libs.consts import *

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)




if getattr(sys, 'frozen', False):
    APPLICATION_PATH = os.path.dirname(sys.executable)

else:
    APPLICATION_PATH = os.path.dirname(__file__)

log.info("APPLICATION_PATH {}".format(APPLICATION_PATH))
SETTINGS_PATH = os.path.join(os.environ['APPDATA'], APPLICATION_NAME, 'data', 'save_data.json')
log.info("SETTINGS PATH {}".format(SETTINGS_PATH))


ICON_PATH = APPLICATION_PATH + "/icons"


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

    # Slots
    apply_filter = QtCore.Signal(str, dict)

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
        self.back_btn.clicked.connect(lambda : self.get_active_browser().back())

        # Forward Button
        self.forward_btn = QtWidgets.QPushButton()
        self.forward_btn.setMaximumWidth(TOOL_BAR_BUTTON_WIDTH)
        self.forward_btn.setIcon(QtGui.QIcon(os.path.join(ICON_PATH, "chevron-right.svg")))
        self.tool_bar.layout().addWidget(self.forward_btn)
        self.forward_btn.clicked.connect(lambda : self.get_active_browser().forward())

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
        self.search_ln_edit.textChanged.connect(self.run_search_thread)
        self.search_ln_edit.setFixedWidth(300)

        # Search Cancel Button
        self.search_cancel_btn = QtWidgets.QPushButton()
        self.search_cancel_btn.setIcon(QtGui.QIcon(os.path.join(ICON_PATH, "x-circle.svg")))
        self.tool_bar.layout().addWidget(self.search_cancel_btn)
        self.search_cancel_btn.hide()


        # Search Status Label
        self.search_status_lbl = QtWidgets.QLabel()
        self.search_status_lbl.setMinimumWidth(30)
        self.tool_bar.layout().addWidget(self.search_status_lbl)
        self.search_status_lbl.hide()
        self.tool_bar.layout().addStretch()


        # Search Results Tab
        # self.search_results_window = BrowserWidget(self)
        # self._browser_widgets_list.append(self.search_results_window)
        # # self._browser_context.add_widget(self.search_results_window)
        # self.set_active_browser(self.search_results_window)
        # self.search_results_window.setWindowTitle("Search Results")
        # self.search_results_window.hide()


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
        self.search_cancel_btn.clicked.connect(self.stop_searching)

        # init
        self._initialized = True

        # Data
        self._filter = None

        # Threading
        self.threadpool = QtCore.QThreadPool()
        log.debug("Max threads {}".format(self.threadpool.maxThreadCount()))
        self._can_search = True
        self._is_searching = False
        self.active_threads = 0
        # self.run_search_thread()


    def set_search_filter(self):
        # print(self.search_ln_edit.text())
        self.apply_filter.emit(self.search_ln_edit.text(), {})

    def search_function(self, progress_callback):

        log.info("Running search function! {}".format(self._can_search))
        self.active_threads += 1
        self.get_active_browser().list_view.clear()

        search_token = self.search_ln_edit.text().lower()
        if not search_token:
            log.info("No token")
            self.active_threads -= 1
            return
        items = self.get_all_file_items()

        found_items = []

        def check_candidate(main_window, file_name, file_path):
            candidate = file_name.lower()
            if search_token in candidate:

                if not file_path.endswith(file_name):
                    full_path = "{}/{}".format(file_path, file_name)
                else:
                    full_path = file_path
                full_path = full_path.replace("\\", "/")

                if full_path in found_items:
                    return
                if len(found_items) > MAX_RESULTS:
                    log.info("Hit max {} results".format(MAX_RESULTS))
                    self._can_search = False
                    return

                found_items.append(full_path)
                try:
                    item = FileItemWidget({'full_path': full_path})
                    main_window.get_active_browser().list_view.add_item(item)
                    found_items.append(full_path)
                except Exception as ex:
                    log.error(ex)

        for i in items:
            assert isinstance(i, FileItem)
            if not self._can_search:
                self.active_threads -= 1
                return "Search Canceled!"

            if i.file_path() in found_items:
                continue

            check_candidate(self, i._file_name, i.file_path())


            # Search through dirs
            if i.is_dir():
                # progress_callback.emit(i.file_name)
                log.debug("{} Scanning Directory!".format(i._file_name))
                for root, dirs, files in os.walk(i.file_path()):
                    if not self._can_search:
                        self.active_threads -= 1
                        return "Search Canceled!"

                    # Check DIR
                    for name in files:
                        check_candidate(self, name, root)
                    for name in dirs:
                        check_candidate(self, name, root)

        self.active_threads -= 1
        return


        if not self._can_search:
            log.warning("Self cannot search!")
        self.active_threads += 1
        idx = 0

        while self._can_search:
            idx += 1
            if idx > 3:
                idx = 0
            if not self._can_search:
                self.active_threads -= 1
                return "Search Canceled! Womp Womp!"
            time.sleep(0.4)

            progress_callback.emit(idx)
        self.active_threads -= 1
        return

    def stop_searching(self):
        self._can_search = False
        self.search_cancel_btn.hide()
        self.search_status_lbl.hide()
        self.search_ln_edit.clear()

    def progress_function(self, n):
        self.search_status_lbl.setText(n)
        # print("Running thread")

    def print_output(self, s):
        print(s)

    def search_complete(self):
        self.search_cancel_btn.hide()
        self.search_status_lbl.hide()
        log.info("Search Completed")

    def run_search_thread(self):
        """

        :return:
        """
        # if not self.search_ln_edit.text():
        #     search_browser = self.get_active_browser().list_view
        #     if search_browser.windowTitle() == SEARCH_TAB_TITLE:
        #         search_browser.clear()
        #     return

        print("Search token {}".format(self.search_ln_edit.text()))
        global CAN_SAVE_SETTINGS
        CAN_SAVE_SETTINGS = False


        self.get_all_file_items()

        self.set_browser_context(TAB_VIEW_MODE)
        if self.get_active_browser() and self.get_active_browser().windowTitle() == SEARCH_TAB_TITLE:
            pass
        else:
            self.add_browser(set_path=False)
            self.set_active_browser_title(SEARCH_TAB_TITLE)

        # Kill any current worker and wait for threads to exit.
        self._can_search = False
        while self.active_threads > 0:
            print("Waiting for threads to exit")
            time.sleep(0.1)
        log.info("Threads Done, starting search.")

        self.threadpool.clear()
        self._can_search = True
        self.search_cancel_btn.show()
        self.search_status_lbl.show()
        worker = utils.Worker(self.search_function)
        worker.signals.result.connect(self.print_output)
        worker.signals.finished.connect(self.search_complete)
        worker.signals.progress.connect(self.progress_function)
        self.threadpool.start(worker)

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
        func = lambda : self.add_fav_list(widget_data={NAME: dialog.textValue()})
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

        pin_list_data = []

        for num in range(self.fav_combo.count()):
            fav_list = self.fav_combo.itemData(num)
            assert isinstance(fav_list, FavWidget)

            pin_list_items = []
            for i in fav_list.get_items():
                pin_list_items.append(serialize(i))

            pin_list_data.append({FAV_WIDGET_NAME: self.fav_combo.itemText(num),
                                  FAV_WIDGET_PINS: pin_list_items})

        if not os.path.exists(os.path.dirname(SETTINGS_PATH)):
            os.makedirs(os.path.dirname(SETTINGS_PATH))

        save_data[PIN_LISTS] = pin_list_data
        save_data[BROWSERS] = browser_data
        log.debug("Saving Pin List data {}".format(SETTINGS_PATH))
        log.debug(save_data)

        with open(SETTINGS_PATH, 'w') as f:
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

        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, 'r') as f:
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

        if not name:
            if widget_data and NAME in widget_data.keys():
                name = widget_data[NAME]
            else:
                name = "Pin List {}".format(self.fav_combo.count())

        self.fav_combo.addItem(name, fav_widget)
        self.fav_grp.layout().addWidget(fav_widget)
        self.fav_combo.setCurrentIndex(self.fav_combo.count() - 1)

    def set_active_pin_tray(self, tray):
        for idx in range(self.fav_combo.count()):
            i = self.fav_combo.itemData(idx)
            if i == tray:
                i.show()
            else:
                i.hide()


    def set_active_browser_title(self, title):
        self._browser_context.set_title(title)

    def add_browser(self, browser_data=None, set_path=True):
        browser_window = BrowserWidget(self, browser_data=browser_data)
        browser_window.is_active.connect(self.set_active_browser)  # Signal
        browser_window.list_view.path_changed.connect(self.set_active_browser_path)
        browser_window.table_view.path_changed.connect(self.set_active_browser_path)

        self._browser_widgets_list.append(browser_window)
        self._browser_context.add_widget(browser_window)
        self.set_active_browser(browser_window)

        if set_path:
            if browser_data:
                self.get_active_browser().set_path(browser_data[FULL_PATH], is_dir=True)
            else:
                self.get_active_browser().set_path(TEST_PATH, is_dir=True)

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
        log.debug("Setting Active Browser Path {}".format(file_item.full_path))
        browser = self.get_active_browser()
        line_edit = browser.path_line_edit

        assert isinstance(browser, BrowserWidget)
        browser.set_path(file_item.full_path, is_dir=True)
        p = line_edit.palette()
        color = file_item.color()
        if isinstance(color, list):
            new_color = QtGui.QColor()
            new_color.setRgbF(*color)
            color = new_color


        p.setColor(line_edit.backgroundRole(), color)
        line_edit.setPalette(p)
        # browser.setStyleSheet('background-color: red;')

        pass

    def set_drag_message(self, message):
        self._drag_message = message

    def get_drag_message(self):
        return self._drag_message

    def get_all_file_items(self):
        all_items = []
        for b in self._browser_widgets_list:
            assert isinstance(b, BrowserWidget)
            if b.windowTitle() == SEARCH_TAB_TITLE:
                continue
            for i in b._view_context.get_items():
                all_items.append(i)
        # fav widgets
        all_items.extend(self.get_fav_items())

        return all_items

    def closeEvent(self, *args):
        try:
            self.kill_active_threads()
        except Exception as ex:
            log.error(ex)

        if CAN_SAVE_SETTINGS:
            self.save_fav_lists()
        else:
            log.warning("Cannot save fav list!")

    def showEvent(self, *args):
        self.load_saved_data()


def serialize(obj):

    serializable_types = [int, list, dict, float, str]

    obj_data = {}
    for k, v in obj.__dict__.items():
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
