# -*- coding: utf-8 -*-
"""
Pick Grouped Elements — select groups then expand the selection to all members.
Place at: Developer.panel\PulloutPanel.pulldown\Pick Grouped Elements.pushbutton\script.py
"""

from pyrevit import HOST_APP, forms
import Autodesk.Revit.DB as DB
from Autodesk.Revit.UI.Selection import ISelectionFilter
from System.Collections.Generic import List as DotNetList

uidoc = __uidoc__ or (HOST_APP.uiapp.ActiveUIDocument if HOST_APP else None)
if not uidoc:
    raise SystemExit

doc = uidoc.Document


class GroupFilter(ISelectionFilter):
    def AllowElement(self, elem):
        return isinstance(elem, DB.Group)

    def AllowReference(self, ref, point):
        return False


try:
    groups = uidoc.Selection.PickElementsByRectangle(GroupFilter(),
                                                     "Box-select groups")
except Exception:
    raise SystemExit

if not groups:
    forms.alert("No groups selected.", title="Pick Grouped Elements")
    raise SystemExit

all_ids = []
for grp in groups:
    all_ids.extend(grp.GetMemberIds())

if all_ids:
    uidoc.Selection.SetElementIds(DotNetList[DB.ElementId](all_ids))
else:
    forms.alert("Selected groups contain no members.", title="Pick Grouped Elements")
