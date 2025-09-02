# -*- coding: utf-8 -*-
# pyRevit script: Pin all Grids and Levels in the model


from Autodesk.Revit.DB import FilteredElementCollector, Grid, Level, Transaction
from Autodesk.Revit.UI import TaskDialog

doc = __revit__.ActiveUIDocument.Document

# Collect Grids and Levels
grids = FilteredElementCollector(doc).OfClass(Grid).ToElements()
levels = FilteredElementCollector(doc).OfClass(Level).ToElements()

count = 0
t = Transaction(doc, "Pin Grids and Levels")
t.Start()

for g in grids:
    if not g.Pinned:
        g.Pinned = True
        count += 1

for l in levels:
    if not l.Pinned:
        l.Pinned = True
        count += 1

t.Commit()

TaskDialog.Show("Grid/Level Auto-Pin", "{} elements pinned.".format(count))
