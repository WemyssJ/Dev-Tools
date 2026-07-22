# -*- coding: utf-8 -*-
"""
Reload Selected DWG — reloads the selected linked DWG from its current path.
Place at: Developer.panel\PulloutPanel.pulldown\Reload DWG.pushbutton\script.py
"""

from pyrevit import HOST_APP, forms
import Autodesk.Revit.DB as DB

uidoc = __uidoc__ or (HOST_APP.uiapp.ActiveUIDocument if HOST_APP else None)
if not uidoc:
    raise SystemExit

doc = uidoc.Document

sel_ids = uidoc.Selection.GetElementIds()
if not sel_ids:
    forms.alert("Select a linked DWG first.", title="Reload DWG")
    raise SystemExit

import_inst = None
for eid in sel_ids:
    elem = doc.GetElement(eid)
    if isinstance(elem, DB.ImportInstance):
        import_inst = elem
        break

if not import_inst:
    forms.alert("No linked DWG found in selection.", title="Reload DWG")
    raise SystemExit

link_type = doc.GetElement(import_inst.GetTypeId())
if not link_type:
    forms.alert("Cannot find the CAD link type.", title="Reload DWG")
    raise SystemExit

from Autodesk.Revit.DB import Transaction

with Transaction(doc, "CDY: Reload DWG") as t:
    t.Start()
    try:
        result = link_type.Reload()
        t.Commit()
        if result.LoadStatus == DB.LinkLoadResultType.Loaded:
            forms.toast("DWG reloaded successfully.")
        else:
            forms.alert("Reload status: {}".format(result.LoadStatus),
                        title="Reload DWG")
    except Exception as ex:
        t.RollBack()
        forms.alert("Reload failed:\n{}".format(ex), title="Reload DWG")
