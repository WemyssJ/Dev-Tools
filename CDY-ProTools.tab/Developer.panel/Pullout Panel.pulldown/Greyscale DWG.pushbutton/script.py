# -*- coding: utf-8 -*-
"""
Greyscale DWG — overrides all DWG layers to black + halftone in the active view
or its applied view template.
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
if not sel_ids:
    forms.alert("Select a linked DWG first.", title="Greyscale DWG")
    raise SystemExit

import_inst = None
for eid in sel_ids:
    elem = doc.GetElement(eid)
    if isinstance(elem, DB.ImportInstance):
        import_inst = elem
        break

if not import_inst:
    forms.alert("No linked DWG found in selection.", title="Greyscale DWG")
    raise SystemExit

root_cat = import_inst.Category
if not root_cat:
    forms.alert("Cannot read DWG category.", title="Greyscale DWG")
    raise SystemExit

tid    = view.ViewTemplateId
target = doc.GetElement(tid) \
         if tid != DB.ElementId.InvalidElementId else view

black = DB.Color(0, 0, 0)
ogs   = DB.OverrideGraphicSettings()
ogs.SetProjectionLineColor(black)
ogs.SetProjectionLinePatternId(DB.ElementId.InvalidElementId)
ogs.SetHalftone(True)

from Autodesk.Revit.DB import Transaction

with Transaction(doc, "CDY: Greyscale DWG") as t:
    t.Start()
    try:
        # Override the root DWG category
        target.SetCategoryOverrides(root_cat.Id, ogs)
        # Override every sub-category (layer)
        for sub in root_cat.SubCategories:
            try:
                target.SetCategoryOverrides(sub.Id, ogs)
            except Exception:
                pass
        t.Commit()
    except Exception as ex:
        t.RollBack()
        forms.alert("Failed:\n{}".format(ex), title="Greyscale DWG")
