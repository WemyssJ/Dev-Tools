# -*- coding: utf-8 -*-
"""
DWG HotLoader — open the selected linked DWG in AutoCAD.
"""

import os
import subprocess
from pyrevit import HOST_APP, forms
import Autodesk.Revit.DB as DB

uidoc = __uidoc__ or (HOST_APP.uiapp.ActiveUIDocument if HOST_APP else None)
if not uidoc:
    raise SystemExit

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


doc = uidoc.Document

sel_ids = uidoc.Selection.GetElementIds()
if not sel_ids:
    forms.alert("Select a linked DWG first.", title="DWG HotLoader")
    raise SystemExit

import_inst = None
for eid in sel_ids:
    elem = doc.GetElement(eid)
    if isinstance(elem, DB.ImportInstance):
        import_inst = elem
        break

if not import_inst:
    forms.alert("No linked DWG found in selection.", title="DWG HotLoader")
    raise SystemExit

# Resolve external file path
link_type = doc.GetElement(import_inst.GetTypeId())
ext_path  = None
try:
    ext_path = link_type.GetExternalFileReference().GetAbsolutePath()
except Exception:
    pass

if not ext_path or not os.path.exists(ext_path):
    forms.alert("Cannot resolve the DWG path:\n{}".format(ext_path),
                title="DWG HotLoader")
    raise SystemExit

# Launch AutoCAD (or associated application)
try:
    os.startfile(ext_path)
except Exception as ex:
    forms.alert("Failed to open DWG:\n{}".format(ex), title="DWG HotLoader")
