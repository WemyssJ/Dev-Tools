# -*- coding: utf-8 -*-
"""
Grid Manager / Flip Grid Bubbles — robust version
"""

from pyrevit import HOST_APP, forms
import Autodesk.Revit.DB as DB
from Autodesk.Revit.DB import Transaction
from Autodesk.Revit import UI, Exceptions
import os, sys


# ---------------------------------------------------------------------------
# UI bootstrap safety (same pattern as Dim tools)
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
# Safe warning bar (consistent across toolkit)
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
# Selection (preselection-first pattern like your other tools)
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

    # fallback pick
    with safe_warning_bar("Select grids, then press Finish"):
        try:
            picked = uidoc.Selection.PickElementsByRectangle()
            return [g for g in picked if isinstance(g, DB.Grid)]
        except Exceptions.OperationCanceledException:
            return []


grids = get_grids()

if not grids:
    forms.alert("Select one or more Grids first.", title="Flip Grid Bubbles")
    raise SystemExit


# ---------------------------------------------------------------------------
# Core flip logic (deterministic, no state dependency)
# ---------------------------------------------------------------------------
def flip_grid(grid, view):
    changed = 0

    end0 = DB.DatumEnds.End0
    end1 = DB.DatumEnds.End1

    try:
        e0 = grid.IsBubbleVisibleInView(end0, view)
        e1 = grid.IsBubbleVisibleInView(end1, view)
    except:
        return 0

    # RULE:
    # If both visible → default collapse End1
    # If only one visible → swap it
    # If none visible → show End0
    try:
        if e0 and e1:
            grid.HideBubbleInView(end1, view)
            changed += 1

        elif e0 and not e1:
            grid.HideBubbleInView(end0, view)
            grid.ShowBubbleInView(end1, view)
            changed += 2

        elif e1 and not e0:
            grid.HideBubbleInView(end1, view)
            grid.ShowBubbleInView(end0, view)
            changed += 2

        else:
            grid.ShowBubbleInView(end0, view)
            changed += 1

    except:
        pass

    return changed


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------
with Transaction(doc, "CDY: Flip Grid Bubbles") as t:
    t.Start()

    total_changes = 0

    for g in grids:
        total_changes += flip_grid(g, view)

    if total_changes:
        t.Commit()
    else:
        t.RollBack()


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------
if total_changes == 0:
    forms.alert("No grid bubbles were changed.", title="Flip Grid Bubbles")
else:
    forms.alert(
        "{} change operations applied to grids.".format(total_changes),
        title="Flip Grid Bubbles"
    )
