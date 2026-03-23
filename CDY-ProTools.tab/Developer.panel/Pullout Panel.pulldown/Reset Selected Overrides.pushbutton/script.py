# -*- coding: utf-8 -*-
"""
Reset Selected Overrides
Removes all graphic overrides from selected elements in the active view.
Place at: Developer.panel\Pullout Panel.pulldown\Reset Selected Overrides.pushbutton\script.py
"""
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import *

doc   = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
view  = doc.ActiveView

selection_ids = uidoc.Selection.GetElementIds()

if not selection_ids:
    TaskDialog.Show("Reset Selected Overrides", "Please select elements first.")
    script.exit()

t = Transaction(doc, "CDY: Reset Selected Graphic Overrides")
t.Start()
for eid in selection_ids:
    view.SetElementOverrides(eid, OverrideGraphicSettings())
t.Commit()
