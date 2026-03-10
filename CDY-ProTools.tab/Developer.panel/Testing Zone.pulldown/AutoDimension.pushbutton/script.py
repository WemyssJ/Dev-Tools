# -*- coding: utf-8 -*-
__title__ = u"Auto Dims SC v5"
__doc__ = u"""Auto-dimensioning for walls, pylons, and structural columns.
v5 - box selection: grids + walls/columns. Dimensions everything within the selection.

Usage:
1. Click the button
2. Box-select grids and elements (walls, columns)
3. Press Enter

Scenarios:
1. Grid inside element -> snap E->G->E (row 1) + overall E->E (row 2)
2. Grid on edge -> snap G->E (acts as overall, row 1)
3. Grid outside element -> single chain G->E->E (row 1)
"""

import clr
import math

clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import (
    FilteredElementCollector, BuiltInCategory, BuiltInParameter,
    Dimension, DimensionType, Grid, Wall, FamilyInstance,
    XYZ, Line, Arc, Reference, ReferenceArray,
    ElementId, Transaction, TransactionGroup,
    Options, ViewPlan,
    PlanarFace, Solid, GeometryInstance,
    FailureProcessingResult, IFailuresPreprocessor,
    BuiltInFailures, DatumEnds,
)
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
from pyrevit import forms, script


# -----------------------------------------
#  FAILURE HANDLER (suppresses "not parallel")
# -----------------------------------------

class DimFailureSwallower(IFailuresPreprocessor):
    """Automatically deletes problematic dimensions instead of showing a dialog."""

    def __init__(self):
        self.had_errors = []

    def PreprocessFailures(self, failuresAccessor):
        failures = failuresAccessor.GetFailureMessages()
        for f in failures:
            try:
                sev = f.GetSeverity()
                desc = f.GetDescriptionText()
                # For errors - delete elements that caused the error
                if sev == sev.Error:
                    self.had_errors.append(desc)
                    ids = f.GetFailingElementIds()
                    if ids and ids.Count > 0:
                        failuresAccessor.DeleteElements(ids)
                    else:
                        failuresAccessor.ResolveFailure(f)
                # For warnings - just dismiss
                elif sev == sev.Warning:
                    failuresAccessor.DeleteWarning(f)
            except Exception:
                try:
                    failuresAccessor.ResolveFailure(f)
                except Exception:
                    pass
        return FailureProcessingResult.Continue


doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
view = doc.ActiveView
output = script.get_output()

# -----------------------------------------
#  SETTINGS
# -----------------------------------------

OFFSET_1_MM = 800  # first row (main dimensions/chains)
OFFSET_2_MM = 1400  # second row (additional overall, if needed)

OFFSET_CHAIN_1_MM = 1500  # pairwise grid chain
OFFSET_CHAIN_GAP_MM = 700  # gap between pairwise and overall grid chain

ZERO_TOL_MM = 5  # edge "on grid" tolerance
INTERSECT_TOL_MM = 50  # grid "intersects" element tolerance
MAX_SNAP_DIST_MM = 10000  # max distance to grid for snapping

DEBUG = True


def mm_to_ft(mm):
    return mm / 304.8


def ft_to_mm(ft):
    return ft * 304.8


# -----------------------------------------
#  DATA COLLECTION
# -----------------------------------------

def collect_grids_from_selection(selected_elements):
    """Collects grids from selected elements. Determines bubble side."""
    grids = []
    for g in selected_elements:
        if not isinstance(g, Grid):
            continue
        try:
            crv = g.Curve
            if not isinstance(crv, Line):
                continue
            d = crv.Direction.Normalize()
            p0 = crv.GetEndPoint(0)
            p1 = crv.GetEndPoint(1)
            if abs(d.Y) < 0.1:
                orientation = "horizontal"
                coord = (p0.Y + p1.Y) / 2.0
            elif abs(d.X) < 0.1:
                orientation = "vertical"
                coord = (p0.X + p1.X) / 2.0
            else:
                continue

            # Determine which end has the bubble (circle with grid name)
            bubble_end = _get_bubble_end(g, p0, p1)

            grids.append({
                "element": g, "name": g.Name,
                "orientation": orientation, "coord_ft": coord,
                "p0": p0, "p1": p1,
                "bubble_end": bubble_end,  # "p0" or "p1"
            })
        except Exception:
            continue
    return grids


def _get_bubble_end(grid, p0, p1):
    """Determines which end of the grid has the bubble.

    Returns "p0" or "p1".
    If both or neither are visible - returns "p0" (start).
    """
    try:
        b0 = grid.IsBubbleVisibleInView(DatumEnds.End0, view)
        b1 = grid.IsBubbleVisibleInView(DatumEnds.End1, view)
        if b1 and not b0:
            return "p1"
        return "p0"  # default: bubble at start
    except Exception:
        return "p0"


