# -*- coding: utf-8 -*-
"""
Grid Manager / Flip Grid Bubbles — flips bubble ends for all selected grids.
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
    raise SystemExit

doc  = uidoc.Document
view = doc.ActiveView

sel_ids = uidoc.Selection.GetElementIds()
grids   = [doc.GetElement(i) for i in sel_ids
           if isinstance(doc.GetElement(i), DB.Grid)]

if not grids:
    forms.alert("Select one or more Grids first.", title="Flip Grid Bubbles")
    raise SystemExit

from Autodesk.Revit.DB import Transaction

with Transaction(doc, "CDY: Flip Grid Bubbles") as t:
    t.Start()
    for grid in grids:
        # Toggle: if end 0 is hidden, show it; if shown, hide it
        end0_visible = grid.IsBubbleVisibleInView(DB.DatumEnds.End0, view)
        end1_visible = grid.IsBubbleVisibleInView(DB.DatumEnds.End1, view)
        if end0_visible:
            grid.HideBubbleInView(DB.DatumEnds.End0, view)
            grid.ShowBubbleInView(DB.DatumEnds.End1, view)
        else:
            grid.ShowBubbleInView(DB.DatumEnds.End0, view)
            grid.HideBubbleInView(DB.DatumEnds.End1, view)
    t.Commit()
