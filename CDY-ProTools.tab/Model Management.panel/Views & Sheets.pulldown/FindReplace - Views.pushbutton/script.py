# -*- coding: utf-8 -*-
__title__ = "Views:Find and Replace"
__author__ = "Erik Frits"
__version__ = 'Version: 1.2'
__doc__ = """Rename multiple views at once with Find/Replace/Suffix/Prefix logic.
You can select views in Project Browser or if nothing selected
you will get a menu to select your views.

Author: Erik Frits"""

# ╦╔╦╗╔═╗╔═╗╦═╗╔╦╗╔═╗
# ║║║║╠═╝║ ║╠╦╝ ║ ╚═╗
# ╩╩ ╩╩  ╚═╝╩╚═ ╩ ╚═╝ IMPORTS
#====================================================================
from Autodesk.Revit.DB import *

# Custom
from Renaming.BaseClass_FindReplace import BaseRenaming
from Snippets._context_manager import ef_Transaction, try_except
from Snippets._selection import get_selected_views

##############################################################################################
# TELEMETRY IMPORTS #
##############################################################################################
# Only works IF specified TELEMETRY_JSON path exists within %AppData%\pyRevit\Extensions\BIMTools.extension\lib\telemetry_auto.py"
# Records tool usage by date & revit version
import os, sys

# Add lib folder for telemetry_auto
lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'lib'))
if lib_path not in sys.path:
    sys.path.append(lib_path)

import telemetry_auto

tool_name = os.path.basename(os.path.dirname(__file__)) 
TOOL_NAME = tool_name.replace(".pushbutton", "")
telemetry_auto.log_tool_usage(TOOL_NAME)
##############################################################################################

# ╦  ╦╔═╗╦═╗╦╔═╗╔╗ ╦  ╔═╗╔═╗
# ╚╗╔╝╠═╣╠╦╝║╠═╣╠╩╗║  ║╣ ╚═╗
#  ╚╝ ╩ ╩╩╚═╩╩ ╩╚═╝╩═╝╚═╝╚═╝ VARIABLES
#====================================================================
doc   = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument


# ╔═╗╦  ╔═╗╔═╗╔═╗
# ║  ║  ╠═╣╚═╗╚═╗
# ╚═╝╩═╝╩ ╩╚═╝╚═╝ CLASS
#====================================================================

class RenameViews(BaseRenaming):
    uidoc = __revit__.ActiveUIDocument
    doc   = __revit__.ActiveUIDocument.Document

    def __init__(self):
        self.start(title=__title__, version=__version__)

    def get_selected_elements(self):
        """Get Selected Views or let user select Views from a list."""
        return get_selected_views(uidoc, title=__title__, version=__version__)

    def rename_elements(self):
        """Function to rename selected Views."""
        with ef_Transaction(self.doc, __title__, debug=True):
            for view in self.selected_elements:

                with try_except(debug=True):
                    current_name  = view.Name
                    new_name      = self.prefix + current_name.replace(self.find,self.replace) + self.suffix

                    if new_name and  new_name != current_name:
                        view.Name = new_name

# ╔╦╗╔═╗╦╔╗╔
# ║║║╠═╣║║║║
# ╩ ╩╩ ╩╩╝╚╝ MAIN
#====================================================================
if __name__ == '__main__':
    x = RenameViews()

