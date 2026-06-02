# -*- coding: utf-8 -*-

from pyrevit import revit
from Autodesk.Revit.DB import *
from System.Collections.Generic import List
import colorsys

doc = revit.doc
view = doc.ActiveView


# ============================================================
# STABLE HASH
# ============================================================

def stable_hash(n):
    n = (n ^ 61) ^ (n >> 16)
    n = n + (n << 3)
    n = n ^ (n >> 4)
    n = n * 0x27d4eb2d
    n = n ^ (n >> 15)
    return n & 0xFFFFFFFF


# ============================================================
# HIGH-VARIETY COLOUR SYSTEM (HSV 3D DISTRIBUTION)
# ============================================================

def make_colour_from_id(elem_int_id):

    h = stable_hash(elem_int_id)

    # Hue: full distribution
    hue = (h & 0xFF) / 255.0

    # Saturation: wide spread (prevents “same tone families”)
    sat = 0.55 + (((h >> 8) & 0x7F) / 255.0) * 0.4  # 0.55–0.95

    # Value: brightness variation (breaks visual clustering)
    val = 0.60 + (((h >> 16) & 0x7F) / 255.0) * 0.40  # 0.60–1.0

    # slight nonlinear shift to avoid banding
    hue = (hue * 0.93 + 0.07) % 1.0

    r, g, b = colorsys.hsv_to_rgb(hue, sat, val)

    return Color(int(r * 255), int(g * 255), int(b * 255))


# ============================================================
# TAG RESOLUTION
# ============================================================

def get_tagged_element_id(tag):
    try:
        ids = list(tag.GetTaggedLocalElementIds())
        if ids:
            return ids[0]
    except:
        pass

    try:
        return tag.TaggedLocalElementId
    except:
        return None


# ============================================================
# SOLID FILL PATTERN (for hatch visibility)
# ============================================================

def get_solid_fill_id():
    for f in FilteredElementCollector(doc).OfClass(FillPatternElement):
        try:
            if f.GetFillPattern().IsSolidFill:
                return f.Id
        except:
            pass
    return ElementId.InvalidElementId


# ============================================================
# SHIFT CLICK = RESET
# ============================================================

if __shiftclick__:

    t = Transaction(doc, "Reset QA Mode")

    try:
        t.Start()

        # --------------------------------------------
        # RESTORE LINKS + CAD
        # --------------------------------------------

        show_ids = List[ElementId]()

        for link in FilteredElementCollector(doc).OfClass(RevitLinkInstance):
            show_ids.Add(link.Id)

        for cad in FilteredElementCollector(doc).OfClass(ImportInstance):
            show_ids.Add(cad.Id)

        if show_ids.Count > 0:
            view.UnhideElements(show_ids)

        # --------------------------------------------
        # CLEAR OVERRIDES
        # --------------------------------------------

        for e in FilteredElementCollector(doc, view.Id):
            try:
                view.SetElementOverrides(e.Id, OverrideGraphicSettings())
            except:
                pass

        t.Commit()

    except Exception as ex:
        if t.HasStarted() and not t.HasEnded():
            t.RollBack()
        raise ex

    print("QA mode cleared.")


# ============================================================
# NORMAL CLICK = APPLY QA MODE
# ============================================================

else:

    t = Transaction(doc, "QA Tag Matcher (High Variety Colours)")

    try:
        t.Start()

        # --------------------------------------------
        # HIDE LINKS + CAD
        # --------------------------------------------

        hide_ids = List[ElementId]()

        for link in FilteredElementCollector(doc).OfClass(RevitLinkInstance):
            hide_ids.Add(link.Id)

        for cad in FilteredElementCollector(doc).OfClass(ImportInstance):
            hide_ids.Add(cad.Id)

        if hide_ids.Count > 0:
            view.HideElements(hide_ids)

        # --------------------------------------------
        # GREY BASE VIEW (DETAIL LINES + HATCHES INCLUDED)
        # --------------------------------------------

        grey = Color(180, 180, 180)
        solid_fill_id = get_solid_fill_id()

        grey_ogs = OverrideGraphicSettings()

        grey_ogs.SetProjectionLineColor(grey)
        grey_ogs.SetCutLineColor(grey)

        if solid_fill_id != ElementId.InvalidElementId:
            grey_ogs.SetSurfaceForegroundPatternId(solid_fill_id)
            grey_ogs.SetSurfaceForegroundPatternColor(grey)

            grey_ogs.SetCutForegroundPatternId(solid_fill_id)
            grey_ogs.SetCutForegroundPatternColor(grey)

        for e in FilteredElementCollector(doc, view.Id):
            try:
                view.SetElementOverrides(e.Id, grey_ogs)
            except:
                pass

        # --------------------------------------------
        # TAG → ELEMENT GROUPING
        # --------------------------------------------

        tags = (
            FilteredElementCollector(doc, view.Id)
            .OfClass(IndependentTag)
            .WhereElementIsNotElementType()
        )

        element_map = {}

        for tag in tags:

            elem_id = get_tagged_element_id(tag)

            if elem_id and elem_id != ElementId.InvalidElementId:

                key = elem_id.IntegerValue

                if key not in element_map:
                    element_map[key] = {
                        "elem_id": elem_id,
                        "tags": []
                    }

                element_map[key]["tags"].append(tag.Id)

        if not element_map:
            t.Commit()
            print("No tag-element relationships found.")
            raise SystemExit

        # --------------------------------------------
        # APPLY HIGH-VARIETY COLOURS
        # --------------------------------------------

        for data in element_map.values():

            elem_id = data["elem_id"]
            tag_list = data["tags"]

            # ✔ HIGH VARIETY COLOUR
            col = make_colour_from_id(elem_id.IntegerValue)

            # ----------------------------------------
            # ELEMENT (FULL PATTERN HIGHLIGHT)
            # ----------------------------------------

            elem_ogs = OverrideGraphicSettings()

            elem_ogs.SetProjectionLineColor(col)
            elem_ogs.SetCutLineColor(col)

            if solid_fill_id != ElementId.InvalidElementId:
                elem_ogs.SetSurfaceForegroundPatternId(solid_fill_id)
                elem_ogs.SetSurfaceForegroundPatternColor(col)

                elem_ogs.SetCutForegroundPatternId(solid_fill_id)
                elem_ogs.SetCutForegroundPatternColor(col)

            try:
                view.SetElementOverrides(elem_id, elem_ogs)
            except:
                pass

            # ----------------------------------------
            # TAGS (MATCH ELEMENT)
            # ----------------------------------------

            tag_ogs = OverrideGraphicSettings()
            tag_ogs.SetProjectionLineColor(col)
            tag_ogs.SetCutLineColor(col)

            for tag_id in tag_list:
                try:
                    view.SetElementOverrides(tag_id, tag_ogs)
                except:
                    pass

        t.Commit()

        print("QA mode active: {} elements grouped".format(len(element_map)))

    except Exception as ex:
        if t.HasStarted() and not t.HasEnded():
            t.RollBack()
        raise ex