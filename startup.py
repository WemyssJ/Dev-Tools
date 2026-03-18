# -*- coding: utf-8 -*-
"""
CDY-ProTools startup.py
  - Hides Developer panel and pyRevit tab until unlocked
  - Registers Rebar Spacing Calculator dockable panel
  - Registers CDY Tools dockable panel (5 tabs)
"""

# =============================================================================
# IMPORTS
# =============================================================================

import clr
import os
import os.path as op
import math
import datetime
import json
import subprocess
import threading

clr.AddReference("AdWindows")
clr.AddReference("PresentationFramework")
clr.AddReference("PresentationCore")
clr.AddReference("WindowsBase")

import Autodesk.Windows as AdWindows
import Autodesk.Revit.DB as DB

from System import EventHandler, Action
from System.Windows import Thickness, FontWeights, TextWrapping
from System.Windows.Controls import (
    StackPanel, TextBox, Button, TextBlock,
    TabControl, TabItem, ScrollViewer,
    ComboBox, ComboBoxItem, CheckBox, Separator
)
from System.Windows.Controls import ScrollBarVisibility
from System.Windows.Media import Brushes, SolidColorBrush
from System.Windows import Media

from Autodesk.Revit.UI import IExternalEventHandler, ExternalEvent
from Autodesk.Revit.UI.Events import IdlingEventArgs
from Autodesk.Revit.DB import (
    FilteredElementCollector, BuiltInCategory, Transaction,
    ViewSheet, IndependentTag, TagMode, TagOrientation,
    Reference, UV, UnitUtils, UnitTypeId, ElementId,
    BuiltInParameter, Line, XYZ, ReferenceArray,
    ViewDuplicateOption
)
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType

from pyrevit import forms, HOST_APP


# =============================================================================
# SECTION 1 — HIDE DEVELOPER / PYREVIT UNTIL UNLOCKED
# =============================================================================

TAB_NAME       = "CDY-ProTools"
DEV_PANEL_NAME = "Developer"
PYRVT_TAB_NAME = "pyRevit"
UNLOCK_FILE    = os.path.join(os.getenv("APPDATA"), "CDY-ProTools", "dev_unlock.json")


def hide_panels():
    ribbon = AdWindows.ComponentManager.Ribbon
    if not ribbon:
        return
    visible = False
    if os.path.exists(UNLOCK_FILE):
        try:
            with open(UNLOCK_FILE, "r") as f:
                data = json.load(f)
            if data.get("unlocked", False):
                visible = True
        except:
            visible = False
    for tab in ribbon.Tabs:
        if tab.Title == TAB_NAME:
            for panel in tab.Panels:
                if panel.Source and panel.Source.Title == DEV_PANEL_NAME:
                    panel.IsVisible = visible
                    panel.IsEnabled = visible
        if tab.Title == PYRVT_TAB_NAME:
            tab.IsVisible = visible


def on_idling(sender, args):
    try:
        hide_panels()
    except:
        pass
    finally:
        HOST_APP.uiapp.Idling -= EventHandler[IdlingEventArgs](on_idling)


HOST_APP.uiapp.Idling += EventHandler[IdlingEventArgs](on_idling)


# =============================================================================
# SECTION 2 — REBAR SPACING CALCULATOR
# =============================================================================

def find_file(filename, search_root):
    for root, dirs, files in os.walk(search_root):
        if filename in files:
            return op.join(root, filename)
    return None


_tab_root       = op.join(op.dirname(__file__), "CDY-ProTools.tab")
_xaml_path      = find_file("RebarSpacingCalculator.xaml", _tab_root)
_cdy_xaml_path  = find_file("CDYTools.xaml", _tab_root)

from Autodesk.Revit.UI.Selection import ObjectSnapTypes

class MeasureHandler(IExternalEventHandler):

    def __init__(self):
        self.spacing_box     = None
        self.cover_box       = None
        self.result_distance = None
        self.result_bars     = None
        self.result_rounded  = None
        self.console         = None
        self.last_result     = ""

    def Execute(self, uiapp):
        uidoc = uiapp.ActiveUIDocument
        if not uidoc:
            return
        try:
            spacing_mm = float(self.spacing_box.Text)
            if spacing_mm <= 0:
                raise ValueError("spacing must be > 0")
        except Exception as e:
            self.result_distance.Text = "Invalid spacing: {}".format(e)
            return
        try:
            cover_mm = float(self.cover_box.Text)
        except:
            cover_mm = 50.0
        try:
            p1 = uidoc.Selection.PickPoint(ObjectSnapTypes.Endpoints, "Pick first point")
            p2 = uidoc.Selection.PickPoint(ObjectSnapTypes.Endpoints, "Pick second point")
        except:
            self.result_distance.Text = "Cancelled"
            return
        dist_internal = p1.DistanceTo(p2)
        dist_mm       = UnitUtils.ConvertFromInternalUnits(dist_internal, UnitTypeId.Millimeters)
        net_mm        = dist_mm - (2 * cover_mm)
        bars          = net_mm / spacing_mm
        rounded_up    = int(math.ceil(bars)) + 1
        self.result_distance.Text = "Distance: {:.0f} mm  (net: {:.0f} mm)".format(dist_mm, net_mm)
        self.result_bars.Text     = "Bars: {:.2f}".format(bars)
        self.result_rounded.Text  = "Rounded Qty: {}".format(rounded_up)
        timestamp  = datetime.datetime.now().strftime("%H:%M:%S")
        result_str = "[{}] {:.0f}mm @ {}mm spacing -> {} bars".format(
            timestamp, dist_mm, int(spacing_mm), rounded_up)
        self.last_result = result_str
        if self.console is not None:
            existing = self.console.Text
            self.console.Text = result_str + ("\n" + existing if existing else "")

    def GetName(self):
        return "Spacing Measure Handler"


_measure_handler = MeasureHandler()
_measure_event   = ExternalEvent.Create(_measure_handler)


class RebarSpacingCalculator(forms.WPFPanel):
    panel_title  = "Rebar Spacing Calculator"
    panel_id     = "3110e336-f81c-4927-87da-4e0d30d4d64b"
    panel_source = _xaml_path

    def SetupDockablePane(self, data):
        data.FrameworkElement = self
        data.VisibleByDefault = False

    def __init__(self):
        super(RebarSpacingCalculator, self).__init__()
        _measure_handler.spacing_box     = self.spacingBox
        _measure_handler.cover_box       = self.coverBox
        _measure_handler.result_distance = self.distanceText
        _measure_handler.result_bars     = self.barsText
        _measure_handler.result_rounded  = self.roundedText
        _measure_handler.console         = self.consoleText

    def measureBtn_Click(self, sender, args):
        _measure_event.Raise()

    def clearBtn_Click(self, sender, args):
        self.consoleText.Text = ""
        _measure_handler.last_result = ""


try:
    if not forms.is_registered_dockable_panel(RebarSpacingCalculator):
        forms.register_dockable_panel(RebarSpacingCalculator)
        print("CDY: RebarSpacingCalculator registered OK.")
    else:
        print("CDY: RebarSpacingCalculator already registered, skipping.")
except Exception as ex:
    print("CDY: RebarSpacingCalculator REGISTRATION FAILED: {}".format(ex))


# =============================================================================
# SECTION 3 — CDY TOOLS PANEL
# =============================================================================

def _set_status(tb, message, error=False):
    tb.Text       = message
    tb.Foreground = Brushes.Crimson if error else Brushes.SeaGreen


# =============================================================================
# SELECTION FILTERS
# =============================================================================

_2D_CATS_RAW = [
    BuiltInCategory.OST_Lines,
    BuiltInCategory.OST_DetailComponents,
    BuiltInCategory.OST_TextNotes,
    BuiltInCategory.OST_Dimensions,
    BuiltInCategory.OST_Grids,
    BuiltInCategory.OST_Levels,
    BuiltInCategory.OST_ReferenceLines,
    BuiltInCategory.OST_FilledRegion,
]
_2D_CATS = set()
for _c in _2D_CATS_RAW:
    try:
        _2D_CATS.add(int(_c))
    except:
        pass

