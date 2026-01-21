"""Activates selection tool that picks only Detail 2D elements."""
#pylint: disable=import-error,invalid-name,unused-argument,broad-except,missing-docstring
from pyrevit import revit, DB, UI

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


selection = revit.get_selection()


class MassSelectionFilter(UI.Selection.ISelectionFilter):
    # standard API override function
    def AllowElement(self, element):
        # only allow view-specific (detail) elements
        # that are not part of a group
        if element.ViewSpecific:
            if element.GroupId == element.GroupId.InvalidElementId:
                return True
        return False

    # standard API override function
    def AllowReference(self, refer, point):
        return False

try:
    msfilter = MassSelectionFilter()
    selection_list = revit.pick_rectangle(pick_filter=msfilter)

    filtered_list = []
    for el in selection_list:
        filtered_list.append(el.Id)

    selection.set_to(filtered_list)
    revit.uidoc.RefreshActiveView()
except Exception:
    pass
