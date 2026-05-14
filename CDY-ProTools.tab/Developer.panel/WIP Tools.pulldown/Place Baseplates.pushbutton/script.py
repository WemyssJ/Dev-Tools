# -*- coding: utf-8 -*-
"""
Place Baseplate at Columns (FINAL - RAYCAST HOSTING)
---------------------------------------------------
✔ Correct host via raycast DOWN (first face hit)
✔ Uses true column base Z (incl. offsets)
✔ Auto-finds 3D view if needed
✔ Correct Z fallback for non-face-hosted families
"""

import clr
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Structure import StructuralType
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType
from Autodesk.Revit.Exceptions import OperationCanceledException

from pyrevit import revit, forms, script

doc    = revit.doc
uidoc  = revit.uidoc
logger = script.get_logger()


# ---------------------------
# Selection Filters
# ---------------------------

class AnyFamilyFilter(ISelectionFilter):
    def AllowElement(self, elem):
        return isinstance(elem, FamilyInstance)
    def AllowReference(self, ref, point):
        return False


class ColumnFilter(ISelectionFilter):
    def AllowElement(self, elem):
        return isinstance(elem, FamilyInstance) and \
               elem.Category.Id.IntegerValue == int(BuiltInCategory.OST_StructuralColumns)
    def AllowReference(self, ref, point):
        return False


# ---------------------------
# Helpers
# ---------------------------

def get_instance_z(inst):
    loc = inst.Location
    if isinstance(loc, LocationPoint):
        return loc.Point.Z
    return None


def get_level_elevation(inst):
    for bip in [BuiltInParameter.FAMILY_BASE_LEVEL_PARAM,
                BuiltInParameter.FAMILY_LEVEL_PARAM]:
        p = inst.get_Parameter(bip)
        if p:
            lvl = doc.GetElement(p.AsElementId())
            if lvl:
                return lvl.Elevation
    return None


def get_column_xy(col):
    loc = col.Location
    if isinstance(loc, LocationPoint):
        pt = loc.Point
        return pt.X, pt.Y
    return None, None


def get_column_level(col):
    p = col.get_Parameter(BuiltInParameter.FAMILY_BASE_LEVEL_PARAM)
    if p:
        return doc.GetElement(p.AsElementId())
    return None


def get_column_level_elev(col):
    lvl = get_column_level(col)
    return lvl.Elevation if lvl else None


def get_column_base_z(col):
    """
    True physical base Z of column (includes base offset)
    """
    loc = col.Location
    if not isinstance(loc, LocationPoint):
        return None

    z = loc.Point.Z

    p = col.get_Parameter(BuiltInParameter.SCHEDULE_BASE_LEVEL_OFFSET_PARAM)
    if p:
        z += p.AsDouble()

    return z


def get_column_rotation(col):
    loc = col.Location
    return getattr(loc, "Rotation", 0.0)


def rotate_instance(inst, pt, angle):
    if abs(angle) < 1e-6:
        return
    axis = Line.CreateBound(pt, XYZ(pt.X, pt.Y, pt.Z + 1))
    ElementTransformUtils.RotateElement(doc, inst.Id, axis, angle)


def is_face_hosted(inst):
    sym = doc.GetElement(inst.GetTypeId())
    return getattr(sym.Family, "IsFaceHosted", False)


# ---------------------------
# 🔥 Get a valid 3D view
# ---------------------------

def get_3d_view():
    view = doc.ActiveView
    if isinstance(view, View3D) and not view.IsTemplate:
        return view

    # fallback: find any 3D view
    views = FilteredElementCollector(doc).OfClass(View3D)
    for v in views:
        if not v.IsTemplate:
            return v

    raise Exception("No valid 3D view found for raycasting.")


# ---------------------------
# 🔥 RAYCAST HOST FINDER
# ---------------------------

def find_host_face_reference(search_pt, view3d):
    """
    Raycast DOWN to find FIRST face below point.
    """

    direction = XYZ(0, 0, -1)

    # Filter for Floors + Structural Foundations
    cat_filter = ElementMulticategoryFilter([
        BuiltInCategory.OST_Floors,
        BuiltInCategory.OST_StructuralFoundation
    ])

    ref_intersector = ReferenceIntersector(
        cat_filter,
        FindReferenceTarget.Face,
        view3d
    )

    ref_intersector.FindReferencesInRevitLinks = True

    results = ref_intersector.Find(search_pt, direction)

    for res in results:
        ref = res.GetReference()
        if ref:
            return ref

    return None


# ---------------------------
# Placement
# ---------------------------

def place_instance(symbol, pt, level, host_ref, face_hosted):
    if face_hosted and host_ref:
        return doc.Create.NewFamilyInstance(host_ref, pt, XYZ.BasisX, symbol)

    if level:
        return doc.Create.NewFamilyInstance(pt, symbol, level, StructuralType.NonStructural)

    return doc.Create.NewFamilyInstance(pt, symbol, StructuralType.NonStructural)


# ---------------------------
# MAIN
# ---------------------------

def main():

    forms.alert("Select baseplate template", ok=True)

    try:
        ref = uidoc.Selection.PickObject(ObjectType.Element, AnyFamilyFilter())
    except OperationCanceledException:
        return

    template = doc.GetElement(ref.ElementId)
    symbol   = doc.GetElement(template.GetTypeId())

    template_z = get_instance_z(template)
    template_lvl_elev = get_level_elevation(template)
    face_hosted = is_face_hosted(template)

    view3d = get_3d_view()

    forms.alert("Select columns", ok=True)

    try:
        refs = uidoc.Selection.PickObjects(ObjectType.Element, ColumnFilter())
    except OperationCanceledException:
        return

    cols = [doc.GetElement(r.ElementId) for r in refs]

    if not symbol.IsActive:
        with Transaction(doc, "Activate") as t:
            t.Start()
            symbol.Activate()
            doc.Regenerate()
            t.Commit()

    with Transaction(doc, "Place Baseplates") as t:
        t.Start()

        for col in cols:

            x, y = get_column_xy(col)
            if x is None:
                continue

            col_lvl = get_column_level(col)
            col_lvl_elev = col_lvl.Elevation if col_lvl else None

            # Placement Z (for non-face-hosted fallback)
            if template_lvl_elev and col_lvl_elev:
                z = template_z + (col_lvl_elev - template_lvl_elev)
            else:
                z = template_z

            placement_pt = XYZ(x, y, z)

            # 🔥 TRUE column base for raycast
            col_base_z = get_column_base_z(col)
            if col_base_z is None:
                logger.warning("Column {} has no valid base Z".format(col.Id))
                continue

            search_pt = XYZ(x, y, col_base_z + 1.0)  # start slightly above

            host_ref = None
            if face_hosted:
                host_ref = find_host_face_reference(search_pt, view3d)

            if not host_ref and face_hosted:
                logger.warning("No host found for column {}".format(col.Id))
                continue

            inst = place_instance(symbol, placement_pt, col_lvl, host_ref, face_hosted)

            # Fix Z if NOT face hosted
            if not face_hosted and col_lvl:
                p = inst.get_Parameter(BuiltInParameter.INSTANCE_FREE_HOST_OFFSET_PARAM)
                if p:
                    p.Set(z - col_lvl.Elevation)

            rotate_instance(inst, placement_pt, get_column_rotation(col))

        t.Commit()

    forms.alert("Baseplates placed correctly.")


if __name__ == "__main__":
    main()