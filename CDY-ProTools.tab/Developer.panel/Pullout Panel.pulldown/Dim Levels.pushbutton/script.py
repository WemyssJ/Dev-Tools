# -*- coding: utf-8 -*-
"""
Dim Levels — places a vertical dimension string across all selected levels.
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
levels  = [doc.GetElement(i) for i in sel_ids
           if isinstance(doc.GetElement(i), DB.Level)]

if len(levels) < 2:
    forms.alert("Select 2 or more Levels first.", title="Dim Levels")
    raise SystemExit

# Sort levels by elevation
levels.sort(key=lambda l: l.Elevation)

ref_array = DB.ReferenceArray()
for lvl in levels:
    ref_array.Append(DB.Reference(lvl))

# Vertical dimension line — offset to the left of the first level curve
crv_first = levels[0].GetCurvesInView(DB.DatumExtentType.ViewSpecific, view)
x_offset  = -10.0   # ~3 m to the left in internal units

if crv_first:
    x_pos = crv_first[0].GetEndPoint(0).X + x_offset
else:
    x_pos = -10.0

y_bottom = levels[0].Elevation
y_top    = levels[-1].Elevation
line_start = DB.XYZ(x_pos, y_bottom, 0)
line_end   = DB.XYZ(x_pos, y_top,    0)
dim_line   = DB.Line.CreateBound(line_start, line_end)

dim_types = DB.FilteredElementCollector(doc).OfClass(DB.DimensionType).ToElements()
dim_type  = next(
    (dt for dt in dim_types
     if dt.StyleType == DB.DimensionStyleType.Linear),
    None)

from Autodesk.Revit.DB import Transaction

with Transaction(doc, "CDY: Dim Levels") as t:
    t.Start()
    try:
        if dim_type:
            doc.Create.NewDimension(view, dim_line, ref_array, dim_type)
        else:
            doc.Create.NewDimension(view, dim_line, ref_array)
        t.Commit()
    except Exception as ex:
        t.RollBack()
        forms.alert("Dimension failed: {}".format(ex), title="Dim Levels")