_3D_CATS_RAW = [
    BuiltInCategory.OST_StructuralColumns,
    BuiltInCategory.OST_StructuralFraming,
    BuiltInCategory.OST_Walls,
    BuiltInCategory.OST_Floors,
    BuiltInCategory.OST_StructuralFoundation,
    BuiltInCategory.OST_Roofs,
    BuiltInCategory.OST_Stairs,
    BuiltInCategory.OST_Ramps,
    BuiltInCategory.OST_Doors,
    BuiltInCategory.OST_Windows,
    BuiltInCategory.OST_GenericModel,
    BuiltInCategory.OST_Rebar,
    BuiltInCategory.OST_AreaRein,
    BuiltInCategory.OST_PathRein,
    BuiltInCategory.OST_Columns,
    BuiltInCategory.OST_Casework,
    BuiltInCategory.OST_Furniture,
    BuiltInCategory.OST_MechanicalEquipment,
]
_3D_CATS = set()
for _c in _3D_CATS_RAW:
    try:
        _3D_CATS.add(int(_c))
    except:
        pass


class Only2DFilter(ISelectionFilter):
    def AllowElement(self, el):
        try:
            cat = el.Category
            if cat is None:
                return False
            return int(cat.Id.IntegerValue) in _2D_CATS
        except:
            return False
    def AllowReference(self, ref, pt):
        return False


class Only3DFilter(ISelectionFilter):
    def AllowElement(self, el):
        try:
            cat = el.Category
            if cat is None:
                return False
            return int(cat.Id.IntegerValue) in _3D_CATS
        except:
            return False
    def AllowReference(self, ref, pt):
        return False


# =============================================================================
# EXTERNAL EVENT HANDLERS
# =============================================================================

# -- TAB 1: VIEW MANAGEMENT ---------------------------------------------------

class OpenHostSheetHandler(IExternalEventHandler):
    def __init__(self):
        self.status = None

    def Execute(self, uiapp):
        uidoc = uiapp.ActiveUIDocument
        doc   = uidoc.Document
        view  = doc.ActiveView
        try:
            sheet_id = view.get_Parameter(
                BuiltInParameter.VIEW_SHEET_VIEWPORT_INFO).AsElementId()
        except:
            sheet_id = ElementId.InvalidElementId

        host_sheet = None
        vps = FilteredElementCollector(doc).OfClass(DB.Viewport).ToElements()
        for vp in vps:
            if vp.ViewId == view.Id:
                host_sheet = doc.GetElement(vp.SheetId)
                break

        if host_sheet is None:
            _set_status(self.status, "Active view is not placed on a sheet.", error=True)
            return
        uidoc.ActiveView = host_sheet
        _set_status(self.status, "Opened sheet: {}".format(host_sheet.Name))

    def GetName(self):
        return "CDY Open Host Sheet"


class OpenSelectedViewOnSheetHandler(IExternalEventHandler):
    def __init__(self):
        self.status = None

    def Execute(self, uiapp):
        uidoc = uiapp.ActiveUIDocument
        doc   = uidoc.Document
        sel   = list(uidoc.Selection.GetElementIds())
        if not sel:
            _set_status(self.status, "Select a viewport on a sheet first.", error=True)
            return
        el = doc.GetElement(sel[0])
        if not isinstance(el, DB.Viewport):
            _set_status(self.status, "Selected element is not a viewport.", error=True)
            return
        view = doc.GetElement(el.ViewId)
        if view is None:
            _set_status(self.status, "Could not resolve view from viewport.", error=True)
            return
        uidoc.ActiveView = view
        _set_status(self.status, "Opened: {}".format(view.Name))

    def GetName(self):
        return "CDY Open Selected View On Sheet"


class OpenParentViewHandler(IExternalEventHandler):
    def __init__(self):
        self.status = None

    def Execute(self, uiapp):
        uidoc = uiapp.ActiveUIDocument
        doc   = uidoc.Document
        view  = doc.ActiveView
        try:
            parent_id = view.GetPrimaryViewId()
        except:
            parent_id = ElementId.InvalidElementId

        if parent_id == ElementId.InvalidElementId or parent_id is None:
            _set_status(self.status, "Active view is already a primary view — no action taken.")
            return
        parent = doc.GetElement(parent_id)
        if parent is None:
            _set_status(self.status, "Parent view could not be found.", error=True)
            return
        uidoc.ActiveView = parent
        _set_status(self.status, "Opened parent: {}".format(parent.Name))

    def GetName(self):
        return "CDY Open Parent View"


# -- TAB 2: MODELLING ---------------------------------------------------------

class Pick2DHandler(IExternalEventHandler):
    def __init__(self):
        self.status = None

    def Execute(self, uiapp):
        uidoc = uiapp.ActiveUIDocument
        try:
            els = uidoc.Selection.PickElementsByRectangle(
                Only2DFilter(), "Box-select 2D elements")
            ids = [e.Id for e in els]
            uidoc.Selection.SetElementIds(System_List_ElementId(ids))
            _set_status(self.status, "Selected {} 2D element(s).".format(len(ids)))
        except:
            _set_status(self.status, "Cancelled.")

    def GetName(self):
        return "CDY Pick 2D"


class Pick3DHandler(IExternalEventHandler):
    def __init__(self):
        self.status = None

    def Execute(self, uiapp):
        uidoc = uiapp.ActiveUIDocument
        try:
            els = uidoc.Selection.PickElementsByRectangle(
                Only3DFilter(), "Box-select 3D elements")
            ids = [e.Id for e in els]
            uidoc.Selection.SetElementIds(System_List_ElementId(ids))
            _set_status(self.status, "Selected {} 3D element(s).".format(len(ids)))
        except:
            _set_status(self.status, "Cancelled.")

    def GetName(self):
        return "CDY Pick 3D"


class PickGroupedElementsHandler(IExternalEventHandler):
    def __init__(self):
        self.status = None

    def Execute(self, uiapp):
        uidoc = uiapp.ActiveUIDocument
        doc   = uidoc.Document
        sel   = list(uidoc.Selection.GetElementIds())
        if not sel:
            _set_status(self.status, "Select one or more groups first.", error=True)
            return
        member_ids = []
        for eid in sel:
            el = doc.GetElement(eid)
            if isinstance(el, DB.Group):
                for mid in el.GetMemberIds():
                    member_ids.append(mid)
        if not member_ids:
            _set_status(self.status, "No group members found in selection.", error=True)
            return
        uidoc.Selection.SetElementIds(System_List_ElementId(member_ids))
        _set_status(self.status, "Selected {} group member(s).".format(len(member_ids)))

    def GetName(self):
        return "CDY Pick Grouped Elements"


class FlipGridBubblesHandler(IExternalEventHandler):
    def __init__(self):
        self.status = None

    def Execute(self, uiapp):
        uidoc = uiapp.ActiveUIDocument
        doc   = uidoc.Document
        view  = doc.ActiveView
        sel   = list(uidoc.Selection.GetElementIds())
        grids = [doc.GetElement(i) for i in sel
                 if isinstance(doc.GetElement(i), DB.Grid)]
        if not grids:
            _set_status(self.status, "Select grid lines first.", error=True)
            return
        flipped = 0
        with Transaction(doc, "CDY: Flip Grid Bubbles") as t:
            t.Start()
            for g in grids:
                try:
                    end0 = g.IsBubbleVisibleInView(DB.DatumEnds.End0, view)
                    end1 = g.IsBubbleVisibleInView(DB.DatumEnds.End1, view)
                    if end0:
                        g.HideBubbleInView(DB.DatumEnds.End0, view)
                        g.ShowBubbleInView(DB.DatumEnds.End1, view)
                    elif end1:
                        g.HideBubbleInView(DB.DatumEnds.End1, view)
                        g.ShowBubbleInView(DB.DatumEnds.End0, view)
                    else:
                        g.ShowBubbleInView(DB.DatumEnds.End0, view)
                    flipped += 1
                except:
                    pass
            t.Commit()
        _set_status(self.status, "Flipped bubbles on {} grid(s).".format(flipped))

    def GetName(self):
        return "CDY Flip Grid Bubbles"


class FlipLevelBubblesHandler(IExternalEventHandler):
    def __init__(self):
        self.status = None

    def Execute(self, uiapp):
        uidoc = uiapp.ActiveUIDocument
        doc   = uidoc.Document
        view  = doc.ActiveView
        sel   = list(uidoc.Selection.GetElementIds())
        levels = [doc.GetElement(i) for i in sel
                  if isinstance(doc.GetElement(i), DB.Level)]
        if not levels:
            _set_status(self.status, "Select level lines first.", error=True)
            return
        flipped = 0
        with Transaction(doc, "CDY: Flip Level Bubbles") as t:
            t.Start()
            for lv in levels:
                try:
                    end0 = lv.IsBubbleVisibleInView(DB.DatumEnds.End0, view)
                    end1 = lv.IsBubbleVisibleInView(DB.DatumEnds.End1, view)
                    if end0:
                        lv.HideBubbleInView(DB.DatumEnds.End0, view)
                        lv.ShowBubbleInView(DB.DatumEnds.End1, view)
                    elif end1:
                        lv.HideBubbleInView(DB.DatumEnds.End1, view)
                        lv.ShowBubbleInView(DB.DatumEnds.End0, view)
                    else:
                        lv.ShowBubbleInView(DB.DatumEnds.End0, view)
                    flipped += 1
                except:
                    pass
            t.Commit()
        _set_status(self.status, "Flipped bubbles on {} level(s).".format(flipped))

    def GetName(self):
        return "CDY Flip Level Bubbles"


