# -*- coding: utf-8 -*-
"""
Dim Grids — places a linear dimension string across all selected grid lines.
Place at: Developer.panel\PulloutPanel.pulldown\Dim Grids.pushbutton\script.py
"""

from pyrevit import HOST_APP, forms
import Autodesk.Revit.DB as DB
from System.Collections.Generic import List as DotNetList

uidoc = __uidoc__ or (HOST_APP.uiapp.ActiveUIDocument if HOST_APP else None)
if not uidoc:
    raise SystemExit

doc  = uidoc.Document
view = doc.ActiveView

sel_ids = uidoc.Selection.GetElementIds()
grids   = [doc.GetElement(i) for i in sel_ids
           if isinstance(doc.GetElement(i), DB.Grid)]

if len(grids) < 2:
    forms.alert("Select 2 or more Grids first.", title="Dim Gridlines")
    raise SystemExit

# Build a reference array from grid curves in the active view
ref_array = DB.ReferenceArray()
curves    = []
for grid in grids:
    crv = grid.GetCurvesInView(DB.DatumExtentType.ViewSpecific, view)
    if not crv:
        crv = [grid.Curve]
    for c in crv:
        ref_array.Append(DB.Reference(grid))
        curves.append(c)
        break   # one curve per grid is enough

if ref_array.Size < 2:
    forms.alert("Could not build references for the selected grids.", title="Dim Gridlines")
    raise SystemExit

# Dimension line runs perpendicular to grids — offset below first grid midpoint
first_curve = curves[0]
last_curve  = curves[-1]
mid1        = first_curve.Evaluate(0.5, True)
mid2        = last_curve.Evaluate(0.5, True)

# Offset the dimension line downward (Y) so it sits below the grids
offset      = DB.XYZ(0, -10, 0)   # ~3 m below in internal units
line_start  = mid1 + offset
line_end    = mid2 + offset
dim_line    = DB.Line.CreateBound(line_start, line_end)

# Find a suitable linear dimension type
dim_types = DB.FilteredElementCollector(doc).OfClass(DB.DimensionType).ToElements()
dim_type  = next(
    (dt for dt in dim_types
     if dt.StyleType == DB.DimensionStyleType.Linear),
    None)

from Autodesk.Revit.DB import Transaction

with Transaction(doc, "CDY: Dim Gridlines") as t:
    t.Start()
    try:
        if dim_type:
            doc.Create.NewDimension(view, dim_line, ref_array, dim_type)
        else:
            doc.Create.NewDimension(view, dim_line, ref_array)
        t.Commit()
    except Exception as ex:
        t.RollBack()
        forms.alert("Dimension failed: {}".format(ex), title="Dim Gridlines")