def collect_elements_from_selection(selected_elements):
    """Collects walls and columns from selected elements."""
    elements = []
    seen_ids = set()
    wall_cat_id = ElementId(BuiltInCategory.OST_Walls)
    str_col_cat_id = ElementId(BuiltInCategory.OST_StructuralColumns)
    col_cat_id = ElementId(BuiltInCategory.OST_Columns)

    for e in selected_elements:
        if isinstance(e, Grid):
            continue
        eid = e.Id.IntegerValue
        if eid in seen_ids:
            continue
        seen_ids.add(eid)

        try:
            cat_id = e.Category.Id if e.Category else None
        except Exception:
            continue

        if cat_id == wall_cat_id:
            info = _bbox(e, "Wall")
            if info:
                elements.append(info)
        elif cat_id == str_col_cat_id or cat_id == col_cat_id:
            if isinstance(e, FamilyInstance) and e.SuperComponent is not None:
                continue
            info = _bbox(e, "Column")
            if info:
                elements.append(info)
    return elements


def _bbox(elem, cat):
    try:
        bb = elem.get_BoundingBox(view) or elem.get_BoundingBox(None)
        if not bb:
            return None
        w = abs(bb.Max.X - bb.Min.X)
        d = abs(bb.Max.Y - bb.Min.Y)
        if ft_to_mm(w) < 50 or ft_to_mm(d) < 50:
            return None
        return {
            "element": elem, "category": cat,
            "min_x": bb.Min.X, "max_x": bb.Max.X,
            "min_y": bb.Min.Y, "max_y": bb.Max.Y,
            "cx": (bb.Min.X + bb.Max.X) / 2.0,
            "cy": (bb.Min.Y + bb.Max.Y) / 2.0,
            "w_ft": w, "d_ft": d,
        }
    except Exception:
        return None


# -----------------------------------------
#  REFERENCES
# -----------------------------------------

def get_faces(elem, axis):
    """Gets face references of an element.

    Wall: references directly from Solid - these work.
    FamilyInstance (custom families):
        GetInstanceGeometry() gives correct coordinates, but
        references from it DO NOT WORK for dimensions!
        Solution: GetSymbolGeometry() -> stable ref -> replace type id with instance id.
    """
    opt = Options()
    opt.ComputeReferences = True
    opt.IncludeNonVisibleObjects = False
    opt.View = view
    geo = elem.get_Geometry(opt)
    if not geo:
        if DEBUG:
            output.print_md(u"   ⚠ get_faces: no geometry (id={})".format(elem.Id.IntegerValue))
        return None, None, None, None

    is_family = isinstance(elem, FamilyInstance)
    faces = []

    for item in geo:
        try:
            if isinstance(item, GeometryInstance) and is_family:
                # --- FamilyInstance: symbol geo + stable ref ---
                xform = item.Transform
                sym_geo = item.GetSymbolGeometry()
                if not sym_geo:
                    continue
                for sym_item in sym_geo:
                    if not isinstance(sym_item, Solid) or sym_item.Faces.Size == 0:
                        continue
                    for face in sym_item.Faces:
                        if not isinstance(face, PlanarFace):
                            continue
                        sym_ref = face.Reference
                        if sym_ref is None:
                            continue
                        # Normal and position in world coordinates
                        wn = xform.OfVector(face.FaceNormal)
                        wo = xform.OfPoint(face.Origin)
                        # Convert reference
                        inst_ref = _symbol_to_instance_ref(sym_ref, elem)
                        if inst_ref is None:
                            continue
                        if axis == "x" and abs(wn.X) > 0.9:
                            faces.append((inst_ref, wo.X))
                        elif axis == "y" and abs(wn.Y) > 0.9:
                            faces.append((inst_ref, wo.Y))

            elif isinstance(item, Solid) and item.Faces.Size > 0:
                # --- Wall / direct Solid ---
                for face in item.Faces:
                    if not isinstance(face, PlanarFace):
                        continue
                    ref = face.Reference
                    if ref is None:
                        continue
                    n = face.FaceNormal
                    if axis == "x" and abs(n.X) > 0.9:
                        faces.append((ref, face.Origin.X))
                    elif axis == "y" and abs(n.Y) > 0.9:
                        faces.append((ref, face.Origin.Y))
        except Exception as ex:
            if DEBUG:
                output.print_md(u"   ⚠ scan error: {}".format(str(ex)))
            continue

    if DEBUG:
        output.print_md(u"   🔍 get_faces axis={}: {} faces, family={} (id={})".format(
            axis, len(faces), is_family, elem.Id.IntegerValue))

    if len(faces) < 2:
        if DEBUG:
            _dump_normals(geo, is_family)
        return None, None, None, None

    faces.sort(key=lambda x: x[1])
    if DEBUG:
        output.print_md(u"   📏 lo={:.0f}mm, hi={:.0f}mm".format(
            ft_to_mm(faces[0][1]), ft_to_mm(faces[-1][1])))
    return faces[0][0], faces[-1][0], faces[0][1], faces[-1][1]


def _symbol_to_instance_ref(sym_ref, instance):
    """Converts a reference from GetSymbolGeometry() to an instance reference.

    Stable representation from symbol:  "{typeId}:1:RVTLINK/{faceStuff}"
    For instance we need:               "{instanceId}:1:RVTLINK/{faceStuff}"
    """
    try:
        stable = sym_ref.ConvertToStableRepresentation(doc)
        # stable looks like "12345:1:RVTLINK/0:2:1/..."
        # First token before ":" is the element id (type id)
        # Replace with instance id
        colon_idx = stable.index(":")
        new_stable = str(instance.Id.IntegerValue) + stable[colon_idx:]
        inst_ref = Reference.ParseFromStableRepresentation(doc, new_stable)
        if DEBUG:
            output.print_md(u"      🔗 ref: {} → {}".format(
                stable[:60], new_stable[:60]))
        return inst_ref
    except Exception as ex:
        if DEBUG:
            output.print_md(u"      ❌ ref convert failed: {}".format(str(ex)))
        return None


