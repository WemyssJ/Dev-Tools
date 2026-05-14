# -*- coding: utf-8 -*-
"""Create Dimension Lines between Grids."""

__title__ = 'Dimension\nGrids'

from pyrevit import revit, DB, forms
from Autodesk.Revit.UI.Selection import ISelectionFilter
from Autodesk.Revit import Exceptions
import os, sys

# -----------------------------------------------------------------------------------
# TELEMETRY (unchanged)
# -----------------------------------------------------------------------------------
lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'lib'))
if lib_path not in sys.path:
    sys.path.append(lib_path)

try:
    import telemetry_auto
    tool_name = os.path.basename(os.path.dirname(__file__))
    TOOL_NAME = tool_name.replace(".pushbutton", "")
    telemetry_auto.log_tool_usage(TOOL_NAME)
except:
    pass

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
# GET PRESELECTED GRIDS OR ASK USER
# -----------------------------------------------------------------------------------
preselected_ids = uidoc.Selection.GetElementIds()
preselected_grids = [doc.GetElement(i) for i in preselected_ids if i.IntegerValue != DB.ElementId.InvalidElementId]

# Filter to grids only
preselected_grids = [g for g in preselected_grids if g.Category and g.Category.Id.IntegerValue == int(DB.BuiltInCategory.OST_Grids)]

if preselected_grids:
    grids = preselected_grids
else:
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
def get_grid_curve_in_view(grid, view):
    crvs = grid.GetCurvesInView(DB.DatumExtentType.ViewSpecific, view)
    if crvs and len(crvs) > 0:
        return crvs[0]
    return grid.Curve

def get_grid_direction(grid):
    crv = get_grid_curve_in_view(grid, active_view)
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
# PICK DIMENSION PLACEMENT POINT
# -----------------------------------------------------------------------------------
with forms.WarningBar(title="Pick dimension placement point"):
    try:
        pick_point = uidoc.Selection.PickPoint()
    except Exceptions.OperationCanceledException:
        forms.alert("Cancelled", exitscript=True)

# -----------------------------------------------------------------------------------
# GET CURVES + MIDPOINTS
# -----------------------------------------------------------------------------------
curves = [get_grid_curve_in_view(g, active_view) for g in straight_grids]
midpoints = [c.Evaluate(0.5, True) for c in curves]

# -----------------------------------------------------------------------------------
# GRID DIRECTION AND DIMENSION DIRECTION
# -----------------------------------------------------------------------------------
grid_dir = (curves[0].GetEndPoint(1) - curves[0].GetEndPoint(0)).Normalize()
view_normal = active_view.ViewDirection.Normalize()

# perpendicular direction (dimension direction)
perp_dir = grid_dir.CrossProduct(view_normal).Normalize()

# optional: force consistent side in plan
if is_plan and perp_dir.DotProduct(active_view.UpDirection) < 0:
    perp_dir = perp_dir.Negate()

# -----------------------------------------------------------------------------------
# SORT GRIDS BY PERPENDICULAR AXIS
# -----------------------------------------------------------------------------------
sorted_data = sorted(zip(straight_grids, midpoints), key=lambda x: x[1].DotProduct(perp_dir))
straight_grids = [x[0] for x in sorted_data]
midpoints      = [x[1] for x in sorted_data]

# -----------------------------------------------------------------------------------
# REBUILD REFERENCES
# -----------------------------------------------------------------------------------
ref_array = DB.ReferenceArray()
for g in straight_grids:
    ref_array.Append(DB.Reference(g))

# -----------------------------------------------------------------------------------
# BUILD DIM LINE THROUGH PICK POINT
# -----------------------------------------------------------------------------------
params = [p.DotProduct(perp_dir) for p in midpoints]
min_p = min(params)
max_p = max(params)
origin_param = pick_point.DotProduct(perp_dir)

start = pick_point + perp_dir * (min_p - origin_param)
end   = pick_point + perp_dir * (max_p - origin_param)

dim_line = DB.Line.CreateBound(start, end)

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
# CREATE DIMENSION
# -----------------------------------------------------------------------------------
with revit.Transaction("Dimension Grids"):
    doc.Create.NewDimension(active_view, dim_line, ref_array)
