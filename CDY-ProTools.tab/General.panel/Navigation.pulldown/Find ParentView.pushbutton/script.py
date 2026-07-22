# -*- coding: utf-8 -*-
"""
Find Parent / Primary View — opens the primary view when the active view is a dependent.
Place at: Developer.panel\PulloutPanel.pulldown\Find ParentView.pushbutton\script.py
"""

from pyrevit import HOST_APP, forms
import Autodesk.Revit.DB as DB

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

uidoc = __uidoc__ or (HOST_APP.uiapp.ActiveUIDocument if HOST_APP else None)
if not uidoc:
    raise RuntimeError("No active document.")

doc  = uidoc.Document
view = doc.ActiveView

parent_id = view.GetPrimaryViewId()
if parent_id and parent_id != DB.ElementId.InvalidElementId:
    parent = doc.GetElement(parent_id)
    if parent:
        uidoc.ActiveView = parent
    else:
        forms.alert("Parent view element not found.", title="Find Parent View")
else:
    forms.alert("Active view has no parent — it is already a primary view.",
                title="Find Parent View")