def _dump_normals(geo, is_family):
    """Dumps all normals for debugging when issues occur."""
    all_n = []
    for item in geo:
        try:
            if isinstance(item, GeometryInstance) and is_family:
                xf = item.Transform
                for si in item.GetSymbolGeometry():
                    if isinstance(si, Solid):
                        for f in si.Faces:
                            if isinstance(f, PlanarFace):
                                wn = xf.OfVector(f.FaceNormal)
                                all_n.append(u"({:.2f},{:.2f},{:.2f})".format(wn.X, wn.Y, wn.Z))
            elif isinstance(item, Solid):
                for f in item.Faces:
                    if isinstance(f, PlanarFace):
                        all_n.append(u"({:.2f},{:.2f},{:.2f})".format(
                            f.FaceNormal.X, f.FaceNormal.Y, f.FaceNormal.Z))
        except Exception:
            pass
    output.print_md(u"   🧊 Normals: {}".format(u", ".join(all_n[:12])))


def get_grid_ref(grid):
    try:
        opt = Options()
        opt.ComputeReferences = True
        opt.IncludeNonVisibleObjects = True
        opt.View = view
        geo = grid.get_Geometry(opt)
        if geo:
            for item in geo:
                if isinstance(item, Line) and item.Reference:
                    return item.Reference
        crv = grid.Curve
        if crv and crv.Reference:
            return crv.Reference
    except Exception:
        pass
    return None


# -----------------------------------------
#  DIMENSION CREATION
# -----------------------------------------

def make_dim(refs, p0, p1, label=""):
    if len(refs) < 2:
        return None
    ra = ReferenceArray()
    for r in refs:
        ra.Append(r)
    try:
        ln = Line.CreateBound(p0, p1)
        if DEBUG:
            d = ln.Direction.Normalize()
            output.print_md(
                u"   📐 make_dim [{}]: {} refs, line ({:.0f},{:.0f})->({:.0f},{:.0f}), dir=({:.2f},{:.2f})".format(
                    label, len(refs),
                    ft_to_mm(p0.X), ft_to_mm(p0.Y),
                    ft_to_mm(p1.X), ft_to_mm(p1.Y),
                    d.X, d.Y))
        dim = doc.Create.NewDimension(view, ln, ra)
        if DEBUG and dim:
            output.print_md(u"   ✅ Dimension created (id={})".format(dim.Id.IntegerValue))
        return dim
    except Exception as e:
        if DEBUG:
            output.print_md(u"   ❌ make_dim ERROR [{}]: **{}**".format(label, str(e)))
        return None


def _displace_small_texts(dim):
    try:
        scale = view.Scale
    except Exception:
        scale = 100

    text_width_mm = 5.0 * scale
    displace_mm = text_width_mm

    try:
        crv = dim.Curve
        if not crv or not isinstance(crv, Line):
            return
        direction = crv.Direction.Normalize()
    except Exception:
        return

    try:
        segs = list(dim.Segments)
        if segs and len(segs) > 0:
            for i, seg in enumerate(segs):
                try:
                    val = seg.Value
                    if val is None:
                        continue
                    val_mm = ft_to_mm(val)
                    if val_mm >= text_width_mm:
                        continue

                    if not seg.IsTextPositionAdjustable():
                        continue

                    tp = seg.TextPosition
                    if tp is None:
                        continue

                    sign = -1.0 if i == 0 else 1.0
                    offset_ft = mm_to_ft(displace_mm)
                    new_tp = XYZ(
                        tp.X + direction.X * offset_ft * sign,
                        tp.Y + direction.Y * offset_ft * sign,
                        tp.Z,
                    )
                    seg.TextPosition = new_tp
                except Exception:
                    continue
            return
    except Exception:
        pass

    try:
        val = dim.Value
        if val is None:
            return
        val_mm = ft_to_mm(val)
        if val_mm >= text_width_mm:
            return

        if not dim.IsTextPositionAdjustable():
            return

        tp = dim.TextPosition
        if tp is None:
            return

        offset_ft = mm_to_ft(displace_mm)
        new_tp = XYZ(
            tp.X + direction.X * offset_ft,
            tp.Y + direction.Y * offset_ft,
            tp.Z,
        )
        dim.TextPosition = new_tp
    except Exception:
        pass


# -----------------------------------------
#  CORE LOGIC
# -----------------------------------------