# -- TAB 3: DIMENSIONING ------------------------------------------------------

class DimGridsHandler(IExternalEventHandler):
    def __init__(self):
        self.status = None

    def Execute(self, uiapp):
        uidoc = uiapp.ActiveUIDocument
        doc   = uidoc.Document
        view  = doc.ActiveView
        sel   = list(uidoc.Selection.GetElementIds())
        grids = [doc.GetElement(i) for i in sel
                 if isinstance(doc.GetElement(i), DB.Grid)]
        if len(grids) < 2:
            _set_status(self.status, "Select 2 or more grids first.", error=True)
            return

        ref_arr = ReferenceArray()
        lines   = []
        for g in grids:
            crv = g.GetCurvesInView(DB.DatumExtentType.ViewSpecific, view)
            if not crv:
                crv = g.GetCurvesInView(DB.DatumExtentType.Model, view)
            if crv:
                ref_arr.Append(Reference(g))
                lines.append(crv[0])

        if ref_arr.Size < 2:
            _set_status(self.status, "Could not resolve grid curves.", error=True)
            return

        offset_ft = UnitUtils.ConvertToInternalUnits(2000, UnitTypeId.Millimeters)
        l0        = lines[0]
        l_last    = lines[-1]

        # Direction the grids run (e.g. vertical grids run in Y)
        grid_dir  = (l0.GetEndPoint(1) - l0.GetEndPoint(0)).Normalize()

        # Perpendicular to the grid lines — this is the direction the spacing
        # between grids is measured, so the dim line must travel this way
        perp      = XYZ(-grid_dir.Y, grid_dir.X, 0)

        # Offset from first grid midpoint, perpendicular by 2000mm
        mid_first = l0.Evaluate(0.5, True)
        mid_last  = l_last.Evaluate(0.5, True)
        origin    = mid_first + perp * offset_ft

        # Span the dim line from first to last grid along the perp direction
        dim_line  = Line.CreateBound(origin, origin + (mid_last - mid_first))

        with Transaction(doc, "CDY: Dimension Grids") as t:
            t.Start()
            doc.Create.NewDimension(view, dim_line, ref_arr)
            t.Commit()
        _set_status(self.status, "Dimensioned {} grids.".format(len(grids)))

    def GetName(self):
        return "CDY Dimension Grids"


class DimLevelsHandler(IExternalEventHandler):
    def __init__(self):
        self.status = None

    def Execute(self, uiapp):
        uidoc = uiapp.ActiveUIDocument
        doc   = uidoc.Document
        view  = doc.ActiveView
        sel   = list(uidoc.Selection.GetElementIds())
        levels = [doc.GetElement(i) for i in sel
                  if isinstance(doc.GetElement(i), DB.Level)]
        if len(levels) < 2:
            _set_status(self.status, "Select 2 or more levels first.", error=True)
            return

        ref_arr = ReferenceArray()
        lines   = []
        for lv in levels:
            crv = lv.GetCurvesInView(DB.DatumExtentType.ViewSpecific, view)
            if not crv:
                crv = lv.GetCurvesInView(DB.DatumExtentType.Model, view)
            if crv:
                ref_arr.Append(Reference(lv))
                lines.append(crv[0])

        if ref_arr.Size < 2:
            _set_status(self.status, "Could not resolve level curves.", error=True)
            return

        offset_ft = UnitUtils.ConvertToInternalUnits(2000, UnitTypeId.Millimeters)
        l0        = lines[0]
        mid       = l0.Evaluate(0.5, True)
        dim_pt0   = XYZ(mid.X - offset_ft, levels[0].Elevation,  0)
        dim_pt1   = XYZ(mid.X - offset_ft, levels[-1].Elevation, 0)
        dim_line  = Line.CreateBound(dim_pt0, dim_pt1)

        with Transaction(doc, "CDY: Dimension Levels") as t:
            t.Start()
            doc.Create.NewDimension(view, dim_line, ref_arr)
            t.Commit()
        _set_status(self.status, "Dimensioned {} levels.".format(len(levels)))

    def GetName(self):
        return "CDY Dimension Levels"


# -- TAB 4: TAGGING -----------------------------------------------------------

TAGGABLE_CATS = {
    "Structural Columns": BuiltInCategory.OST_StructuralColumns,
    "Framing / Beams":    BuiltInCategory.OST_StructuralFraming,
    "Walls":              BuiltInCategory.OST_Walls,
    "Floors":             BuiltInCategory.OST_Floors,
    "Foundations":        BuiltInCategory.OST_StructuralFoundation,
    "Grids":              BuiltInCategory.OST_Grids,
    "Levels":             BuiltInCategory.OST_Levels,
    "Doors":              BuiltInCategory.OST_Doors,
    "Windows":            BuiltInCategory.OST_Windows,
    "Rooms":              BuiltInCategory.OST_Rooms,
}

TAG_CATS = {
    "Structural Columns": BuiltInCategory.OST_StructuralColumnTags,
    "Framing / Beams":    BuiltInCategory.OST_StructuralFramingTags,
    "Walls":              BuiltInCategory.OST_WallTags,
    "Floors":             BuiltInCategory.OST_FloorTags,
    "Foundations":        BuiltInCategory.OST_StructuralFoundationTags,
    "Grids":              BuiltInCategory.OST_GridHeads,
    "Levels":             BuiltInCategory.OST_LevelHeads,
    "Doors":              BuiltInCategory.OST_DoorTags,
    "Windows":            BuiltInCategory.OST_WindowTags,
    "Rooms":              BuiltInCategory.OST_RoomTags,
}


class SelectUntaggedHandler(IExternalEventHandler):
    def __init__(self):
        self.cat_combo = None
        self.status    = None

    def Execute(self, uiapp):
        uidoc    = uiapp.ActiveUIDocument
        doc      = uidoc.Document
        view     = doc.ActiveView
        cat_name = self.cat_combo.SelectedItem.Content if self.cat_combo.SelectedItem else None

        if not cat_name or cat_name not in TAGGABLE_CATS:
            _set_status(self.status, "Select a valid category.", error=True)
            return

        bic     = TAGGABLE_CATS[cat_name]
        tag_bic = TAG_CATS[cat_name]

        all_els = list(
            FilteredElementCollector(doc, view.Id)
            .OfCategory(bic)
            .WhereElementIsNotElementType()
        )
        existing_tags = list(
            FilteredElementCollector(doc, view.Id)
            .OfCategory(tag_bic)
            .WhereElementIsNotElementType()
        )
        tagged_ids = set()
        for tag in existing_tags:
            try:
                for ref in tag.GetTaggedReferences():
                    tagged_ids.add(ref.ElementId)
            except:
                pass

        untagged = [el for el in all_els if el.Id not in tagged_ids]
        if not untagged:
            _set_status(self.status, "All {} elements are already tagged.".format(cat_name))
            return

        uidoc.Selection.SetElementIds(
            System_List_ElementId([el.Id for el in untagged]))
        _set_status(self.status,
                    "Selected {} untagged {} element(s).".format(len(untagged), cat_name))

    def GetName(self):
        return "CDY Select Untagged"


# -- TAB 5: FILE NAVIGATION ---------------------------------------------------

class OpenDWGInAutoCADHandler(IExternalEventHandler):
    def __init__(self):
        self.status = None

    def Execute(self, uiapp):
        uidoc = uiapp.ActiveUIDocument
        doc   = uidoc.Document
        sel   = list(uidoc.Selection.GetElementIds())
        if not sel:
            _set_status(self.status, "Select a linked/imported DWG first.", error=True)
            return
        el   = doc.GetElement(sel[0])
        path = None
        try:
            link_type_id = el.GetTypeId()
            link_type    = doc.GetElement(link_type_id)
            ext_ref      = link_type.GetExternalFileReference()
            path         = DB.ModelPathUtils.ConvertModelPathToUserVisiblePath(
                               ext_ref.GetAbsolutePath())
        except:
            pass
        if not path or not op.exists(path):
            _set_status(self.status, "Could not resolve DWG path.", error=True)
            return
        try:
            os.startfile(path)
            _set_status(self.status, "Opened: {}".format(op.basename(path)))
        except Exception as e:
            _set_status(self.status, "Failed to open: {}".format(e), error=True)

    def GetName(self):
        return "CDY Open DWG in AutoCAD"


