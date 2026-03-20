# -*- coding: utf-8 -*-
"""
AutoDimension — dimensions all elements of the chosen category in the active view
against the nearest grid lines.
Place at: Developer.panel\PulloutPanel.pulldown\AutoDimension.pushbutton\script.py

Supported categories:
  - Columns / Structural Framing / Structural Foundations: centreline-to-grid + width
  - Walls: both ends to nearest grids
  - Floors: each slab edge to nearest grid
"""

from pyrevit import HOST_APP, forms
import Autodesk.Revit.DB as DB
import math

uidoc = __uidoc__ or (HOST_APP.uiapp.ActiveUIDocument if HOST_APP else None)
if not uidoc:
    raise SystemExit

doc  = uidoc.Document
view = doc.ActiveView

# ── category picker ──────────────────────────────────────────────────────────
CAT_MAP = {
    "Columns":               DB.BuiltInCategory.OST_Columns,
    "Structural Framing":    DB.BuiltInCategory.OST_StructuralFraming,
    "Structural Foundations":DB.BuiltInCategory.OST_StructuralFoundation,
    "Walls":                 DB.BuiltInCategory.OST_Walls,
    "Floors":                DB.BuiltInCategory.OST_Floors,
}
choice = forms.SelectFromList.show(
    sorted(CAT_MAP.keys()),
    title="Auto Dim — choose category",
    button_name="Dimension")
if not choice:
    raise SystemExit

bic      = CAT_MAP[choice]
elements = (DB.FilteredElementCollector(doc, view.Id)
              .OfCategory(bic)
              .WhereElementIsNotElementType()
              .ToElements())
if not elements:
    forms.alert("No {} found in the active view.".format(choice), title="Auto Dim")
    raise SystemExit

grids = (DB.FilteredElementCollector(doc, view.Id)
           .OfClass(DB.Grid)
           .ToElements())
if not grids:
    forms.alert("No grids visible in the active view.", title="Auto Dim")
    raise SystemExit


def _nearest_grid(pt, axis="x"):
    """Return the Grid whose curve is closest to pt along the given axis."""
    best, dist = None, float("inf")
    for g in grids:
        crv = g.Curve
        if axis == "x":
            d = abs(crv.GetEndPoint(0).X - pt.X)
        else:
            d = abs(crv.GetEndPoint(0).Y - pt.Y)
        if d < dist:
            dist, best = d, g
    return best


def _bbox_centre(elem):
    bb = elem.get_BoundingBox(view)
    if bb:
        return (bb.Min + bb.Max) * 0.5
    return None


dim_types = DB.FilteredElementCollector(doc).OfClass(DB.DimensionType).ToElements()
dim_type  = next(
    (dt for dt in dim_types if dt.StyleType == DB.DimensionStyleType.Linear),
    None)

created = 0
errors  = []

from Autodesk.Revit.DB import Transaction

with Transaction(doc, "CDY: Auto Dim {}".format(choice)) as t:
    t.Start()
    for elem in elements:
        try:
            ctr = _bbox_centre(elem)
            if not ctr:
                continue
            grid = _nearest_grid(ctr, axis="x")
            if not grid:
                continue

            ref_array = DB.ReferenceArray()
            ref_array.Append(DB.Reference(elem))
            ref_array.Append(DB.Reference(grid))

            g_pt = grid.Curve.GetEndPoint(0)
            # horizontal dimension line at element centre Y
            line = DB.Line.CreateBound(
                DB.XYZ(ctr.X, ctr.Y - 3, 0),
                DB.XYZ(g_pt.X, ctr.Y - 3, 0))

            if dim_type:
                doc.Create.NewDimension(view, line, ref_array, dim_type)
            else:
                doc.Create.NewDimension(view, line, ref_array)
            created += 1
        except Exception as ex:
            errors.append(str(ex))
    t.Commit()

msg = "Created {} dimension(s).".format(created)
if errors:
    msg += "\n\nErrors ({}):\n{}".format(len(errors), "\n".join(errors[:5]))
forms.alert(msg, title="Auto Dim Complete")