def dim_along_axis(ei, axis, grids_perpendicular, grids_parallel, all_elems, dims_to_adjust, forced_side=None,
                   occupied_zones=None):
    elem = ei["element"]
    created = 0

    elem_name = elem.Name if hasattr(elem, 'Name') else '?'
    if DEBUG:
        output.print_md(u"---")
        output.print_md(u"### {} (id={}) axis={}  cat={}".format(
            elem_name, elem.Id.IntegerValue, axis, ei["category"]))
        output.print_md(u"   bbox: X[{:.0f}..{:.0f}] Y[{:.0f}..{:.0f}] mm".format(
            ft_to_mm(ei["min_x"]), ft_to_mm(ei["max_x"]),
            ft_to_mm(ei["min_y"]), ft_to_mm(ei["max_y"])))

    ref_lo, ref_hi, c_lo, c_hi = get_faces(elem, axis)
    if ref_lo is None:
        if DEBUG:
            output.print_md(u"   ⏭ Skipped — no faces found")
        return 0

    if axis == "x":
        perp_lo = ei["min_y"]
        perp_hi = ei["max_y"]
    else:
        perp_lo = ei["min_x"]
        perp_hi = ei["max_x"]

    side = _pick_side(ei, axis, grids_parallel, forced_side)

    off1 = mm_to_ft(OFFSET_1_MM)
    off2 = mm_to_ft(OFFSET_2_MM)

    if side < 0:
        line_row1 = perp_lo - off1
        line_row2 = perp_lo - off2
    else:
        line_row1 = perp_hi + off1
        line_row2 = perp_hi + off2

    best_grid, best_dist_ft = _find_nearest_grid(ei, axis, grids_perpendicular)

    if DEBUG:
        if best_grid:
            output.print_md(u"   🎯 Nearest grid: **{}** (dist={:.0f}mm), coord={:.0f}mm".format(
                best_grid["name"], ft_to_mm(best_dist_ft), ft_to_mm(best_grid["coord_ft"])))
        else:
            output.print_md(u"   ⚠ No suitable grid found")

    if best_grid is None or ft_to_mm(best_dist_ft) > MAX_SNAP_DIST_MM:
        if DEBUG:
            output.print_md(u"   → Overall only (no grid / too far)")
        dim_g = _dim_overall(ref_lo, ref_hi, c_lo, c_hi, axis, line_row1)
        if dim_g:
            dims_to_adjust.append(dim_g)
            created += 1
        return created

    grid_coord = best_grid["coord_ft"]
    grid_ref = get_grid_ref(best_grid["element"])
    if grid_ref is None:
        if DEBUG:
            output.print_md(u"   ❌ Failed to get Reference for grid {}".format(best_grid["name"]))
        dim_g = _dim_overall(ref_lo, ref_hi, c_lo, c_hi, axis, line_row1)
        if dim_g:
            dims_to_adjust.append(dim_g)
            created += 1
        return created

    tol_zero = mm_to_ft(ZERO_TOL_MM)
    tol_inter = mm_to_ft(INTERSECT_TOL_MM)

    intersects = (c_lo - tol_inter) < grid_coord < (c_hi + tol_inter)

    if DEBUG:
        output.print_md(u"   face_lo={:.0f}mm, face_hi={:.0f}mm, grid={:.0f}mm, intersects={}".format(
            ft_to_mm(c_lo), ft_to_mm(c_hi), ft_to_mm(grid_coord), intersects))
        output.print_md(u"   side={}, line_row1={:.0f}mm, line_row2={:.0f}mm".format(
            side, ft_to_mm(line_row1), ft_to_mm(line_row2)))

    if intersects:
        d_lo = abs(c_lo - grid_coord)
        d_hi = abs(c_hi - grid_coord)

        is_on_lo = d_lo <= tol_zero
        is_on_hi = d_hi <= tol_zero

        if DEBUG:
            output.print_md(u"   → INTERSECTS: d_lo={:.0f}mm, d_hi={:.0f}mm, on_lo={}, on_hi={}".format(
                ft_to_mm(d_lo), ft_to_mm(d_hi), is_on_lo, is_on_hi))

        if is_on_lo or is_on_hi:
            # Grid coincides with an edge. Create a single dimension.
            refs_snap = [grid_ref]
            if not is_on_lo: refs_snap.append(ref_lo)
            if not is_on_hi: refs_snap.append(ref_hi)

            # Collision check with full span
            if occupied_zones is not None:
                line_row1 = _adjust_perp_for_collisions(
                    axis, c_lo, c_hi, line_row1, side, occupied_zones, grid_coord)

            p0, p1 = _line_pts(c_lo, c_hi, axis, line_row1, grid_coord)
            dim1 = make_dim(refs_snap, p0, p1, "on-edge")
            if dim1:
                dims_to_adjust.append(dim1)
                created += 1
                if occupied_zones is not None:
                    _register_zone(axis, c_lo, c_hi, line_row1, occupied_zones, grid_coord)
        else:
            # Grid strictly inside element. E->G->E and separate Overall
            refs_snap = [ref_lo, grid_ref, ref_hi]

            # Collision check row1
            if occupied_zones is not None:
                line_row1 = _adjust_perp_for_collisions(
                    axis, c_lo, c_hi, line_row1, side, occupied_zones, grid_coord)

            p0, p1 = _line_pts(c_lo, c_hi, axis, line_row1, grid_coord)
            dim1 = make_dim(refs_snap, p0, p1, "inside-EGE")
            if dim1:
                dims_to_adjust.append(dim1)
                created += 1
                if occupied_zones is not None:
                    _register_zone(axis, c_lo, c_hi, line_row1, occupied_zones, grid_coord)

            # Collision check row2 (overall further from row1)
            min_gap = mm_to_ft(OFFSET_2_MM - OFFSET_1_MM)
            if side < 0:
                line_row2 = min(line_row1 - min_gap, line_row2)
            else:
                line_row2 = max(line_row1 + min_gap, line_row2)
            if occupied_zones is not None:
                line_row2 = _adjust_perp_for_collisions(
                    axis, c_lo, c_hi, line_row2, side, occupied_zones)

            dim_g = _dim_overall(ref_lo, ref_hi, c_lo, c_hi, axis, line_row2)
            if dim_g:
                dims_to_adjust.append(dim_g)
                created += 1
                if occupied_zones is not None:
                    _register_zone(axis, c_lo, c_hi, line_row2, occupied_zones)

    else:
        # Scenario: grid does NOT intersect element. Build a single chain G->E->E
        if DEBUG:
            output.print_md(u"   → OUTSIDE: chain G->E->E")
        refs_chain = [grid_ref, ref_lo, ref_hi]

        span_min = min(c_lo, c_hi, grid_coord)
        span_max = max(c_lo, c_hi, grid_coord)

        # Collision check with full span (from grid to element)
        if occupied_zones is not None:
            line_row1 = _adjust_perp_for_collisions(
                axis, span_min, span_max, line_row1, side, occupied_zones)

        # Check collisions with other elements
        safe_line_row1 = _avoid_collision(
            ei, line_row1, span_min, span_max,
            axis, side, all_elems or []
        )

        p0, p1 = _line_pts(c_lo, c_hi, axis, safe_line_row1, grid_coord)
        dim_chain = make_dim(refs_chain, p0, p1, "outside-GEE")
        if dim_chain:
            dims_to_adjust.append(dim_chain)
            created += 1
            if occupied_zones is not None:
                _register_zone(axis, span_min, span_max, safe_line_row1, occupied_zones)

    return created


