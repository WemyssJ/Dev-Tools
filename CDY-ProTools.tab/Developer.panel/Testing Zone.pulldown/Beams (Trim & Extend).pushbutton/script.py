# -*- coding: utf-8 -*-
__title__ = 'Trim/Extend Beams to Line/Grid'
__doc__ = 'Trim or extend multiple beams so their ends align with a selected line or grid (preserving Z).'

from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import *
from Autodesk.Revit.UI.Selection import ObjectType
from Autodesk.Revit.Exceptions import InvalidOperationException

uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document


def get_line_from_element(elem):
    """Extract a Line geometry from beams, model/detail lines, or grids."""
    if hasattr(elem, 'Location') and isinstance(elem.Location, LocationCurve):
        return elem.Location.Curve
    if isinstance(elem, (ModelCurve, DetailCurve)):
        return elem.GeometryCurve
    if isinstance(elem, Grid):
        return elem.Curve
    return None


def project_point_to_line_xy(point, line):
    """Project a point to a line ignoring Z (XY-plane only)."""
    p0 = line.GetEndPoint(0)
    p1 = line.GetEndPoint(1)

    # Flatten both line and point to Z=0 plane for projection
    p0f = XYZ(p0.X, p0.Y, 0)
    p1f = XYZ(p1.X, p1.Y, 0)
    pf = XYZ(point.X, point.Y, 0)

    v = (p1f - p0f).Normalize()
    t = (v.DotProduct(pf - p0f))
    projected_flat = p0f + t * v

    # Return same Z as original point to preserve elevation
    return XYZ(projected_flat.X, projected_flat.Y, point.Z)


try:
    # Step 1: Pick reference line, grid, or beam
    ref_elem_ref = uidoc.Selection.PickObject(ObjectType.Element, "Pick reference line, grid, or beam")
    ref_elem = doc.GetElement(ref_elem_ref)
    ref_line = get_line_from_element(ref_elem)
    if not ref_line:
        raise Exception("Selected element doesn't contain a valid reference line or curve.")

    # Step 2: Pick beams to modify
    beam_refs = uidoc.Selection.PickObjects(ObjectType.Element, "Select beams to trim/extend")

    t = Transaction(doc, "Trim/Extend Beams to Reference (Z preserved)")
    t.Start()

    for r in beam_refs:
        beam = doc.GetElement(r)
        loc = beam.Location
        if not isinstance(loc, LocationCurve):
            continue

        beam_line = loc.Curve
        start = beam_line.GetEndPoint(0)
        end = beam_line.GetEndPoint(1)

        # Project beam endpoints to reference line (in XY only)
        proj_start = project_point_to_line_xy(start, ref_line)
        proj_end = project_point_to_line_xy(end, ref_line)

        # Calculate 2D (XY) distances to decide which end is closer
        dist_start = ((start.X - proj_start.X) ** 2 + (start.Y - proj_start.Y) ** 2) ** 0.5
        dist_end = ((end.X - proj_end.X) ** 2 + (end.Y - proj_end.Y) ** 2) ** 0.5

        # Choose which end to move based on which is closer to reference
        if dist_start < dist_end:
            new_line = Line.CreateBound(proj_start, end)
        else:
            new_line = Line.CreateBound(start, proj_end)

        loc.Curve = new_line

    t.Commit()

    TaskDialog.Show("Trim/Extend Beams", "Beams have been trimmed or extended to the selected reference (Z preserved).")

except InvalidOperationException:
    # User cancelled selection
    pass
except Exception as e:
    TaskDialog.Show("Error", str(e))
