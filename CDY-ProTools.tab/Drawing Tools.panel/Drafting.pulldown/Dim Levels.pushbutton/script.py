# -*- coding: utf-8 -*-
"""Create Dimension Lines between Levels."""

__title__ = 'Dimension\nLevels'

from pyrevit import HOST_APP, revit, DB, forms
from Autodesk.Revit.UI.Selection import ISelectionFilter
from Autodesk.Revit import Exceptions

import os, sys

# -- Telemetry (optional) ---------------------------------------------------
lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'lib'))
if lib_path not in sys.path:
    sys.path.append(lib_path)
try:
    import telemetry_auto
    telemetry_auto.log_tool_usage(os.path.basename(os.path.dirname(__file__)).replace(".pushbutton", ""))
except:
    pass

# -- Setup ------------------------------------------------------------------
try:
    uiapp = __revit__  # noqa
except NameError:
    uiapp = HOST_APP.uiapp

uidoc = uiapp.ActiveUIDocument
doc   = uidoc.Document
view  = doc.ActiveView

# -- Guard: levels only make sense in section/elevation ---------------------
valid_view_types = (DB.ViewType.Section, DB.ViewType.Elevation, DB.ViewType.Detail)
if view.ViewType not in valid_view_types:
    forms.alert("Switch to a Section or Elevation view first.")
    raise SystemExit

# -- Set and ASSIGN sketch plane to view so all interactive picks work ------
with revit.Transaction("Set Sketch Plane", doc=doc):
    plane = DB.Plane.CreateByNormalAndOrigin(view.ViewDirection, view.Origin)
    sp    = DB.SketchPlane.Create(doc, plane)
    view.SketchPlane = sp

# -- Selection filter -------------------------------------------------------
class LevelFilter(ISelectionFilter):
    def AllowElement(self, e):
        return e.Category and e.Category.Id.IntegerValue == int(DB.BuiltInCategory.OST_Levels)
    def AllowReference(self, r, p):
        return True

# -- Get levels (pre-selected or pick) --------------------------------------
def get_levels():
    pre = [doc.GetElement(i) for i in uidoc.Selection.GetElementIds()
           if isinstance(doc.GetElement(i), DB.Level)]
    if pre:
        return pre
    with forms.WarningBar(title="Select levels"):
        try:
            return list(uidoc.Selection.PickElementsByRectangle(LevelFilter(), "Select Levels"))
        except Exceptions.OperationCanceledException:
            return []

# -- Main -------------------------------------------------------------------
levels = [l for l in get_levels() if isinstance(l, DB.Level)]

if len(levels) < 2:
    forms.alert("Select at least 2 levels.")
    raise SystemExit

# Sort levels by elevation
levels = sorted(levels, key=lambda l: l.Elevation)

# Levels are horizontal — dimension line runs vertically (along view up direction)
up_dir = view.UpDirection.Normalize()

# Pick placement point
with forms.WarningBar(title="Pick dimension placement point"):
    try:
        pick_pt = uidoc.Selection.PickPoint()
    except Exceptions.OperationCanceledException:
        raise SystemExit

# Build dimension line: vertical, passing through pick point's X, spanning level elevations
elevations   = [l.Elevation for l in levels]
origin_param = pick_pt.DotProduct(up_dir)
start        = pick_pt + up_dir * (min(elevations) - origin_param)
end          = pick_pt + up_dir * (max(elevations) - origin_param)
dim_line     = DB.Line.CreateBound(start, end)

# Build reference array
refs = DB.ReferenceArray()
for l in levels:
    refs.Append(DB.Reference(l))

# Get the user's default linear dimension type
def default_dim_type():
    type_id = doc.GetDefaultElementTypeId(DB.ElementTypeGroup.LinearDimensionType)
    if type_id and type_id != DB.ElementId.InvalidElementId:
        return doc.GetElement(type_id)
    return None

# Create dimension
with revit.Transaction("Dimension Levels", doc=doc):
    dim_type = default_dim_type()
    if dim_type:
        doc.Create.NewDimension(view, dim_line, refs, dim_type)
    else:
        doc.Create.NewDimension(view, dim_line, refs)