def _dim_overall(ref_lo, ref_hi, c_lo, c_hi, axis, perp_pos):
    p0, p1 = _line_pts(c_lo, c_hi, axis, perp_pos)
    return make_dim([ref_lo, ref_hi], p0, p1, "overall")


def _line_pts(coord_lo, coord_hi, axis, perp_pos, grid_coord=None):
    lo = min(coord_lo, coord_hi)
    hi = max(coord_lo, coord_hi)
    if grid_coord is not None:
        lo = min(lo, grid_coord)
        hi = max(hi, grid_coord)

    if axis == "x":
        return XYZ(lo, perp_pos, 0), XYZ(hi, perp_pos, 0)
    else:
        return XYZ(perp_pos, lo, 0), XYZ(perp_pos, hi, 0)


def _pick_side(ei, axis, grids_parallel, forced_side=None):
    """Chooses the side for the dimension line.

    If forced_side is set — use it (for X and Y consistency).
    Otherwise determined by the nearest parallel grid.

    Rule: X-dimensions and Y-dimensions go in the same "diagonal":
      X down  → Y left   (both side=-1)
      X up    → Y right  (both side=+1)
    This way they don't overlap each other.
    """
    if forced_side is not None:
        if DEBUG:
            output.print_md(u"   📍 _pick_side axis={}: forced side={}".format(axis, forced_side))
        return forced_side

    if not grids_parallel:
        if axis == "x":
            return -1
        else:
            return -1  # consistent with X default

    if axis == "x":
        elem_center = ei["cy"]
    else:
        elem_center = ei["cx"]

    best_grid = None
    best_d = None
    best_sign = 0
    for g in grids_parallel:
        d = g["coord_ft"] - elem_center
        abs_d = abs(d)
        if best_d is None or abs_d < best_d:
            best_d = abs_d
            best_grid = g
            best_sign = d

    if best_grid is None:
        return -1

    side = -1 if best_sign < 0 else +1
    if DEBUG:
        output.print_md(u"   📍 _pick_side axis={}: parallel grid **{}** ({:.0f}mm), center={:.0f}mm → side={}".format(
            axis, best_grid["name"], ft_to_mm(best_grid["coord_ft"]),
            ft_to_mm(elem_center), side))
    return side


def _find_nearest_grid(ei, axis, grids):
    if axis == "x":
        elem_center = ei["cx"]
    else:
        elem_center = ei["cy"]
    best = None
    best_d = None
    for g in grids:
        d = abs(elem_center - g["coord_ft"])
        if best_d is None or d < best_d:
            best_d = d
            best = g
    if DEBUG:
        output.print_md(u"   🔎 _find_nearest_grid axis={}: {} grids available, center={:.0f}mm".format(
            axis, len(grids), ft_to_mm(elem_center)))
    return best, best_d if best_d is not None else (None, None)


def _avoid_collision(ei, perp_pos, coord_lo, coord_hi, axis, side, all_elems):
    margin = mm_to_ft(200)
    my_id = ei["element"].Id.IntegerValue
    lo = min(coord_lo, coord_hi)
    hi = max(coord_lo, coord_hi)

    for other in all_elems:
        if other["element"].Id.IntegerValue == my_id:
            continue

        if axis == "x":
            if other["max_x"] < lo or other["min_x"] > hi:
                continue
            if other["min_y"] - margin < perp_pos < other["max_y"] + margin:
                if side < 0:
                    perp_pos = min(perp_pos, other["min_y"] - margin)
                else:
                    perp_pos = max(perp_pos, other["max_y"] + margin)
        else:
            if other["max_y"] < lo or other["min_y"] > hi:
                continue
            if other["min_x"] - margin < perp_pos < other["max_x"] + margin:
                if side < 0:
                    perp_pos = min(perp_pos, other["min_x"] - margin)
                else:
                    perp_pos = max(perp_pos, other["max_x"] + margin)

    return perp_pos