class ReloadDWGHandler(IExternalEventHandler):
    def __init__(self):
        self.status = None

    def Execute(self, uiapp):
        uidoc = uiapp.ActiveUIDocument
        doc   = uidoc.Document
        sel   = list(uidoc.Selection.GetElementIds())
        if not sel:
            _set_status(self.status, "Select a linked DWG first.", error=True)
            return
        el = doc.GetElement(sel[0])
        with Transaction(doc, "CDY: Reload DWG") as t:
            t.Start()
            try:
                link_type_id = el.GetTypeId()
                link_type    = doc.GetElement(link_type_id)
                link_type.Reload()
            except Exception as e:
                t.RollBack()
                _set_status(self.status, "Reload failed: {}".format(e), error=True)
                return
            t.Commit()
        _set_status(self.status, "DWG reloaded successfully.")

    def GetName(self):
        return "CDY Reload DWG"


# =============================================================================
# HELPERS — shared by DWG colour/hide handlers
# =============================================================================

def _get_import_instance(doc, sel):
    """Return the first ImportInstance found in the selection."""
    for eid in sel:
        el = doc.GetElement(eid)
        if isinstance(el, DB.ImportInstance):
            return el
    return None


def _get_override_target(doc, view):
    """
    Return (target_view_or_template, display_name).
    Respects view templates — consistent with Grey Scale buttons.
    """
    template_id = view.ViewTemplateId
    if template_id != DB.ElementId.InvalidElementId:
        target = doc.GetElement(template_id)
        return target, "template '{}'".format(target.Name)
    return view, "active view"


# =============================================================================
# GREYSCALE / REVERT HANDLERS
# =============================================================================

class GreyScaleDWGHandler(IExternalEventHandler):
    def __init__(self):
        self.status = None

    def Execute(self, uiapp):
        uidoc = uiapp.ActiveUIDocument
        doc   = uidoc.Document
        view  = doc.ActiveView
        sel   = list(uidoc.Selection.GetElementIds())

        if not sel:
            _set_status(self.status, "Select a linked/imported DWG first.", error=True)
            return

        import_inst = _get_import_instance(doc, sel)
        if import_inst is None:
            _set_status(self.status, "No DWG import/link found in selection.", error=True)
            return

        target, target_name = _get_override_target(doc, view)
        root_cat = import_inst.Category
        if not root_cat:
            _set_status(self.status, "Could not resolve DWG categories.", error=True)
            return

        with Transaction(doc, "CDY: Greyscale DWG") as t:
            t.Start()
            try:
                # Halftone must be applied to the root import category —
                # Revit ignores SetHalftone on DWG subcategories (layers)
                root_ovr = DB.OverrideGraphicSettings()
                root_ovr.SetHalftone(True)
                target.SetCategoryOverrides(root_cat.Id, root_ovr)

                # Black colour override applied per-layer as normal
                for layer_cat in root_cat.SubCategories:
                    ovr = DB.OverrideGraphicSettings()
                    ovr.SetProjectionLineColor(DB.Color(0, 0, 0))
                    target.SetCategoryOverrides(layer_cat.Id, ovr)
                t.Commit()
            except Exception as e:
                t.RollBack()
                _set_status(self.status, "Failed: {}".format(e), error=True)
                return

        _set_status(self.status, "Greyscale applied on {}.".format(target_name))

    def GetName(self):
        return "CDY Greyscale DWG"


class RevertGreyScaleDWGHandler(IExternalEventHandler):
    def __init__(self):
        self.status = None

    def Execute(self, uiapp):
        uidoc = uiapp.ActiveUIDocument
        doc   = uidoc.Document
        view  = doc.ActiveView
        sel   = list(uidoc.Selection.GetElementIds())

        if not sel:
            _set_status(self.status, "Select a linked/imported DWG first.", error=True)
            return

        import_inst = _get_import_instance(doc, sel)
        if import_inst is None:
            _set_status(self.status, "No DWG import/link found in selection.", error=True)
            return

        target, target_name = _get_override_target(doc, view)
        root_cat = import_inst.Category
        if not root_cat:
            _set_status(self.status, "Could not resolve DWG categories.", error=True)
            return

        with Transaction(doc, "CDY: Revert Greyscale DWG") as t:
            t.Start()
            try:
                # Clear root category (halftone lives here)
                target.SetCategoryOverrides(root_cat.Id, DB.OverrideGraphicSettings())
                # Clear all layer overrides
                for layer_cat in root_cat.SubCategories:
                    target.SetCategoryOverrides(layer_cat.Id, DB.OverrideGraphicSettings())
                t.Commit()
            except Exception as e:
                t.RollBack()
                _set_status(self.status, "Failed: {}".format(e), error=True)
                return

        _set_status(self.status, "Greyscale reverted on {}.".format(target_name))

    def GetName(self):
        return "CDY Revert Greyscale DWG"


# =============================================================================
# HIDE LAYER TOGGLE — pick loop handler
# =============================================================================

# Mutable flag — shared between the handler and the pick loop so a second
# button press (Raise → Execute) can signal the loop to stop.
_hide_layer_active = [False]


class HideLayerToggleHandler(IExternalEventHandler):
    """
    First click  → turns the button red, enters a PickObject loop.
                   Each picked DWG geometry resolves its layer and hides it
                   immediately in a micro-transaction.
    Second click → sets _hide_layer_active[0] = False, which causes the
                   loop to exit after its next ESC/pick attempt.
    ESC on canvas→ exits the loop directly.

    Respects view templates (via _get_override_target), consistent with
    the Grey Scale buttons.
    """

    def __init__(self):
        self.status     = None   # TextBlock for feedback
        self.toggle_btn = None   # Button ref — repainted to show active state

    # ---- UI helpers (dispatched onto the WPF thread) ------------------------

    def _ui_set_active(self):
        def _do():
            if self.toggle_btn:
                self.toggle_btn.Background = SolidColorBrush(
                    Media.Color.FromRgb(180, 40, 40))
                self.toggle_btn.Foreground = Brushes.White
                self.toggle_btn.Content    = "● Active — Press ESC to Finish"
            if self.status:
                _set_status(self.status, "Click DWG layers to hide. ESC to stop.")
        self.toggle_btn.Dispatcher.Invoke(Action(_do))

    def _ui_set_inactive(self, hidden_count):
        def _do():
            if self.toggle_btn:
                self.toggle_btn.ClearValue(Button.BackgroundProperty)
                self.toggle_btn.ClearValue(Button.ForegroundProperty)
                self.toggle_btn.Content = "Hide Layer (Toggle)"
            if self.status:
                if hidden_count:
                    _set_status(
                        self.status,
                        "Hide mode off — {} layer(s) hidden.".format(hidden_count))
                else:
                    _set_status(self.status, "Hide mode off.")
        self.toggle_btn.Dispatcher.Invoke(Action(_do))

    def _ui_update_count(self, layer_name, total):
        def _do():
            if self.status:
                _set_status(
                    self.status,
                    "Hidden '{}' ({} total). ESC to stop.".format(layer_name, total))
        self.toggle_btn.Dispatcher.Invoke(Action(_do))

    def _ui_error(self, msg):
        def _do():
            if self.status:
                _set_status(self.status, msg, error=True)
        self.toggle_btn.Dispatcher.Invoke(Action(_do))

    # ---- main execute -------------------------------------------------------

    def Execute(self, uiapp):
        # Second click while already active → signal loop to stop
        if _hide_layer_active[0]:
            _hide_layer_active[0] = False
            return

        uidoc = uiapp.ActiveUIDocument
        doc   = uidoc.Document

        _hide_layer_active[0] = True
        hidden_count          = 0
        hidden_names          = set()   # deduplicate within the session

        self._ui_set_active()

        while _hide_layer_active[0]:
            # ---- pick one point on DWG geometry -----------------------------
            try:
                ref = uidoc.Selection.PickObject(
                    ObjectType.PointOnElement,
                    "Click a DWG layer to hide it  (ESC to finish)"
                )
            except:
                break   # ESC or any interruption

            elem = doc.GetElement(ref.ElementId)

            # ---- resolve ImportInstance and GraphicsStyle id ----------------
            import_inst = None
            gs_id       = None

            if isinstance(elem, DB.ImportInstance):
                import_inst = elem
                try:
                    geom  = import_inst.GetGeometryObjectFromReference(ref)
                    gs_id = geom.GraphicsStyleId
                except:
                    pass
            else:
                # Walk up element hierarchy to find owning ImportInstance
                parent = elem
                while parent:
                    if isinstance(parent, DB.ImportInstance):
                        import_inst = parent
                        break
                    try:
                        host_param = parent.get_Parameter(BuiltInParameter.HOST_ID_PARAM)
                        parent = doc.GetElement(host_param.AsElementId()) if host_param else None
                    except:
                        parent = None
                if elem:
                    try:
                        gs_id = elem.GraphicsStyleId
                    except:
                        pass

            if not import_inst or not gs_id:
                continue

            gs = doc.GetElement(gs_id)
            if not gs:
                continue

            layer_name = gs.GraphicsStyleCategory.Name
            root_cat   = import_inst.Category
            if not root_cat:
                continue

            # Skip silently if already hidden this session
            if layer_name in hidden_names:
                continue

            try:
                layer_cat = root_cat.SubCategories.get_Item(layer_name)
            except:
                layer_cat = None

            if not layer_cat:
                continue

            # ---- resolve target (view or template) --------------------------
            view   = doc.ActiveView
            target, _target_name = _get_override_target(doc, view)

            # ---- hide in a micro-transaction --------------------------------
            with Transaction(doc, "CDY: Hide DWG Layer '{}'".format(layer_name)) as t:
                t.Start()
                try:
                    target.SetCategoryHidden(layer_cat.Id, True)
                    t.Commit()
                    hidden_names.add(layer_name)
                    hidden_count += 1
                    self._ui_update_count(layer_name, hidden_count)
                except Exception as e:
                    t.RollBack()
                    self._ui_error("Could not hide '{}': {}".format(layer_name, e))

        # ---- loop exited ----------------------------------------------------
        _hide_layer_active[0] = False
        self._ui_set_inactive(hidden_count)

    def GetName(self):
        return "CDY Hide Layer Toggle"


