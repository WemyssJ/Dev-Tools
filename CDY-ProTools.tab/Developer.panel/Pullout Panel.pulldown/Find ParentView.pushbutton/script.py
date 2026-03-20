# -*- coding: utf-8 -*-
"""
Find Parent / Primary View — opens the primary view when the active view is a dependent.
Place at: Developer.panel\PulloutPanel.pulldown\Find ParentView.pushbutton\script.py
"""

from pyrevit import HOST_APP, forms
import Autodesk.Revit.DB as DB

uidoc = __uidoc__ or (HOST_APP.uiapp.ActiveUIDocument if HOST_APP else None)
if not uidoc:
    raise RuntimeError("No active document.")

doc  = uidoc.Document
view = doc.ActiveView

parent_id = view.GetPrimaryViewId()
if parent_id and parent_id != DB.ElementId.InvalidElementId:
    parent = doc.GetElement(parent_id)
    if parent:
        uidoc.ActiveView = parent
    else:
        forms.alert("Parent view element not found.", title="Find Parent View")
else:
    forms.alert("Active view has no parent — it is already a primary view.",
                title="Find Parent View")