# -----------------------------------------
#  DIMENSION COLLISION PREVENTION
# -----------------------------------------

COLLISION_SHIFT_MM = 300  # shift step on collision
COLLISION_MAX_PASSES = 3


def _make_zone(axis, coord_lo, coord_hi, perp_pos, height_ft=None):
    """Creates a rectangular zone for dimension collision checking.

    axis=x: horizontal line at perp_pos along Y, span along X from coord_lo to coord_hi
    axis=y: vertical line at perp_pos along X, span along Y from coord_lo to coord_hi
    """
    if height_ft is None:
        height_ft = mm_to_ft(200)  # half-height of dimension zone
    lo = min(coord_lo, coord_hi)
    hi = max(coord_lo, coord_hi)
    if axis == "x":
        return (lo, perp_pos - height_ft, hi, perp_pos + height_ft)
    else:
        return (perp_pos - height_ft, lo, perp_pos + height_ft, hi)


def _zone_overlaps(zone, occupied):
    """Checks if zone intersects with any of the occupied zones."""
    for oz in occupied:
        if zone[2] <= oz[0] or oz[2] <= zone[0]:
            continue
        if zone[3] <= oz[1] or oz[3] <= zone[1]:
            continue
        return True
    return False


def _adjust_perp_for_collisions(axis, coord_lo, coord_hi, perp_pos, side, occupied, grid_coord=None):
    """Shifts perp_pos until the dimension zone no longer overlaps with occupied zones."""
    lo = min(coord_lo, coord_hi)
    hi = max(coord_lo, coord_hi)
    if grid_coord is not None:
        lo = min(lo, grid_coord)
        hi = max(hi, grid_coord)

    shift = mm_to_ft(COLLISION_SHIFT_MM)
    original_perp = perp_pos
    for attempt in range(COLLISION_MAX_PASSES):
        zone = _make_zone(axis, lo, hi, perp_pos)
        if not _zone_overlaps(zone, occupied):
            break
        if DEBUG:
            output.print_md(u"   ⚠ COLLISION pass {}: perp={:.0f}mm overlaps, shifting by {}mm".format(
                attempt + 1, ft_to_mm(perp_pos), COLLISION_SHIFT_MM * (1 if side > 0 else -1)))
        perp_pos += shift * side
    if DEBUG and perp_pos != original_perp:
        output.print_md(u"   ↔ SHIFTED: {:.0f}mm → {:.0f}mm".format(
            ft_to_mm(original_perp), ft_to_mm(perp_pos)))
    return perp_pos


def _register_zone(axis, coord_lo, coord_hi, perp_pos, occupied, grid_coord=None):
    """Registers an occupied zone after a dimension is created."""
    lo = min(coord_lo, coord_hi)
    hi = max(coord_lo, coord_hi)
    if grid_coord is not None:
        lo = min(lo, grid_coord)
        hi = max(hi, grid_coord)
    zone = _make_zone(axis, lo, hi, perp_pos)
    occupied.append(zone)


# -----------------------------------------
#  GRID CHAINS
# -----------------------------------------

def _grid_chain_exists(grids_sorted, measure_axis):
    """Checks if a dimension chain between the given grids already exists.

    Searches all Dimensions on the view and checks if they
    reference the same grids (by ElementId).
    """
    grid_ids = set()
    for g in grids_sorted:
        grid_ids.add(g["element"].Id.IntegerValue)

    if len(grid_ids) < 2:
        return False

    try:
        dims_on_view = FilteredElementCollector(doc, view.Id).OfClass(Dimension).ToElements()
    except Exception:
        return False

    for dim in dims_on_view:
        try:
            refs = dim.References
            if refs is None or refs.Size < 2:
                continue

            dim_ref_ids = set()
            for ref in refs:
                eid = ref.ElementId.IntegerValue
                dim_ref_ids.add(eid)

            # If all our grids are in this dimension's references — chain already exists
            if grid_ids.issubset(dim_ref_ids):
                if DEBUG:
                    output.print_md(u"   ⏭ Grid chain already exists (dim id={})".format(
                        dim.Id.IntegerValue))
                return True
        except Exception:
            continue

    return False


