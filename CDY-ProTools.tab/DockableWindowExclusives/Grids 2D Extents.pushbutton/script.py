# -*- coding: utf-8 -*-
"""
Grid Manager / Set All Grid Extents (2D or 3D)
"""

from pyrevit import HOST_APP, forms
import Autodesk.Revit.DB as DB
from Autodesk.Revit.DB import Transaction
from Autodesk.Revit import UI, Exceptions


# ---------------------------------------------------------------------------
# UI bootstrap safety
# ---------------------------------------------------------------------------
uiapp = getattr(HOST_APP, "uiapp", None) or __revit__
uidoc = uiapp.ActiveUIDocument
doc   = uidoc.Document
view  = doc.ActiveView


# ---------------------------------------------------------------------------
# Safe warning bar
# ---------------------------------------------------------------------------
def safe_warning_bar(title):
    try:
        return forms.WarningBar(title=title)
    except:
        class _Dummy:
            def __enter__(self): pass
            def __exit__(self, *a): pass
        return _Dummy()


# ---------------------------------------------------------------------------
# Selection (pre + post)
# ---------------------------------------------------------------------------
def get_grids():
    sel = uidoc.Selection.GetElementIds()

    pre = [
        doc.GetElement(i)
        for i in sel
        if isinstance(doc.GetElement(i), DB.Grid)
    ]

    if pre:
        return pre

    with safe_warning_bar("Select grids, then press Finish"):
        try:
            picked = uidoc.Selection.PickElementsByRectangle()
            return [g for g in picked if isinstance(g, DB.Grid)]
        except Exceptions.OperationCanceledException:
            return []


grids = get_grids()

if not grids:
    forms.alert("Select one or more grids first.", title="Grid Extents")
    raise SystemExit


# ---------------------------------------------------------------------------
# CORE SETTERS
# ---------------------------------------------------------------------------
def set_all_2d(grid, view):
    try:
        # View-specific extents (2D)
        grid.SetDatumExtentType(DB.DatumEnds.End0, view, DB.DatumExtentType.ViewSpecific)
        grid.SetDatumExtentType(DB.DatumEnds.End1, view, DB.DatumExtentType.ViewSpecific)
        return 1
    except:
        return 0


def set_all_3d(grid, view):
    try:
        # IMPORTANT: clear view-specific dominance first (prevents silent failure)
        try:
            grid.HideBubbleInView(DB.DatumEnds.End0, view)
            grid.HideBubbleInView(DB.DatumEnds.End1, view)
        except:
            pass

        # Model extents (3D)
        grid.SetDatumExtentType(DB.DatumEnds.End0, view, DB.DatumExtentType.Model)
        grid.SetDatumExtentType(DB.DatumEnds.End1, view, DB.DatumExtentType.Model)
        return 1
    except:
        return 0


# ---------------------------------------------------------------------------
# USER CHOICE (simple + explicit)
# ---------------------------------------------------------------------------
choice = forms.CommandSwitchWindow.show(
    ["Set ALL to 2D (ViewSpecific)", "Set ALL to 3D (Model)"],
    message="Grid Extents Mode"
)

if not choice:
    raise SystemExit


mode_2d = "2D" in choice


# ---------------------------------------------------------------------------
# TRANSACTION
# ---------------------------------------------------------------------------
with Transaction(doc, "CDY: Set All Grid Extents") as t:
    t.Start()

    changed = 0

    for g in grids:
        if mode_2d:
            changed += set_all_2d(g, view)
        else:
            changed += set_all_3d(g, view)

    if changed:
        t.Commit()
    else:
        t.RollBack()


# ---------------------------------------------------------------------------
# FEEDBACK
# ---------------------------------------------------------------------------
if changed == 0:
    forms.alert("No grid extents were changed.", title="Grid Extents")
else:
    forms.alert(
        "{} grids updated to {} mode.".format(
            changed,
            "2D" if mode_2d else "3D"
        ),
        title="Grid Extents"
    )