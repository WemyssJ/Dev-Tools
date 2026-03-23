# -*- coding: utf-8 -*-
"""
Find View — if a viewport is already selected, jump to it immediately.
Otherwise prompt the user to pick one on the sheet.
Place at: Developer.panel\PulloutPanel.pulldown\Find View.pushbutton\script.py
"""
 
from pyrevit import HOST_APP, forms
import Autodesk.Revit.DB as DB
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
 
uidoc = __uidoc__ or (HOST_APP.uiapp.ActiveUIDocument if HOST_APP else None)
if not uidoc:
    raise RuntimeError("No active document.")
 
doc = uidoc.Document
 
 
class ViewportFilter(ISelectionFilter):
    def AllowElement(self, elem):
        return isinstance(elem, DB.Viewport)
    def AllowReference(self, ref, point):
        return False
 
 
# ── 1. Check for a pre-existing selection of exactly one Viewport ────────────
vp = None
 
current_ids = list(uidoc.Selection.GetElementIds())
if current_ids:
    viewports = [doc.GetElement(i) for i in current_ids
                 if isinstance(doc.GetElement(i), DB.Viewport)]
    if len(viewports) == 1:
        vp = viewports[0]
    elif len(viewports) > 1:
        # Multiple viewports selected — let the user choose which one to open
        choices = {"{} — {}".format(
                        doc.GetElement(v.ViewId).Name if doc.GetElement(v.ViewId) else "Unknown",
                        v.Id): v
                   for v in viewports}
        picked = forms.SelectFromList.show(
            sorted(choices.keys()),
            title="Find View",
            prompt="Multiple viewports selected — choose one to open:",
            multiselect=False)
        if not picked:
            raise SystemExit
        vp = choices[picked]
 
# ── 2. Nothing useful selected — ask the user to pick ───────────────────────
if vp is None:
    try:
        ref = uidoc.Selection.PickObject(ObjectType.Element, ViewportFilter(),
                                         "Select a viewport on the sheet")
    except:
        raise SystemExit
    vp = doc.GetElement(ref.ElementId)
 
# ── 3. Open the view ─────────────────────────────────────────────────────────
view = doc.GetElement(vp.ViewId) if vp else None
if view:
    uidoc.ActiveView = view
else:
    forms.alert("Could not find the view for the selected viewport.", title="Find View")