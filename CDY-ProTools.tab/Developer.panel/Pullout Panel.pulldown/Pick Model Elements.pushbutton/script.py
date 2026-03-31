# -*- coding: utf-8 -*-
# pylint: skip-file
"""Activates selection tool that picks only Model (3D) elements."""

from pyrevit import forms
import Autodesk.Revit.DB as DB
from Autodesk.Revit.UI.Selection import ISelectionFilter
from System.Collections.Generic import List as DotNetList

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


uidoc = __uidoc__
if not uidoc:
    raise SystemExit


class ModelSelectionFilter(ISelectionFilter):
    def AllowElement(self, element):
        # Only non-view-specific (model/3D) elements
        if not element.ViewSpecific:
            return True
        return False

    def AllowReference(self, refer, point):
        return False


try:
    picked = uidoc.Selection.PickElementsByRectangle(
        ModelSelectionFilter(), "Box-select 3D / model elements")
    if picked:
        uidoc.Selection.SetElementIds(
            DotNetList[DB.ElementId]([e.Id for e in picked]))
    else:
        forms.toast("No 3D elements found in selection box.")
except Exception:
    pass
