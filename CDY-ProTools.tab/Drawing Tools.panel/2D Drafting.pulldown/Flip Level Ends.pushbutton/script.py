# -*- coding: utf-8 -*-
__title__ = 'Flip Level Ends'
__doc__ = """Flip visibility of bubbles at the ends of selected levels. If both bubbles were visible, only one remains."""

try:
    from pyrevit.versionmgr import PYREVIT_VERSION
except:
    from pyrevit import versionmgr
    PYREVIT_VERSION = versionmgr.get_pyrevit_version()

from pyrevit import script, revit
output = script.get_output()
logger = script.get_logger()
linkify = output.linkify
doc = revit.doc
uidoc = revit.uidoc
selection = revit.get_selection()

from Autodesk.Revit.DB import Level, DatumEnds, Transaction
from Autodesk.Revit import UI
from Autodesk.Revit.UI import TaskDialog

##############################################################################################
# TELEMETRY IMPORTS #
##############################################################################################
# Only works IF specified TELEMETRY_JSON path exists within %AppData%\pyRevit\Extensions\BIMTools.extension\lib\telemetry_auto.py"
# Records tool usage by date & revit version
import os, sys

# Add lib folder for telemetry_auto
lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'lib'))
if lib_path not in sys.path:
    sys.path.append(lib_path)

import telemetry_auto

tool_name = os.path.basename(os.path.dirname(__file__)) 
TOOL_NAME = tool_name.replace(".pushbutton", "")
telemetry_auto.log_tool_usage(TOOL_NAME)
##############################################################################################

class PickByCategorySelectionFilter(UI.Selection.ISelectionFilter):
    def __init__(self, catname):
        self.category = catname

    def AllowElement(self, element):
        return self.category in element.Category.Name

    def AllowReference(self, refer, point):
        return False


def pickbycategory(catname):
    msfilter = PickByCategorySelectionFilter(catname)
    selection_list = revit.pick_rectangle(pick_filter=msfilter)
    return selection_list


def get_selected_levels():
    sel = selection.elements
    sel = filter(lambda x: isinstance(x, Level), sel)

    if len(sel) == 0:
        TaskDialog.Show(__title__, "Select Levels to flip bubbles visibility")
        sel = pickbycategory("Level")
        if not sel:
            return

    return list(sel)


def flip_level(level, view):
    if not level.CanBeVisibleInView(view):
        return

    ends = [DatumEnds.End0, DatumEnds.End1]
    last = None
    changed = 0
    for end in ends:
        if level.IsBubbleVisibleInView(end, view) and not last:
            level.HideBubbleInView(end, view)
            last = True
            changed += 1
        else:
            if not level.IsBubbleVisibleInView(end, view):
                level.ShowBubbleInView(end, view)
                changed += 1

    return bool(changed)


def main():
    sel_levels = get_selected_levels()
    if not sel_levels:
        return
    active_view = doc.ActiveView

    changed = 0
    t = Transaction(doc)
    t.Start(__title__)

    for lvl in sel_levels:
        changed += bool(flip_level(lvl, active_view))

    if changed > 0:
        t.Commit()
    else:
        t.Rollback()

    if changed != len(sel_levels):
        TaskDialog.Show(__title__, "%d of %d levels were flipped" % (changed, len(sel_levels)))
    elif changed == 0:
        TaskDialog.Show(__title__, "Nothing flipped")

if __name__ == '__main__':
    main()
