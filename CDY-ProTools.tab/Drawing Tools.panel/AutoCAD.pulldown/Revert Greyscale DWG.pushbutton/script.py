# -*- coding: utf-8 -*-
"""
Revert Greyscale DWG — removes all colour overrides on the selected DWG,
restoring Revit defaults.
Place at: Developer.panel\Testing Zone.pulldown\Revert Greyscale DWG.pushbutton\script.py
"""

from pyrevit import HOST_APP, forms
import Autodesk.Revit.DB as DB

uidoc = __uidoc__ or (HOST_APP.uiapp.ActiveUIDocument if HOST_APP else None)
if not uidoc:
    raise SystemExit

doc  = uidoc.Document
view = doc.ActiveView

sel_ids = uidoc.Selection.GetElementIds()
if not sel_ids:
    forms.alert("Select a linked DWG first.", title="Revert Greyscale DWG")
    raise SystemExit

import_inst = None
for eid in sel_ids:
    elem = doc.GetElement(eid)
    if isinstance(elem, DB.ImportInstance):
        import_inst = elem
        break

if not import_inst:
    forms.alert("No linked DWG found in selection.", title="Revert Greyscale DWG")
    raise SystemExit

root_cat = import_inst.Category
if not root_cat:
    forms.alert("Cannot read DWG category.", title="Revert Greyscale DWG")
    raise SystemExit

tid    = view.ViewTemplateId
target = doc.GetElement(tid) \
         if tid != DB.ElementId.InvalidElementId else view

blank = DB.OverrideGraphicSettings()   # default / no overrides

from Autodesk.Revit.DB import Transaction

with Transaction(doc, "CDY: Revert Greyscale DWG") as t:
    t.Start()
    try:
        target.SetCategoryOverrides(root_cat.Id, blank)
        for sub in root_cat.SubCategories:
            try:
                target.SetCategoryOverrides(sub.Id, blank)
            except Exception:
                pass
        t.Commit()
    except Exception as ex:
        t.RollBack()
        forms.alert("Failed:\n{}".format(ex), title="Revert Greyscale DWG")
