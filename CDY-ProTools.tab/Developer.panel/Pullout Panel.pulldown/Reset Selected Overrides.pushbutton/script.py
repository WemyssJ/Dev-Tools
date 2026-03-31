# -*- coding: utf-8 -*-
"""
Reset Selected Overrides
Removes all graphic overrides from selected elements in the active view.
"""
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import *

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


doc   = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
view  = doc.ActiveView

selection_ids = uidoc.Selection.GetElementIds()

if not selection_ids:
    TaskDialog.Show("Reset Selected Overrides", "Please select elements first.")
    script.exit()

t = Transaction(doc, "CDY: Reset Selected Graphic Overrides")
t.Start()
for eid in selection_ids:
    view.SetElementOverrides(eid, OverrideGraphicSettings())
t.Commit()
