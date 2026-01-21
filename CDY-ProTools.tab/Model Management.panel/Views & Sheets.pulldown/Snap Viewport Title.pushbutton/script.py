# encoding: utf-8
# from https://discourse.pyrevitlabs.io/t/i-developed-a-tool-need-help-to-get-it-into-the-new-release-of-pyrevit/7639/3

from pyrevit import DB
from pyrevit.revit import pick_point, pick_element_by_category, Transaction
from pyrevit.forms import alert

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


def move_viewport_label(viewport, point):
    viewminpoint = viewport.GetBoxOutline().MinimumPoint
    new_label_location = point - viewminpoint
    viewport.LabelOffset = new_label_location


if __name__ == '__main__':
    selected_point = pick_point("Select a point")
    selected_viewport = pick_element_by_category(DB.BuiltInCategory.OST_Viewports, "Select a viewport")
    if selected_point is not None and selected_viewport is not None:
        with Transaction("Move Label to Point"):
            move_viewport_label(selected_viewport, selected_point)
    else:
        alert("Invalid selection. Please try again.")
