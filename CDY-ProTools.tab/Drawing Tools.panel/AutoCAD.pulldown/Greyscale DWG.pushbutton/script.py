# -*- coding: utf-8 -*-
"""
Greyscale DWG — overrides all DWG layers to black + halftone in the active view
or its applied view template.
Place at: Developer.panel\Testing Zone.pulldown\Greyscale DWG.pushbutton\script.py
"""

from pyrevit import HOST_APP, forms
import Autodesk.Revit.DB as DB
from pyrevit import revit



uidoc = revit.uidoc
doc = revit.doc
view = doc.ActiveView

sel_ids = uidoc.Selection.GetElementIds()
if not sel_ids:
    forms.alert("Select a linked DWG first.", title="Greyscale DWG")
    raise SystemExit

import_inst = None
for eid in sel_ids:
    elem = doc.GetElement(eid)
    if isinstance(elem, DB.ImportInstance):
        import_inst = elem
        break

if not import_inst:
    forms.alert("No linked DWG found in selection.", title="Greyscale DWG")
    raise SystemExit

root_cat = import_inst.Category
if not root_cat:
    forms.alert("Cannot read DWG category.", title="Greyscale DWG")
    raise SystemExit

tid    = view.ViewTemplateId
target = doc.GetElement(tid) \
         if tid != DB.ElementId.InvalidElementId else view

black = DB.Color(0, 0, 0)
ogs   = DB.OverrideGraphicSettings()
ogs.SetProjectionLineColor(black)
ogs.SetProjectionLinePatternId(DB.ElementId.InvalidElementId)
ogs.SetHalftone(True)

from Autodesk.Revit.DB import Transaction

with Transaction(doc, "CDY: Greyscale DWG") as t:
    t.Start()
    try:
        # Override the root DWG category
        target.SetCategoryOverrides(root_cat.Id, ogs)
        # Override every sub-category (layer)
        for sub in root_cat.SubCategories:
            try:
                target.SetCategoryOverrides(sub.Id, ogs)
            except Exception:
                pass
        t.Commit()
    except Exception as ex:
        t.RollBack()
        forms.alert("Failed:\n{}".format(ex), title="Greyscale DWG")