def make_grid_chain(grids_sorted, measure_axis, offset_mm):
    """Creates a dimension chain between grids.

    Placement: offset from the grid ends where bubbles (circles) are.
    Direction — outward from the bubble.
    """
    if len(grids_sorted) < 2:
        return 0

    # Check if such a chain already exists
    if _grid_chain_exists(grids_sorted, measure_axis):
        return 0

    refs = []
    for g in grids_sorted:
        r = get_grid_ref(g["element"])
        if r:
            refs.append(r)
    if len(refs) < 2:
        return 0

    # Determine bubble position and shift direction
    bubble_coord, bubble_side = _get_bubble_baseline(grids_sorted, measure_axis)

    # Check existing dimensions to avoid overlap
    existing_offset_ft = _find_existing_grid_dim_offset(grids_sorted, measure_axis, bubble_side)

    off = mm_to_ft(offset_mm)

    if bubble_side > 0:
        # Dimensions above/right of bubble → offset up/right
        base = max(bubble_coord, existing_offset_ft) if existing_offset_ft is not None else bubble_coord
        perp = base + off
    else:
        # Dimensions below/left of bubble → offset down/left
        base = min(bubble_coord, existing_offset_ft) if existing_offset_ft is not None else bubble_coord
        perp = base - off

    if measure_axis == "x":
        p0 = XYZ(grids_sorted[0]["coord_ft"], perp, 0)
        p1 = XYZ(grids_sorted[-1]["coord_ft"], perp, 0)
    else:
        p0 = XYZ(perp, grids_sorted[0]["coord_ft"], 0)
        p1 = XYZ(perp, grids_sorted[-1]["coord_ft"], 0)

    if DEBUG:
        output.print_md(u"   📏 chain {}: perp={:.0f}mm, bubble_side={}, base={:.0f}mm (exist={})".format(
            measure_axis, ft_to_mm(perp), bubble_side, ft_to_mm(bubble_coord),
            u"{:.0f}mm".format(ft_to_mm(existing_offset_ft)) if existing_offset_ft is not None else "none"))

    ra = ReferenceArray()
    for r in refs:
        ra.Append(r)
    try:
        dim = doc.Create.NewDimension(view, Line.CreateBound(p0, p1), ra)
        return 1 if dim else 0
    except Exception as e:
        if DEBUG:
            output.print_md(u"⚠ chain: {}".format(str(e)))
        return 0


def _get_bubble_baseline(grids_sorted, measure_axis):
    """Determines the bubble-end coordinate and shift direction.

    Returns:
        (bubble_coord_ft, side): side=+1 outward up/right, -1 outward down/left
    """
    bubble_coords = []
    non_bubble_coords = []

    for g in grids_sorted:
        be = g.get("bubble_end", "p0")
        bp = g[be]  # bubble point
        nbp = g["p1"] if be == "p0" else g["p0"]  # opposite end

        if measure_axis == "x":
            # V-grids: measure along X, chain offset along Y
            bubble_coords.append(bp.Y)
            non_bubble_coords.append(nbp.Y)
        else:
            # H-grids: measure along Y, chain offset along X
            bubble_coords.append(bp.X)
            non_bubble_coords.append(nbp.X)

    avg_bubble = sum(bubble_coords) / len(bubble_coords)
    avg_non_bubble = sum(non_bubble_coords) / len(non_bubble_coords)

    # Bubble is outward from the building. Dimensions placed INWARD from bubble
    # (between bubble and elements — closer to the building)
    if avg_bubble > avg_non_bubble:
        # Bubble above/right → dimensions slightly below/left of bubble (inward)
        bubble_edge = max(bubble_coords)
        return bubble_edge, -1  # inward = minus
    else:
        # Bubble below/left → dimensions slightly above/right of bubble (inward)
        bubble_edge = min(bubble_coords)
        return bubble_edge, +1  # inward = plus


def _find_existing_grid_dim_offset(grids_sorted, measure_axis, side=1):
    """Finds the position of existing grid dimension chains to avoid overlap.

    side=+1: look for maximum coordinate (above/right)
    side=-1: look for minimum coordinate (below/left)
    """
    grid_ids = set(g["element"].Id.IntegerValue for g in grids_sorted)

    try:
        dims_on_view = FilteredElementCollector(doc, view.Id).OfClass(Dimension).ToElements()
    except Exception:
        return None

    best_perp = None

    for dim in dims_on_view:
        try:
            refs = dim.References
            if refs is None or refs.Size < 2:
                continue

            match_count = 0
            for ref in refs:
                if ref.ElementId.IntegerValue in grid_ids:
                    match_count += 1

            if match_count < 2:
                continue

            crv = dim.Curve
            if crv and isinstance(crv, Line):
                if measure_axis == "x":
                    if side > 0:
                        perp = max(crv.GetEndPoint(0).Y, crv.GetEndPoint(1).Y)
                        if best_perp is None or perp > best_perp:
                            best_perp = perp
                    else:
                        perp = min(crv.GetEndPoint(0).Y, crv.GetEndPoint(1).Y)
                        if best_perp is None or perp < best_perp:
                            best_perp = perp
                else:
                    if side > 0:
                        perp = max(crv.GetEndPoint(0).X, crv.GetEndPoint(1).X)
                        if best_perp is None or perp > best_perp:
                            best_perp = perp
                    else:
                        perp = min(crv.GetEndPoint(0).X, crv.GetEndPoint(1).X)
                        if best_perp is None or perp < best_perp:
                            best_perp = perp
        except Exception:
            continue

    return best_perp


# -----------------------------------------
#  MAIN
# -----------------------------------------

