# -*- coding: utf-8 -*-
"""Create Dimension Lines between Grids."""

__title__ = 'Dimension\nGrids'

from pyrevit import HOST_APP, revit, DB, forms
from Autodesk.Revit.UI.Selection import ISelectionFilter
from Autodesk.Revit import Exceptions

import os, sys

# ---------------------------------------------------------------------------
# Telemetry (optional)
# ---------------------------------------------------------------------------
lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'lib'))
if lib_path not in sys.path:
    sys.path.append(lib_path)

try:
    import telemetry_auto
    telemetry_auto.log_tool_usage(
        os.path.basename(os.path.dirname(__file__)).replace(".pushbutton", "")
    )
except:
    pass

# ---------------------------------------------------------------------------
# UI / App bootstrap fix (CRITICAL)
# ---------------------------------------------------------------------------
uiapp = getattr(HOST_APP, "uiapp", None) or __revit__

# Force-safe hydration for pyRevit UI layer (prevents MainWindowHandle = None issues)
try:
    if hasattr(uiapp, "MainWindowHandle") and not uiapp.MainWindowHandle:
        import pyrevit
        pyrevit.framework.get_current_uiapp()
except:
    pass

uidoc = uiapp.ActiveUIDocument
doc   = uidoc.Document
view  = doc.ActiveView


# ---------------------------------------------------------------------------
# Safe WarningBar wrapper (prevents crash when UI handle not ready)
# ---------------------------------------------------------------------------
def safe_warning_bar(title):
    try:
        return forms.WarningBar(title=title)
    except Exception:
        class _DummyCtx(object):
            def __enter__(self): pass
            def __exit__(self, exc_type, exc_val, exc_tb): pass
        return _DummyCtx()


# ---------------------------------------------------------------------------
# Set sketch plane (required for interactive operations)
# ---------------------------------------------------------------------------
with revit.Transaction("Set Sketch Plane", doc=doc):
    plane = DB.Plane.CreateByNormalAndOrigin(view.ViewDirection, view.Origin)
    sp    = DB.SketchPlane.Create(doc, plane)
    view.SketchPlane = sp


# ---------------------------------------------------------------------------
# Selection filter
# ---------------------------------------------------------------------------
class GridFilter(ISelectionFilter):
    def AllowElement(self, e):
        return e.Category and e.Category.Id.IntegerValue == int(DB.BuiltInCategory.OST_Grids)

    def AllowReference(self, r, p):
        return True


# ---------------------------------------------------------------------------
# Grid selection
# ---------------------------------------------------------------------------
def get_grids():
    pre = [
        doc.GetElement(i)
        for i in uidoc.Selection.GetElementIds()
        if isinstance(doc.GetElement(i), DB.Grid)
    ]

    if pre:
        return pre

    with safe_warning_bar("Select parallel grid lines, then press Finish"):
        try:
            return list(uidoc.Selection.PickElementsByRectangle(GridFilter()))
        except Exceptions.OperationCanceledException:
            return []


grids = [g for g in get_grids() if isinstance(g, DB.Grid) and not g.IsCurved]

if len(grids) < 2:
    forms.alert("Select at least 2 straight parallel grids.")
    raise SystemExit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def curve_in_view(g):
    c = g.GetCurvesInView(DB.DatumExtentType.ViewSpecific, view)
    return c[0] if c else g.Curve


def direction(g):
    c = curve_in_view(g)
    return (c.GetEndPoint(1) - c.GetEndPoint(0)).Normalize()


# ---------------------------------------------------------------------------
# Validate parallelism
# ---------------------------------------------------------------------------
base_dir = direction(grids[0])

if any(
    not (direction(g).IsAlmostEqualTo(base_dir) or direction(g).IsAlmostEqualTo(base_dir.Negate()))
    for g in grids[1:]
):
    forms.alert("Grids must be parallel.")
    raise SystemExit


# ---------------------------------------------------------------------------
# Sort grids along perpendicular axis
# ---------------------------------------------------------------------------
view_normal = view.ViewDirection.Normalize()
perp_dir = direction(grids[0]).CrossProduct(view_normal).Normalize()

grids = sorted(
    grids,
    key=lambda g: curve_in_view(g).Evaluate(0.5, True).DotProduct(perp_dir)
)


# ---------------------------------------------------------------------------
# Pick dimension placement point
# ---------------------------------------------------------------------------
with safe_warning_bar("Pick dimension placement point"):
    try:
        pick_pt = uidoc.Selection.PickPoint()
    except Exceptions.OperationCanceledException:
        raise SystemExit


# ---------------------------------------------------------------------------
# Build dimension line
# ---------------------------------------------------------------------------
midpoints = [curve_in_view(g).Evaluate(0.5, True) for g in grids]
params    = [p.DotProduct(perp_dir) for p in midpoints]

origin_param = pick_pt.DotProduct(perp_dir)

start = pick_pt + perp_dir * (min(params) - origin_param)
end   = pick_pt + perp_dir * (max(params) - origin_param)

dim_line = DB.Line.CreateBound(start, end)


# ---------------------------------------------------------------------------
# Reference array
# ---------------------------------------------------------------------------
refs = DB.ReferenceArray()
for g in grids:
    refs.Append(DB.Reference(g))


# ---------------------------------------------------------------------------
# Dimension type helper
# ---------------------------------------------------------------------------
def default_dim_type():
    type_id = doc.GetDefaultElementTypeId(DB.ElementTypeGroup.LinearDimensionType)
    if type_id and type_id != DB.ElementId.InvalidElementId:
        return doc.GetElement(type_id)
    return None


# ---------------------------------------------------------------------------
# Create dimension
# ---------------------------------------------------------------------------
with revit.Transaction("Dimension Grids", doc=doc):
    dim_type = default_dim_type()

    if dim_type:
        doc.Create.NewDimension(view, dim_line, refs, dim_type)
    else:
        doc.Create.NewDimension(view, dim_line, refs)