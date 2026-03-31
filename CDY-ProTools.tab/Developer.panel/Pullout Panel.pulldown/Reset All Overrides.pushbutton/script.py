# -*- coding: utf-8 -*-
"""
Reset All Overrides
Removes all graphic overrides from every element in the active view.
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

# Collect all elements visible in the active view (excluding element types)
element_ids = (
    FilteredElementCollector(doc, view.Id)
    .WhereElementIsNotElementType()
    .ToElementIds()
)

if not element_ids:
    TaskDialog.Show("Reset All Overrides", "No elements found in the active view.")
    script.exit()

t = Transaction(doc, "CDY: Reset All Graphic Overrides")
t.Start()
blank = OverrideGraphicSettings()
for eid in element_ids:
    view.SetElementOverrides(eid, blank)
t.Commit()
