# -*- coding: utf-8 -*-
"""
Find Sheet — open the host sheet for the active view.
Place at: Developer.panel\PulloutPanel.pulldown\Find Sheet.pushbutton\script.py
"""

from pyrevit import HOST_APP
import Autodesk.Revit.DB as DB

uidoc = __uidoc__ or (HOST_APP.uiapp.ActiveUIDocument if HOST_APP else None)
if not uidoc:
    raise RuntimeError("No active document.")

doc  = uidoc.Document
view = doc.ActiveView

# Find the sheet that hosts this view
sheets = DB.FilteredElementCollector(doc).OfClass(DB.ViewSheet).ToElements()
host_sheet = None
for sheet in sheets:
    vp_ids = sheet.GetAllViewports()
    for vp_id in vp_ids:
        vp = doc.GetElement(vp_id)
        if vp and vp.ViewId == view.Id:
            host_sheet = sheet
            break
    if host_sheet:
        break

if host_sheet:
    uidoc.ActiveView = host_sheet
else:
    from pyrevit import forms
    forms.alert("Active view is not placed on any sheet.", title="Find Sheet")