def main():
    if not isinstance(view, ViewPlan):
        forms.alert(u"Please open a plan view.", title=__title__)
        return

    # --- Box selection ---
    try:
        sel_refs = uidoc.Selection.PickObjects(
            ObjectType.Element,
            u"Box-select grids, walls, and columns, then press Enter"
        )
    except Exception:
        # User pressed Esc
        return

    if not sel_refs:
        forms.alert(u"Nothing selected.", title=__title__)
        return

    selected_elements = [doc.GetElement(r.ElementId) for r in sel_refs]

    all_grids = collect_grids_from_selection(selected_elements)
    all_elems = collect_elements_from_selection(selected_elements)

    h_grids = sorted([g for g in all_grids if g["orientation"] == "horizontal"],
                     key=lambda g: g["coord_ft"])
    v_grids = sorted([g for g in all_grids if g["orientation"] == "vertical"],
                     key=lambda g: g["coord_ft"])

    if DEBUG:
        n_walls = sum(1 for e in all_elems if e["category"] == "Wall")
        n_cols = sum(1 for e in all_elems if e["category"] == "Column")
        output.print_md(u"## Data (from selection)")
        output.print_md(u"- H grids: **{}** ({})".format(
            len(h_grids), u", ".join(g["name"] for g in h_grids)))
        output.print_md(u"- V grids: **{}** ({})".format(
            len(v_grids), u", ".join(g["name"] for g in v_grids)))
        output.print_md(u"- Elements: **{}** (walls: {}, columns: {})".format(
            len(all_elems), n_walls, n_cols))

    if not all_elems:
        forms.alert(u"No walls or columns in the selection.", title=__title__)
        return

    if not all_grids:
        forms.alert(u"No grids in the selection. Please select at least one grid.", title=__title__)
        return

    tg = TransactionGroup(doc, u"Auto Dims SC v5")
    tg.Start()
    total = 0
    failure_handler = DimFailureSwallower()

    try:
        # 1. Build grid chains
        #    Side is determined automatically by bubble (circle) position
        #    Dimensions are placed between bubbles and elements (inward from circles)
        t1 = Transaction(doc, u"Chains")
        opts1 = t1.GetFailureHandlingOptions()
        opts1.SetFailuresPreprocessor(failure_handler)
        t1.SetFailureHandlingOptions(opts1)
        t1.Start()
        n_chains = 0
        if len(v_grids) >= 2:
            # Pairwise chain of V-grids
            n_chains += make_grid_chain(v_grids, "x", OFFSET_CHAIN_1_MM)
            # Overall (extreme grids) — further from bubble
            if len(v_grids) > 2:
                n_chains += make_grid_chain(
                    [v_grids[0], v_grids[-1]], "x",
                    OFFSET_CHAIN_1_MM + OFFSET_CHAIN_GAP_MM)
        if len(h_grids) >= 2:
            # Pairwise chain of H-grids
            n_chains += make_grid_chain(h_grids, "y", OFFSET_CHAIN_1_MM)
            # Overall (extreme grids) — further from bubble
            if len(h_grids) > 2:
                n_chains += make_grid_chain(
                    [h_grids[0], h_grids[-1]], "y",
                    OFFSET_CHAIN_1_MM + OFFSET_CHAIN_GAP_MM)
        t1.Commit()
        total += n_chains
        if DEBUG:
            output.print_md(u"✅ Grid chains: **{}**".format(n_chains))

        # 2. Build snaps and overalls
        t2 = Transaction(doc, u"Snaps+Overalls")
        opts2 = t2.GetFailureHandlingOptions()
        opts2.SetFailuresPreprocessor(failure_handler)
        t2.SetFailureHandlingOptions(opts2)
        t2.Start()
        n_x = 0
        n_y = 0
        dims_to_adjust = []
        occupied_zones = []  # registry of occupied zones for collision prevention

        for ei in all_elems:
            # Compute side for X — same for Y (same diagonal)
            side_x = _pick_side(ei, "x", h_grids)
            side_y = side_x

            try:
                n_x += dim_along_axis(ei, "x", v_grids, h_grids, all_elems, dims_to_adjust,
                                      forced_side=side_x, occupied_zones=occupied_zones)
            except Exception as e:
                if DEBUG:
                    output.print_md(u"⚠ Error on X axis: {}".format(str(e)))
            try:
                n_y += dim_along_axis(ei, "y", h_grids, v_grids, all_elems, dims_to_adjust,
                                      forced_side=side_y, occupied_zones=occupied_zones)
            except Exception as e:
                if DEBUG:
                    output.print_md(u"⚠ Error on Y axis: {}".format(str(e)))

        # Regeneration is required before calling TextPosition
        doc.Regenerate()

        for d in dims_to_adjust:
            _displace_small_texts(d)

        t2.Commit()
        total += n_x + n_y
        if DEBUG:
            output.print_md(u"✅ Dimensions along X: **{}**, along Y: **{}**".format(n_x, n_y))
            if occupied_zones:
                output.print_md(u"📦 Reserved zones: **{}**".format(len(occupied_zones)))
            if failure_handler.had_errors:
                output.print_md(u"⚠ Revit errors (auto-resolved): **{}**".format(len(failure_handler.had_errors)))
                for err_msg in failure_handler.had_errors:
                    output.print_md(u"   - {}".format(err_msg))

        tg.Assimilate()

    except Exception as e:
        tg.RollBack()
        forms.alert(u"Error:\n{}".format(str(e)), title=__title__)
        return

    output.print_md(u"---")
    output.print_md(u"## Result: **{}** dimensions created".format(total))


if __name__ == "__main__":
    main()