# =============================================================================
# REMAINING FILE NAV HANDLERS
# =============================================================================

class OpenBIM360Handler(IExternalEventHandler):
    def __init__(self):
        self.status = None

    def Execute(self, uiapp):
        doc  = uiapp.ActiveUIDocument.Document
        path = doc.PathName
        if not path:
            _set_status(self.status, "File has not been saved.", error=True)
            return
        if "BIM 360" in path or "ACC" in path or path.startswith("BIM"):
            import webbrowser
            webbrowser.open("https://acc.autodesk.com")
            _set_status(self.status, "Opened ACC in browser.")
        else:
            _set_status(self.status,
                        "Model does not appear to be hosted on BIM360/ACC.", error=True)

    def GetName(self):
        return "CDY Open BIM360"


class OpenCentralLocationHandler(IExternalEventHandler):
    def __init__(self):
        self.status = None

    def Execute(self, uiapp):
        doc = uiapp.ActiveUIDocument.Document
        try:
            central_path = DB.ModelPathUtils.ConvertModelPathToUserVisiblePath(
                doc.GetWorksharingCentralModelPath())
        except:
            central_path = None

        if not central_path:
            _set_status(self.status, "No central model path found.", error=True)
            return

        folder = op.dirname(central_path)
        if op.exists(folder):
            subprocess.Popen('explorer "{}"'.format(folder))
            _set_status(self.status, "Opened: {}".format(folder))
        else:
            _set_status(self.status, "Folder not found: {}".format(folder), error=True)

    def GetName(self):
        return "CDY Open Central Location"


class OpenLocalLocationHandler(IExternalEventHandler):
    def __init__(self):
        self.status = None

    def Execute(self, uiapp):
        doc  = uiapp.ActiveUIDocument.Document
        path = doc.PathName
        if not path:
            _set_status(self.status, "File has not been saved.", error=True)
            return
        folder = op.dirname(path)
        if op.exists(folder):
            subprocess.Popen('explorer "{}"'.format(folder))
            _set_status(self.status, "Opened: {}".format(folder))
        else:
            _set_status(self.status, "Folder not found: {}".format(folder), error=True)

    def GetName(self):
        return "CDY Open Local Location"


# =============================================================================
# INSTANTIATE ALL HANDLERS & EVENTS
# =============================================================================

from System.Collections.Generic import List as DotNetList

def System_List_ElementId(ids):
    lst = DotNetList[ElementId]()
    for i in ids:
        lst.Add(i)
    return lst

# Tab 1
_open_sheet_h       = OpenHostSheetHandler()
_open_sheet_e       = ExternalEvent.Create(_open_sheet_h)
_open_view_sheet_h  = OpenSelectedViewOnSheetHandler()
_open_view_sheet_e  = ExternalEvent.Create(_open_view_sheet_h)
_open_parent_h      = OpenParentViewHandler()
_open_parent_e      = ExternalEvent.Create(_open_parent_h)

# Tab 2
_pick2d_h           = Pick2DHandler()
_pick2d_e           = ExternalEvent.Create(_pick2d_h)
_pick3d_h           = Pick3DHandler()
_pick3d_e           = ExternalEvent.Create(_pick3d_h)
_pick_group_h       = PickGroupedElementsHandler()
_pick_group_e       = ExternalEvent.Create(_pick_group_h)
_flip_grid_h        = FlipGridBubblesHandler()
_flip_grid_e        = ExternalEvent.Create(_flip_grid_h)
_flip_level_h       = FlipLevelBubblesHandler()
_flip_level_e       = ExternalEvent.Create(_flip_level_h)

# Tab 3
_dim_grids_h        = DimGridsHandler()
_dim_grids_e        = ExternalEvent.Create(_dim_grids_h)
_dim_levels_h       = DimLevelsHandler()
_dim_levels_e       = ExternalEvent.Create(_dim_levels_h)

# Tab 4
_sel_untagged_h     = SelectUntaggedHandler()
_sel_untagged_e     = ExternalEvent.Create(_sel_untagged_h)

# Tab 5
_open_dwg_h         = OpenDWGInAutoCADHandler()
_open_dwg_e         = ExternalEvent.Create(_open_dwg_h)
_reload_dwg_h       = ReloadDWGHandler()
_reload_dwg_e       = ExternalEvent.Create(_reload_dwg_h)
_greyscale_dwg_h    = GreyScaleDWGHandler()
_greyscale_dwg_e    = ExternalEvent.Create(_greyscale_dwg_h)
_revert_grey_dwg_h  = RevertGreyScaleDWGHandler()
_revert_grey_dwg_e  = ExternalEvent.Create(_revert_grey_dwg_h)
_hide_layer_h       = HideLayerToggleHandler()
_hide_layer_e       = ExternalEvent.Create(_hide_layer_h)
_open_bim360_h      = OpenBIM360Handler()
_open_bim360_e      = ExternalEvent.Create(_open_bim360_h)
_open_central_h     = OpenCentralLocationHandler()
_open_central_e     = ExternalEvent.Create(_open_central_h)
_open_local_h       = OpenLocalLocationHandler()
_open_local_e       = ExternalEvent.Create(_open_local_h)


# =============================================================================
# DOCKABLE PANEL
# =============================================================================

