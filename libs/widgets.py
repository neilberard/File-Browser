import abc
from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import Signal

ICON_PROVIDER = QtWidgets.QFileIconProvider()

class AbstractDockWindow:
    def __init__(self, main_window):
        self.MainWindow = main_window

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

    def __init__(self, main_window):
        AbstractDockWindow.__init__(self, main_window)
        QtWidgets.QTabWidget.__init__(self)
        # super().__init__(main_window)

        self.dir_path = ""

        self.setAcceptDrops(True)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_tab)
        self.currentChanged.connect(self.set_active)

    def set_title(self, title):
        idx = self.indexOf(self.MainWindow().get_active_browser())
        self.setTabText(idx, title)

    def add_widget(self, browser_window, path=None, set_current=True):
        self.addTab(browser_window, browser_window.windowTitle())
        if set_current:
            self.setCurrentWidget(browser_window)
            self.MainWindow().set_active_browser(browser_window)

    def populate(self):
        self.blockSignals(True)
        for w in self.MainWindow().get_browser_list():
            self.add_widget(w, set_current=False)
        self.setCurrentWidget(self.MainWindow().get_active_browser())
        self.blockSignals(False)

    def remove_widget(self, widget):
        self.removeTab(self.indexOf(widget))

    def close_tab(self, *args):
        self.MainWindow().remove_browser(self.widget(args[0]))

    def clear_widgets(self):
        self.blockSignals(True)
        self.clear()
        self.blockSignals(False)

    def set_active(self):
        self.MainWindow().set_active_browser(self.currentWidget())


class DockWindow(AbstractDockWindow, QtWidgets.QWidget):
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
        dock = self.MainWindow().get_active_browser()
        if dock:
            dock.parent().setWindowTitle(title)

    def add_widget(self, browser_window, path=None, set_current=True):
        dock_widget = DockWidget(browser_window)
        dock_widget.closed_event.connect(self.MainWindow().remove_browser)
        self.splitter.addWidget(dock_widget)

    def remove_widget(self, dock_widget):
        self.MainWindow().remove_browser(dock_widget)

    def populate(self):
        for w in self.MainWindow().get_browser_list():
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


# FAV LIST
class FileItem:
    file_info = QtCore.QFileInfo()
    full_path = None

    def __init__(self, item_data: dict):
        self.__dict__.update(item_data)

        self.file_info = QtCore.QFileInfo(self.full_path)
        self.file_name = self.file_info.fileName()

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




