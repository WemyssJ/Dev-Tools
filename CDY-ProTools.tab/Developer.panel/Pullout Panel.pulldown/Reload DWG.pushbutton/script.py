# -*- coding: utf-8 -*-
"""
Reload Selected DWG — reloads the selected linked DWG from its current path.
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

doc = uidoc.Document

sel_ids = uidoc.Selection.GetElementIds()
if not sel_ids:
    forms.alert("Select a linked DWG first.", title="Reload DWG")
    raise SystemExit

import_inst = None
for eid in sel_ids:
    elem = doc.GetElement(eid)
    if isinstance(elem, DB.ImportInstance):
        import_inst = elem
        break

if not import_inst:
    forms.alert("No linked DWG found in selection.", title="Reload DWG")
    raise SystemExit

link_type = doc.GetElement(import_inst.GetTypeId())
if not link_type:
    forms.alert("Cannot find the CAD link type.", title="Reload DWG")
    raise SystemExit

from Autodesk.Revit.DB import Transaction

with Transaction(doc, "CDY: Reload DWG") as t:
    t.Start()
    try:
        result = link_type.Reload()
        t.Commit()
        if result.LoadStatus == DB.LinkLoadResultType.Loaded:
            forms.toast("DWG reloaded successfully.")
        else:
            forms.alert("Reload status: {}".format(result.LoadStatus),
                        title="Reload DWG")
    except Exception as ex:
        t.RollBack()
        forms.alert("Reload failed:\n{}".format(ex), title="Reload DWG")