class CDYToolsPanel(forms.WPFPanel):
    panel_title  = "CDY Tools"
    panel_id     = "c4e8f127-9d3b-4a71-b6e2-1f0d7c5a8b94"
    panel_source = _cdy_xaml_path

    def SetupDockablePane(self, data):
        data.FrameworkElement = self
        data.VisibleByDefault = False

    def __init__(self):
        super(CDYToolsPanel, self).__init__()
        try:
            self._build_ui()
        except Exception as ex:
            print("CDY: CDYToolsPanel INIT ERROR: {}".format(ex))

    # -------------------------------------------------------------------------
    # WIDGET HELPERS
    # -------------------------------------------------------------------------

    def _label(self, text, bold=False, small=False):
        tb              = TextBlock()
        tb.Text         = text
        tb.TextWrapping = TextWrapping.Wrap
        tb.Margin       = Thickness(0, 4, 0, 2)
        if bold:
            tb.FontWeight = FontWeights.Bold
        if small:
            tb.FontSize   = 10
            tb.Foreground = Brushes.Gray
        return tb

    def _button(self, text, handler_fn):
        btn         = Button()
        btn.Content = text
        btn.Margin  = Thickness(0, 4, 0, 2)
        btn.Padding = Thickness(6, 4, 6, 4)
        btn.HorizontalAlignment = System_HAlign.Stretch
        btn.Click  += handler_fn
        return btn

    def _status(self):
        tb              = TextBlock()
        tb.Text         = "---"
        tb.Margin       = Thickness(0, 6, 0, 4)
        tb.TextWrapping = TextWrapping.Wrap
        tb.Foreground   = Brushes.Gray
        tb.FontSize     = 11
        return tb

    def _sep(self):
        s        = Separator()
        s.Margin = Thickness(0, 6, 0, 6)
        return s

    def _make_tab(self, header):
        tab            = TabItem()
        tab.Header     = header
        scroll         = ScrollViewer()
        scroll.VerticalScrollBarVisibility   = ScrollBarVisibility.Auto
        scroll.HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled
        # Semi-transparent white so the XAML watermark DrawingBrush on
        # rootPanel bleeds through the tab content area
        scroll.Background = SolidColorBrush(Media.Color.FromArgb(150, 255, 255, 255))
        panel          = StackPanel()
        panel.Margin   = Thickness(8)
        scroll.Content = panel
        tab.Content    = scroll
        return tab, panel

    def _section(self, panel, title):
        panel.Children.Add(self._label(title, bold=True))
        panel.Children.Add(self._sep())

    # -------------------------------------------------------------------------
    # ROOT BUILD
    # -------------------------------------------------------------------------

    def _build_ui(self):
        tabs = TabControl()
        tabs.Items.Add(self._build_view_mgmt_tab())
        tabs.Items.Add(self._build_modelling_tab())
        tabs.Items.Add(self._build_dimensioning_tab())
        tabs.Items.Add(self._build_tagging_tab())
        tabs.Items.Add(self._build_file_nav_tab())

        # ── Watermark ────────────────────────────────────────────────────────
        # Build the DrawingBrush entirely in Python so it is guaranteed to
        # render regardless of whether the XAML rootPanel resolves correctly.
        try:
            from System.Windows.Media import (
                DrawingBrush, DrawingGroup, GeometryDrawing,
                TileMode, BrushMappingMode
            )
            from System.Windows.Media.Geometry import Parse as ParseGeometry
            from System.Windows import Rect

            LOGO_PATH = (
                "M20.0244 6.68262V13.5674H19.4531C19.0234 11.7705 18.2227 10.3936 "
                "17.0508 9.43652C15.8789 8.47949 14.5508 8.00098 13.0664 8.00098C"
                "11.8262 8.00098 10.6885 8.35742 9.65332 9.07031C8.61816 9.7832 "
                "7.86133 10.7158 7.38281 11.8682C6.76758 13.3428 6.45996 14.9834 "
                "6.45996 16.79C6.45996 18.5674 6.68457 20.1885 7.13379 21.6533C"
                "7.58301 23.1084 8.28613 24.2119 9.24316 24.9639C10.2002 25.7061 "
                "11.4404 26.0771 12.9639 26.0771C14.2139 26.0771 15.3564 25.8037 "
                "16.3916 25.2568C17.4365 24.71 18.5352 23.7676 19.6875 22.4297V"
                "24.1436C18.5742 25.3057 17.4121 26.1504 16.2012 26.6777C15 27.1953 "
                "13.5938 27.4541 11.9824 27.4541C9.86328 27.4541 7.97852 27.0293 "
                "6.32812 26.1797C4.6875 25.3301 3.41797 24.1094 2.51953 22.5176C"
                "1.63086 20.9258 1.18652 19.2314 1.18652 17.4346C1.18652 15.54 "
                "1.67969 13.7432 2.66602 12.0439C3.66211 10.3447 5 9.02637 6.67969 "
                "8.08887C8.36914 7.15137 10.1611 6.68262 12.0557 6.68262C13.4521 "
                "6.68262 14.9268 6.98535 16.4795 7.59082C17.3779 7.94238 17.9492 "
                "8.11816 18.1934 8.11816C18.5059 8.11816 18.7744 8.00586 18.999 "
                "7.78125C19.2334 7.54688 19.3848 7.18066 19.4531 6.68262H20.0244Z"
                "M33.2484 17.9473V23.5137C33.2484 24.5879 33.3119 25.2666 33.4389 "
                "25.5498C33.5756 25.8232 33.81 26.043 34.142 26.209C34.474 26.375 "
                "35.0941 26.458 36.0023 26.458V27H25.8363V26.458C26.7543 26.458 "
                "27.3744 26.375 27.6967 26.209C28.0287 26.0332 28.2582 25.8086 "
                "28.3852 25.5352C28.5219 25.2617 28.5902 24.5879 28.5902 23.5137V"
                "10.623C28.5902 9.54883 28.5219 8.875 28.3852 8.60156C28.2582 "
                "8.31836 28.0287 8.09375 27.6967 7.92773C27.3646 7.76172 26.7445 "
                "7.67871 25.8363 7.67871V7.13672H35.0648C37.4672 7.13672 39.225 "
                "7.30273 40.3383 7.63477C41.4516 7.9668 42.3598 8.58203 43.0629 "
                "9.48047C43.766 10.3691 44.1176 11.4141 44.1176 12.6152C44.1176 "
                "14.0801 43.5902 15.291 42.5355 16.248C41.8617 16.8535 40.9193 "
                "17.3076 39.7084 17.6104L44.4838 24.334C45.1088 25.2031 45.5531 "
                "25.7451 45.8168 25.96C46.2172 26.2627 46.6811 26.4287 47.2084 "
                "26.458V27H40.9535L34.5521 17.9473H33.2484ZM33.2484 8.20605V"
                "16.9072H34.0834C35.4408 16.9072 36.4564 16.7852 37.1303 16.541C"
                "37.8041 16.2871 38.3314 15.8379 38.7123 15.1934C39.1029 14.5391 "
                "39.2982 13.6895 39.2982 12.6445C39.2982 11.1309 38.9418 10.0127 "
                "38.2289 9.29004C37.5258 8.56738 36.3881 8.20605 34.8158 8.20605H"
                "33.2484ZM63.0398 21.3457H56.0232L55.1883 23.2793C54.9148 23.9238 "
                "54.7781 24.4561 54.7781 24.876C54.7781 25.4326 55.0027 25.8428 "
                "55.452 26.1064C55.7156 26.2627 56.365 26.3799 57.4002 26.458V27H"
                "50.7938V26.458C51.5066 26.3506 52.0926 26.0576 52.5516 25.5791C"
                "53.0105 25.0908 53.577 24.0898 54.2508 22.5762L61.3553 6.72656H"
                "61.6336L68.7967 23.0156C69.4803 24.5586 70.0418 25.5303 70.4813 "
                "25.9307C70.8133 26.2334 71.282 26.4092 71.8875 26.458V27H62.2781V"
                "26.458H62.6736C63.4451 26.458 63.9871 26.3506 64.2996 26.1357C"
                "64.5145 25.9795 64.6219 25.7549 64.6219 25.4619C64.6219 25.2861 "
                "64.5926 25.1055 64.534 24.9199C64.5145 24.832 64.368 24.4658 "
                "64.0945 23.8213L63.0398 21.3457ZM62.5418 20.2617L59.5828 13.4209L"
                "56.5359 20.2617H62.5418ZM76.2346 27V26.458H76.8938C77.4699 26.458 "
                "77.9094 26.3701 78.2121 26.1943C78.5246 26.0088 78.7541 25.7598 "
                "78.9006 25.4473C78.9885 25.2422 79.0324 24.627 79.0324 23.6016V"
                "10.5352C79.0324 9.51953 78.9787 8.88477 78.8713 8.63086C78.7639 "
                "8.37695 78.5441 8.15723 78.2121 7.97168C77.8898 7.77637 77.4504 "
                "7.67871 76.8938 7.67871H76.2346V7.13672H85.1262C87.4992 7.13672 "
                "89.4084 7.45898 90.8537 8.10352C92.6213 8.89453 93.9592 10.0908 "
                "94.8674 11.6924C95.7854 13.2939 96.2443 15.1055 96.2443 17.127C"
                "96.2443 18.5234 96.0197 19.8125 95.5705 20.9941C95.1213 22.166 "
                "94.5402 23.1377 93.8273 23.9092C93.1145 24.6709 92.2893 25.2861 "
                "91.3518 25.7549C90.424 26.2139 89.2863 26.5703 87.9387 26.8242C"
                "87.343 26.9414 86.4055 27 85.1262 27H76.2346ZM83.8078 8.26465V"
                "23.7627C83.8078 24.583 83.8469 25.0859 83.925 25.2715C84.0031 "
                "25.457 84.135 25.5986 84.3205 25.6963C84.5842 25.8428 84.965 "
                "25.916 85.4631 25.916C87.0939 25.916 88.3391 25.3594 89.1984 "
                "24.2461C90.3703 22.7422 90.9563 20.4082 90.9563 17.2441C90.9563 "
                "14.6953 90.5559 12.6592 89.7551 11.1357C89.1203 9.94434 88.3049 "
                "9.13379 87.3088 8.7041C86.6057 8.40137 85.4387 8.25488 83.8078 "
                "8.26465ZM101.514 27V26.458H102.173C102.75 26.458 103.189 26.3701 "
                "103.492 26.1943C103.804 26.0088 104.034 25.7598 104.18 25.4473C"
                "104.268 25.2422 104.312 24.627 104.312 23.6016V10.5352C104.312 "
                "9.51953 104.258 8.88477 104.151 8.63086C104.044 8.37695 103.824 "
                "8.15723 103.492 7.97168C103.17 7.77637 102.73 7.67871 102.173 "
                "7.67871H101.514V7.13672H110.406C112.779 7.13672 114.688 7.45898 "
                "116.133 8.10352C117.901 8.89453 119.239 10.0908 120.147 11.6924C"
                "121.065 13.2939 121.524 15.1055 121.524 17.127C121.524 18.5234 "
                "121.299 19.8125 120.85 20.9941C120.401 22.166 119.82 23.1377 "
                "119.107 23.9092C118.394 24.6709 117.569 25.2861 116.631 25.7549C"
                "115.704 26.2139 114.566 26.5703 113.218 26.8242C112.623 26.9414 "
                "111.685 27 110.406 27H101.514ZM109.088 8.26465V23.7627C109.088 "
                "24.583 109.127 25.0859 109.205 25.2715C109.283 25.457 109.415 "
                "25.5986 109.6 25.6963C109.864 25.8428 110.245 25.916 110.743 "
                "25.916C112.374 25.916 113.619 25.3594 114.478 24.2461C115.65 "
                "22.7422 116.236 20.4082 116.236 17.2441C116.236 14.6953 115.836 "
                "12.6592 115.035 11.1357C114.4 9.94434 113.585 9.13379 112.588 "
                "8.7041C111.885 8.40137 110.718 8.25488 109.088 8.26465Z"
                "M147.727 7.13672V7.67871C147.072 7.7666 146.569 7.95703 146.218 "
                "8.25C145.729 8.66016 144.958 9.77832 143.903 11.6045L139.597 "
                "18.7969V23.6016C139.597 24.627 139.65 25.2666 139.758 25.5205C"
                "139.865 25.7646 140.075 25.9844 140.388 26.1797C140.71 26.3652 "
                "141.135 26.458 141.662 26.458H142.775V27H131.628V26.458H132.668C"
                "133.254 26.458 133.718 26.3555 134.06 26.1504C134.313 26.0137 "
                "134.514 25.7793 134.66 25.4473C134.768 25.2129 134.821 24.5977 "
                "134.821 23.6016V19.6172L130.148 11.1064C129.221 9.42676 128.566 "
                "8.44043 128.186 8.14746C127.805 7.84473 127.297 7.68848 126.662 "
                "7.67871V7.13672H136.184V7.67871H135.759C135.183 7.67871 134.777 "
                "7.76172 134.543 7.92773C134.318 8.09375 134.206 8.26953 134.206 "
                "8.45508C134.206 8.80664 134.597 9.69043 135.378 11.1064L138.967 "
                "17.6836L142.541 11.6924C143.43 10.2275 143.874 9.25586 143.874 "
                "8.77734C143.874 8.51367 143.747 8.29395 143.493 8.11816C143.161 "
                "7.87402 142.551 7.72754 141.662 7.67871V7.13672H147.727Z"
                "M165.77 6.68262L165.931 13.3037H165.33C165.047 11.6436 164.349 "
                "10.3105 163.236 9.30469C162.132 8.28906 160.936 7.78125 159.647 "
                "7.78125C158.651 7.78125 157.86 8.0498 157.274 8.58691C156.698 "
                "9.11426 156.41 9.72461 156.41 10.418C156.41 10.8574 156.512 "
                "11.248 156.717 11.5898C157 12.0488 157.454 12.5029 158.079 "
                "12.9521C158.538 13.2744 159.598 13.8457 161.258 14.666C163.582 "
                "15.8086 165.15 16.8877 165.96 17.9033C166.761 18.9189 167.162 "
                "20.0811 167.162 21.3896C167.162 23.0498 166.512 24.4805 165.213 "
                "25.6816C163.924 26.873 162.284 27.4688 160.291 27.4688C159.666 "
                "27.4688 159.076 27.4053 158.519 27.2783C157.962 27.1514 157.264 "
                "26.9121 156.424 26.5605C155.955 26.3652 155.57 26.2676 155.267 "
                "26.2676C155.013 26.2676 154.745 26.3652 154.461 26.5605C154.178 "
                "26.7559 153.949 27.0537 153.773 27.4541H153.231V19.9541H153.773C"
                "154.203 22.0635 155.028 23.6748 156.248 24.7881C157.479 25.8916 "
                "158.802 26.4434 160.218 26.4434C161.312 26.4434 162.181 26.1455 "
                "162.826 25.5498C163.48 24.9541 163.807 24.2607 163.807 23.4697C"
                "163.807 23.001 163.68 22.5469 163.426 22.1074C163.182 21.668 "
                "162.806 21.2529 162.298 20.8623C161.79 20.4619 160.892 19.9443 "
                "159.603 19.3096C157.796 18.4209 156.497 17.6641 155.706 17.0391C"
                "154.915 16.4141 154.305 15.7158 153.875 14.9443C153.455 14.1729 "
                "153.246 13.3232 153.246 12.3955C153.246 10.8135 153.827 9.46582 "
                "154.989 8.35254C156.151 7.23926 157.616 6.68262 159.383 6.68262C"
                "160.028 6.68262 160.653 6.76074 161.258 6.91699C161.717 7.03418 "
                "162.274 7.25391 162.928 7.57617C163.592 7.88867 164.056 8.04492 "
                "164.32 8.04492C164.574 8.04492 164.774 7.9668 164.92 7.81055C"
                "165.067 7.6543 165.204 7.27832 165.33 6.68262H165.77Z"
            )

            geom    = ParseGeometry(LOGO_PATH)
            drawing = GeometryDrawing()
            drawing.Brush    = SolidColorBrush(Media.Color.FromArgb(255, 0, 0, 0))
            drawing.Geometry = geom

            grp         = DrawingGroup()
            grp.Opacity = 0.06   # very subtle — increase to taste
            grp.Children.Add(drawing)

            brush                   = DrawingBrush()
            brush.Drawing           = grp
            brush.Stretch           = Media.Stretch.Uniform
            brush.TileMode          = TileMode.None
            brush.AlignmentX        = Media.AlignmentX.Center
            brush.AlignmentY        = Media.AlignmentY.Center
            brush.ViewportUnits     = BrushMappingMode.RelativeToBoundingBox
            brush.Viewport          = Rect(0.05, 0.3, 0.9, 0.4)

            tabs.Background = brush

        except Exception as ex:
            print("CDY: Watermark failed to render: {}".format(ex))
        # ── end watermark ────────────────────────────────────────────────────

        if hasattr(self, 'rootPanel') and self.rootPanel is not None:
            self.rootPanel.Children.Add(tabs)
        else:
            self.Content = tabs

    # -------------------------------------------------------------------------
    # TAB 1: VIEW MANAGEMENT
    # -------------------------------------------------------------------------

    def _build_view_mgmt_tab(self):
        tab, p = self._make_tab("Views")

        self._section(p, "View Navigation")
        p.Children.Add(self._label(
            "Navigate quickly between views, sheets and parent/dependent relationships.",
            small=True))
        p.Children.Add(self._sep())

        p.Children.Add(self._button("Open Host Sheet", self._on_open_sheet))
        p.Children.Add(self._label(
            "Opens the sheet that the active view is placed on.", small=True))

        p.Children.Add(self._button("Open View Selected on Sheet", self._on_open_view_sheet))
        p.Children.Add(self._label(
            "Select a viewport on a sheet, then click to jump to that view.", small=True))

        p.Children.Add(self._button("Open Parent / Primary View", self._on_open_parent))
        p.Children.Add(self._label(
            "Opens the primary view if the active view is a dependent. "
            "Shows a message if already primary.", small=True))

        self._vm_status = self._status()
        p.Children.Add(self._vm_status)

        _open_sheet_h.status      = self._vm_status
        _open_view_sheet_h.status = self._vm_status
        _open_parent_h.status     = self._vm_status
        return tab

    def _on_open_sheet(self, s, a):       _open_sheet_e.Raise()
    def _on_open_view_sheet(self, s, a):  _open_view_sheet_e.Raise()
    def _on_open_parent(self, s, a):      _open_parent_e.Raise()

    # -------------------------------------------------------------------------
    # TAB 2: MODELLING
    # -------------------------------------------------------------------------

    def _build_modelling_tab(self):
        tab, p = self._make_tab("Modelling")

        self._section(p, "Selection Filters")
        p.Children.Add(self._label(
            "Box-select elements filtered to only 2D or 3D categories.", small=True))
        p.Children.Add(self._button("Pick 2D Elements",      self._on_pick2d))
        p.Children.Add(self._button("Pick 3D Elements",      self._on_pick3d))
        p.Children.Add(self._button("Pick Grouped Elements", self._on_pick_group))
        p.Children.Add(self._label(
            "For grouped elements: select groups first, then click.", small=True))

        p.Children.Add(self._sep())
        self._section(p, "Datum Bubbles")
        p.Children.Add(self._label(
            "Select grids or levels, then flip their bubble end in the active view.",
            small=True))
        p.Children.Add(self._button("Flip Grid Bubbles",  self._on_flip_grid))
        p.Children.Add(self._button("Flip Level Bubbles", self._on_flip_level))

        self._mod_status = self._status()
        p.Children.Add(self._mod_status)

        _pick2d_h.status      = self._mod_status
        _pick3d_h.status      = self._mod_status
        _pick_group_h.status  = self._mod_status
        _flip_grid_h.status   = self._mod_status
        _flip_level_h.status  = self._mod_status
        return tab

    def _on_pick2d(self, s, a):        _pick2d_e.Raise()
    def _on_pick3d(self, s, a):        _pick3d_e.Raise()
    def _on_pick_group(self, s, a):    _pick_group_e.Raise()
    def _on_flip_grid(self, s, a):     _flip_grid_e.Raise()
    def _on_flip_level(self, s, a):    _flip_level_e.Raise()

    # -------------------------------------------------------------------------
    # TAB 3: DIMENSIONING
    # -------------------------------------------------------------------------

    def _build_dimensioning_tab(self):
        tab, p = self._make_tab("Dimensions")

        self._section(p, "Auto Dimension")
        p.Children.Add(self._label(
            "Select 2 or more grids or levels, then click. "
            "Dimensions are placed on the active view.", small=True))

        p.Children.Add(self._button("Dimension Selected Gridlines", self._on_dim_grids))
        p.Children.Add(self._label(
            "Places a linear dimension string across all selected grids.", small=True))

        p.Children.Add(self._button("Dimension Selected Levels", self._on_dim_levels))
        p.Children.Add(self._label(
            "Places a vertical dimension string across all selected levels.", small=True))

        self._dim_status = self._status()
        p.Children.Add(self._dim_status)

        _dim_grids_h.status  = self._dim_status
        _dim_levels_h.status = self._dim_status
        return tab

    def _on_dim_grids(self, s, a):   _dim_grids_e.Raise()
    def _on_dim_levels(self, s, a):  _dim_levels_e.Raise()

    # -------------------------------------------------------------------------
    # TAB 4: TAGGING
    # -------------------------------------------------------------------------

    def _build_tagging_tab(self):
        tab, p = self._make_tab("Tagging")

        self._section(p, "Select Untagged Elements")
        p.Children.Add(self._label(
            "Selects all untagged elements of the chosen category in the active view. "
            "Use with Tag All to finish tagging in one step.", small=True))
        p.Children.Add(self._sep())

        p.Children.Add(self._label("Category:"))
        self._tag_cat_combo = ComboBox()
        self._tag_cat_combo.Margin = Thickness(0, 0, 0, 4)
        for name in TAGGABLE_CATS.keys():
            item         = ComboBoxItem()
            item.Content = name
            self._tag_cat_combo.Items.Add(item)
        self._tag_cat_combo.SelectedIndex = 0
        p.Children.Add(self._tag_cat_combo)

        p.Children.Add(self._button("Select Untagged in Active View", self._on_sel_untagged))

        self._tag_status = self._status()
        p.Children.Add(self._tag_status)

        _sel_untagged_h.cat_combo = self._tag_cat_combo
        _sel_untagged_h.status    = self._tag_status
        return tab

    def _on_sel_untagged(self, s, a):  _sel_untagged_e.Raise()

    # -------------------------------------------------------------------------
    # TAB 5: FILE NAVIGATION
    # -------------------------------------------------------------------------

    def _build_file_nav_tab(self):
        tab, p = self._make_tab("Files")

        self._section(p, "DWG Links")
        p.Children.Add(self._label(
            "Select a linked DWG in the canvas first.", small=True))

        p.Children.Add(self._button("Open Selected DWG in AutoCAD", self._on_open_dwg))

        p.Children.Add(self._button("Reload Selected DWG", self._on_reload_dwg))

        p.Children.Add(self._label(
            "Overrides all DWG layers to black with halftone in the active view or its view template.", small=True))
        p.Children.Add(self._button("Grey Scale Selected DWG", self._on_greyscale_dwg))

        p.Children.Add(self._button("Revert Grey Scale", self._on_revert_grey_dwg))
        p.Children.Add(self._label(
            "Removes all colour overrides from every layer of the selected DWG, "
            "restoring Revit defaults.", small=True))

        # Hide Layer toggle — store button ref so handler can repaint it
        self._hide_layer_btn = self._button(
            "Hide Layer (Toggle)", self._on_hide_layer_toggle)
        p.Children.Add(self._hide_layer_btn)
        p.Children.Add(self._label(
            "Toggle on (button turns red), then click any DWG geometry to hide "
            "that layer instantly. Click the button again or press ESC to stop. "
            "Respects view templates.", small=True))

        p.Children.Add(self._sep())
        self._section(p, "Project Locations")

        p.Children.Add(self._button("Open BIM360 / ACC", self._on_open_bim360))
        p.Children.Add(self._label(
            "Opens ACC in your default browser (BIM360-hosted models only).", small=True))

        p.Children.Add(self._button("Open Central Model Location", self._on_open_central))
        p.Children.Add(self._label(
            "Opens the folder containing the central model in Explorer.", small=True))

        p.Children.Add(self._button("Open Local File Location", self._on_open_local))
        p.Children.Add(self._label(
            "Opens the folder containing the currently open local file.", small=True))

        self._file_status = self._status()
        p.Children.Add(self._file_status)

        # Wire status TextBlocks and the toggle button reference to handlers
        _open_dwg_h.status        = self._file_status
        _reload_dwg_h.status      = self._file_status
        _greyscale_dwg_h.status   = self._file_status
        _revert_grey_dwg_h.status = self._file_status
        _hide_layer_h.status      = self._file_status
        _hide_layer_h.toggle_btn  = self._hide_layer_btn
        _open_bim360_h.status     = self._file_status
        _open_central_h.status    = self._file_status
        _open_local_h.status      = self._file_status
        return tab

    def _on_open_dwg(self, s, a):            _open_dwg_e.Raise()
    def _on_reload_dwg(self, s, a):          _reload_dwg_e.Raise()
    def _on_greyscale_dwg(self, s, a):       _greyscale_dwg_e.Raise()
    def _on_revert_grey_dwg(self, s, a):     _revert_grey_dwg_e.Raise()
    def _on_hide_layer_toggle(self, s, a):   _hide_layer_e.Raise()
    def _on_open_bim360(self, s, a):         _open_bim360_e.Raise()
    def _on_open_central(self, s, a):        _open_central_e.Raise()
    def _on_open_local(self, s, a):          _open_local_e.Raise()


# ── HorizontalAlignment shorthand ────────────────────────────────────────────
from System.Windows import HorizontalAlignment as System_HAlign


# =============================================================================
# REGISTER CDY TOOLS PANEL
# =============================================================================

try:
    if not forms.is_registered_dockable_panel(CDYToolsPanel):
        forms.register_dockable_panel(CDYToolsPanel)
        print("CDY: CDYToolsPanel registered OK.")
    else:
        print("CDY: CDYToolsPanel already registered, skipping.")
except Exception as ex:
    print("CDY: CDYToolsPanel REGISTRATION FAILED: {}".format(ex))
