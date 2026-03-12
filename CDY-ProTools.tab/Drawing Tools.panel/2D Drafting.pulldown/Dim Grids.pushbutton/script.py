# -*- coding: utf-8 -*-
"""Create Dimension Lines between Grids."""

__title__ = 'Dimension\nGrids'

from pyrevit import revit, DB, forms
from Autodesk.Revit.UI.Selection import ISelectionFilter
from Autodesk.Revit import Exceptions
import os, sys

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

# -----------------------------------------------------------------------------------
# SETUP
# -----------------------------------------------------------------------------------
doc = revit.doc
uidoc = revit.uidoc
active_view = doc.ActiveView

# -----------------------------------------------------------------------------------
# SELECTION FILTER
# -----------------------------------------------------------------------------------
class GridSelectionFilter(ISelectionFilter):
    def AllowElement(self, element):
        return element.Category and element.Category.Id.IntegerValue == int(DB.BuiltInCategory.OST_Grids)

    def AllowReference(self, ref, point):
        return True

# -----------------------------------------------------------------------------------
# CHECK VIEW TYPE
# -----------------------------------------------------------------------------------
is_plan = active_view.ViewType == DB.ViewType.FloorPlan

# -----------------------------------------------------------------------------------
# PICK GRIDS
# -----------------------------------------------------------------------------------
with forms.WarningBar(title="Select parallel straight grid lines"):
    try:
        grids = uidoc.Selection.PickElementsByRectangle(
            GridSelectionFilter(),
            "Select Grids"
        )
    except Exceptions.OperationCanceledException:
        forms.alert("Cancelled", exitscript=True)

if not grids:
    forms.alert("No grids selected.", exitscript=True)

# -----------------------------------------------------------------------------------
# FILTER STRAIGHT GRIDS ONLY
# -----------------------------------------------------------------------------------
straight_grids = [g for g in grids if not g.IsCurved]

if len(straight_grids) < 2:
    forms.alert("Select at least two straight parallel grids.", exitscript=True)

# -----------------------------------------------------------------------------------
# VALIDATE PARALLEL
# -----------------------------------------------------------------------------------
def get_grid_direction(grid):
    crv = grid.Curve
    return (crv.GetEndPoint(1) - crv.GetEndPoint(0)).Normalize()

base_direction = get_grid_direction(straight_grids[0])

for g in straight_grids[1:]:
    this_dir = get_grid_direction(g)

    if not (
        this_dir.IsAlmostEqualTo(base_direction) or
        this_dir.IsAlmostEqualTo(base_direction.Negate())
    ):
        forms.alert("Selected grids are not parallel.", exitscript=True)

# -----------------------------------------------------------------------------------
# BUILD REFERENCE ARRAY
# -----------------------------------------------------------------------------------
ref_array = DB.ReferenceArray()

for grid in straight_grids:
    ref = DB.Reference.ParseFromStableRepresentation(doc, grid.UniqueId)
    ref_array.Append(ref)

# -----------------------------------------------------------------------------------
# DETERMINE DIMENSION DIRECTION
# -----------------------------------------------------------------------------------
if is_plan:
    # Perpendicular in XY plane
    dim_direction = DB.XYZ(-base_direction.Y, base_direction.X, 0).Normalize()
else:
    # Use view right direction in elevation/section
    dim_direction = active_view.RightDirection.Normalize()

# -----------------------------------------------------------------------------------
# SET SKETCH PLANE FOR SECTION/ELEVATION
# -----------------------------------------------------------------------------------
if not is_plan:
    with revit.Transaction("Set Sketch Plane"):
        plane = DB.Plane.CreateByNormalAndOrigin(
            active_view.ViewDirection,
            active_view.Origin
        )
        sp = DB.SketchPlane.Create(doc, plane)
        active_view.SketchPlane = sp
        doc.Regenerate()

# -----------------------------------------------------------------------------------
# PICK DIMENSION PLACEMENT POINT
# -----------------------------------------------------------------------------------
with forms.WarningBar(title="Pick dimension placement point"):
    try:
        pick_point = uidoc.Selection.PickPoint()
    except Exceptions.OperationCanceledException:
        forms.alert("Cancelled", exitscript=True)

# -----------------------------------------------------------------------------------
# CREATE DIMENSION LINE
# -----------------------------------------------------------------------------------
line_length = 100.0
dim_line = DB.Line.CreateBound(
    pick_point,
    pick_point + dim_direction * line_length
)

# -----------------------------------------------------------------------------------
# CREATE DIMENSION
# -----------------------------------------------------------------------------------
with revit.Transaction("Dimension Grids"):
    doc.Create.NewDimension(active_view, dim_line, ref_array)
