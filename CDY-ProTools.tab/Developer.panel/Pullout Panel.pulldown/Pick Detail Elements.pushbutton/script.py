# -*- coding: utf-8 -*-
# pylint: skip-file
"""Activates selection tool that picks only Detail 2D elements."""

from pyrevit import forms
import Autodesk.Revit.DB as DB
from Autodesk.Revit.UI.Selection import ISelectionFilter
from System.Collections.Generic import List as DotNetList

uidoc = __uidoc__
if not uidoc:
    raise SystemExit


class DetailSelectionFilter(ISelectionFilter):
    def AllowElement(self, element):
        # Only view-specific (detail/annotation) elements not in a group
        if element.ViewSpecific:
            if element.GroupId == element.GroupId.InvalidElementId:
                return True
        return False

    def AllowReference(self, refer, point):
        return False


try:
    picked = uidoc.Selection.PickElementsByRectangle(
        DetailSelectionFilter(), "Box-select 2D / detail elements")
    if picked:
        uidoc.Selection.SetElementIds(
            DotNetList[DB.ElementId]([e.Id for e in picked]))
    else:
        forms.toast("No 2D elements found in selection box.")
except Exception:
    pass
