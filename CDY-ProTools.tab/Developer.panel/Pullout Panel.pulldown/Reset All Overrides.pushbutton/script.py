# -*- coding: utf-8 -*-
"""
Reset All Overrides
Removes all graphic overrides from every element in the active view.
Place at: Developer.panel\Pullout Panel.pulldown\Reset All Overrides.pushbutton\script.py
"""
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import *

doc   = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
view  = doc.ActiveView

# Collect all elements visible in the active view (excluding element types)
element_ids = (
    FilteredElementCollector(doc, view.Id)
    .WhereElementIsNotElementType()
    .ToElementIds()
)

if not element_ids:
    TaskDialog.Show("Reset All Overrides", "No elements found in the active view.")
    script.exit()

t = Transaction(doc, "CDY: Reset All Graphic Overrides")
t.Start()
blank = OverrideGraphicSettings()
for eid in element_ids:
    view.SetElementOverrides(eid, blank)
t.Commit()
