# -*- coding: utf-8 -*-
"""
Flip Level Ends — flips bubble ends for all selected levels.
Place at: Developer.panel\PulloutPanel.pulldown\Flip Level Ends.pushbutton\script.py
"""

from pyrevit import HOST_APP, forms
import Autodesk.Revit.DB as DB

uidoc = __uidoc__ or (HOST_APP.uiapp.ActiveUIDocument if HOST_APP else None)
if not uidoc:
    raise SystemExit

doc  = uidoc.Document
view = doc.ActiveView

sel_ids = uidoc.Selection.GetElementIds()
levels  = [doc.GetElement(i) for i in sel_ids
           if isinstance(doc.GetElement(i), DB.Level)]

if not levels:
    forms.alert("Select one or more Levels first.", title="Flip Level Bubbles")
    raise SystemExit

from Autodesk.Revit.DB import Transaction

with Transaction(doc, "CDY: Flip Level Bubbles") as t:
    t.Start()
    for level in levels:
        end0_visible = level.IsBubbleVisibleInView(DB.DatumEnds.End0, view)
        if end0_visible:
            level.HideBubbleInView(DB.DatumEnds.End0, view)
            level.ShowBubbleInView(DB.DatumEnds.End1, view)
        else:
            level.ShowBubbleInView(DB.DatumEnds.End0, view)
            level.HideBubbleInView(DB.DatumEnds.End1, view)
    t.Commit()
