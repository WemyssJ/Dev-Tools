# -*- coding: utf-8 -*-
__title__ = 'Flip Level Ends'
__doc__ = """Flip visibility of bubbles at the ends of selected levels."""

import os, sys

from pyrevit import HOST_APP, revit, forms
from Autodesk.Revit.DB import Level, DatumEnds, Transaction, BuiltInCategory
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.UI.Selection import ISelectionFilter
from Autodesk.Revit import Exceptions


# ---------------------------------------------------------------------------
# UI bootstrap fix (same pattern as Dim tools)
# ---------------------------------------------------------------------------
uiapp = getattr(HOST_APP, "uiapp", None) or __revit__

try:
    if hasattr(uiapp, "MainWindowHandle") and not uiapp.MainWindowHandle:
        import pyrevit
        pyrevit.framework.get_current_uiapp()
except:
    pass

doc   = uiapp.ActiveUIDocument.Document
uidoc = uiapp.ActiveUIDocument
view  = doc.ActiveView


# ---------------------------------------------------------------------------
# Safe warning bar (same pattern as grids/levels tools)
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
# Telemetry (unchanged but safe-guarded)
# ---------------------------------------------------------------------------
lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'lib'))
if lib_path not in sys.path:
    sys.path.append(lib_path)

try:
    import telemetry_auto
    TOOL_NAME = os.path.basename(os.path.dirname(__file__)).replace(".pushbutton", "")
    telemetry_auto.log_tool_usage(TOOL_NAME)
except:
    pass


# ---------------------------------------------------------------------------
# Selection filter (Revit-safe category ID, not string matching)
# ---------------------------------------------------------------------------
class LevelFilter(ISelectionFilter):
    def AllowElement(self, e):
        return (
            isinstance(e, Level)
            or (e.Category and e.Category.Id.IntegerValue == int(BuiltInCategory.OST_Levels))
        )

    def AllowReference(self, reference, point):
        return False


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------
def get_selected_levels():
    pre = [
        doc.GetElement(i)
        for i in uidoc.Selection.GetElementIds()
        if isinstance(doc.GetElement(i), Level)
    ]

    if pre:
        return pre

    with safe_warning_bar("Select levels, then press Finish"):
        try:
            return list(uidoc.Selection.PickElementsByRectangle(LevelFilter()))
        except Exceptions.OperationCanceledException:
            return []


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------
def flip_level(level, view):
    if not level.CanBeVisibleInView(view):
        return False

    changed = 0

    for end in (DatumEnds.End0, DatumEnds.End1):

        is_visible = level.IsBubbleVisibleInView(end, view)

        # If visible → hide
        if is_visible:
            try:
                level.HideBubbleInView(end, view)
                changed += 1
            except:
                pass

        # If hidden → show
        else:
            try:
                level.ShowBubbleInView(end, view)
                changed += 1
            except:
                pass

    return changed > 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    levels = get_selected_levels()

    if not levels:
        return

    changed_total = 0

    with Transaction(doc, __title__) as t:
        t.Start()

        for lvl in levels:
            changed_total += int(flip_level(lvl, view))

        if changed_total:
            t.Commit()
        else:
            t.RollBack()


    # Feedback
    if changed_total == 0:
        TaskDialog.Show(__title__, "Nothing flipped")

# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    main()
