# -*- coding: utf-8 -*-
"""
Grid Manager / Flip Grid Bubbles — flips bubble ends for all selected grids.
Place at: Developer.panel\PulloutPanel.pulldown\Grid Manager.pushbutton\script.py
"""

from pyrevit import HOST_APP, forms
import Autodesk.Revit.DB as DB

uidoc = __uidoc__ or (HOST_APP.uiapp.ActiveUIDocument if HOST_APP else None)
if not uidoc:
    raise SystemExit

doc  = uidoc.Document
view = doc.ActiveView

sel_ids = uidoc.Selection.GetElementIds()
grids   = [doc.GetElement(i) for i in sel_ids
           if isinstance(doc.GetElement(i), DB.Grid)]

if not grids:
    forms.alert("Select one or more Grids first.", title="Flip Grid Bubbles")
    raise SystemExit

from Autodesk.Revit.DB import Transaction

with Transaction(doc, "CDY: Flip Grid Bubbles") as t:
    t.Start()
    for grid in grids:
        # Toggle: if end 0 is hidden, show it; if shown, hide it
        end0_visible = grid.IsBubbleVisibleInView(DB.DatumEnds.End0, view)
        end1_visible = grid.IsBubbleVisibleInView(DB.DatumEnds.End1, view)
        if end0_visible:
            grid.HideBubbleInView(DB.DatumEnds.End0, view)
            grid.ShowBubbleInView(DB.DatumEnds.End1, view)
        else:
            grid.ShowBubbleInView(DB.DatumEnds.End0, view)
            grid.HideBubbleInView(DB.DatumEnds.End1, view)
    t.Commit()
