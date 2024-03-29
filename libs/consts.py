"""
@Author Neil Berard
Internal constants.
"""
from PySide2.QtCore import Qt
import os
import sys
import logging
log = logging.getLogger("Conts")

APPLICATION_NAME = "File-Browser"
if getattr(sys, 'frozen', False):
    APPLICATION_PATH = os.path.dirname(os.path.dirname(sys.executable))
else:
    APPLICATION_PATH = os.path.dirname(os.path.dirname(__file__))

log.info("APPLICATION_PATH {}".format(APPLICATION_PATH))
SETTINGS_DIR = os.path.join(os.environ['APPDATA'], APPLICATION_NAME, 'settings')
DATA_DIR = os.path.join(os.environ['APPDATA'], APPLICATION_NAME, 'data')


ICON_PATH = APPLICATION_PATH + "/icons"


VERSION = 1.0

# A way to hold onto to the File Data weather we are using ListWidget or TableWidget items.
# FileItem

FILE_ITEM_DATA_ROLE = Qt.UserRole + 2
# FILE_ITEM_DATA_ROLE = 1

# DROP ACTIONS
# Specify what we want to do when dragging or dropping items
USE_FILE_ITEM_ACTION = 'USE_FILE_ITEM'


TOOL_BAR_BUTTON_WIDTH = 40
TEST_PATH = '{}'.format(os.environ['USERPROFILE'])

# Context Modes
# Main Window
DOCK_WIDGET_VIEW_MODE = "Dock Widgets"
TAB_VIEW_MODE = "Tabs"

# Browser Widget
TABLE_VIEW_MODE = "table_view_mode"
LIST_VIEW_MODE = "list_view_mode"


# display keys (FileItem attributes), what columns to show
FILE_NAME = "file_name"
FILE_PATH = "file_path"

FULL_PATH = "_full_path"

FILE_COLOR = "_color"


CAN_SAVE_SETTINGS = True