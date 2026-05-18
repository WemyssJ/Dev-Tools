# -*- coding: utf-8 -*-
"""Create Dimension Lines between Levels."""

__title__ = 'Dimension\nLevels'

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
# UI / App bootstrap fix (CRITICAL - same as grids)
# ---------------------------------------------------------------------------
uiapp = getattr(HOST_APP, "uiapp", None) or __revit__

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
# Safe WarningBar wrapper (same as grids)
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
# View guard
# ---------------------------------------------------------------------------
valid_view_types = (DB.ViewType.Section, DB.ViewType.Elevation, DB.ViewType.Detail)
if view.ViewType not in valid_view_types:
    forms.alert("Switch to a Section or Elevation view first.")
    raise SystemExit


# ---------------------------------------------------------------------------
# Sketch plane (safe, consistent with grids tool)
# ---------------------------------------------------------------------------
with revit.Transaction("Set Sketch Plane", doc=doc):
    try:
        plane = DB.Plane.CreateByNormalAndOrigin(view.ViewDirection, view.Origin)
        sp    = DB.SketchPlane.Create(doc, plane)
        view.SketchPlane = sp
    except:
        pass


# ---------------------------------------------------------------------------
# Selection filter
# ---------------------------------------------------------------------------
class LevelFilter(ISelectionFilter):
    def AllowElement(self, e):
        return e.Category and e.Category.Id.IntegerValue == int(DB.BuiltInCategory.OST_Levels)

    def AllowReference(self, r, p):
        return True


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------
def get_levels():
    pre = [
        doc.GetElement(i)
        for i in uidoc.Selection.GetElementIds()
        if isinstance(doc.GetElement(i), DB.Level)
    ]

    if pre:
        return pre

    with safe_warning_bar("Select levels, then press Finish"):
        try:
            return list(uidoc.Selection.PickElementsByRectangle(LevelFilter()))
        except Exceptions.OperationCanceledException:
            return []


levels = [l for l in get_levels() if isinstance(l, DB.Level)]

if len(levels) < 2:
    forms.alert("Select at least 2 levels.")
    raise SystemExit


# ---------------------------------------------------------------------------
# Sort by elevation
# ---------------------------------------------------------------------------
levels = sorted(levels, key=lambda l: l.Elevation)


# ---------------------------------------------------------------------------
# Dimension direction
# ---------------------------------------------------------------------------
up_dir = view.UpDirection.Normalize()


# ---------------------------------------------------------------------------
# Pick placement point
# ---------------------------------------------------------------------------
with safe_warning_bar("Pick dimension placement point"):
    try:
        pick_pt = uidoc.Selection.PickPoint()
    except Exceptions.OperationCanceledException:
        raise SystemExit


# ---------------------------------------------------------------------------
# Build dimension line (same structure as grids tool)
# ---------------------------------------------------------------------------
elevations   = [l.Elevation for l in levels]
origin_param = pick_pt.DotProduct(up_dir)

start = pick_pt + up_dir * (min(elevations) - origin_param)
end   = pick_pt + up_dir * (max(elevations) - origin_param)

dim_line = DB.Line.CreateBound(start, end)


# ---------------------------------------------------------------------------
# Reference array
# ---------------------------------------------------------------------------
refs = DB.ReferenceArray()
for l in levels:
    refs.Append(DB.Reference(l))


# ---------------------------------------------------------------------------
# Dimension type helper (same as grids)
# ---------------------------------------------------------------------------
def default_dim_type():
    type_id = doc.GetDefaultElementTypeId(DB.ElementTypeGroup.LinearDimensionType)
    if type_id and type_id != DB.ElementId.InvalidElementId:
        return doc.GetElement(type_id)
    return None


# ---------------------------------------------------------------------------
# Create dimension
# ---------------------------------------------------------------------------
with revit.Transaction("Dimension Levels", doc=doc):
    dim_type = default_dim_type()

    if dim_type:
        doc.Create.NewDimension(view, dim_line, refs, dim_type)
    else:
        doc.Create.NewDimension(view, dim_line, refs)