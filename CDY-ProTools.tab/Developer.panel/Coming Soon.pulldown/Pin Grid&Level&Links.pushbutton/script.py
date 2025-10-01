# -*- coding: utf-8 -*-
# pyRevit script: Pin Grids, Levels, Revit Links, and CAD Imports

from Autodesk.Revit.DB import FilteredElementCollector, Grid, Level, ImportInstance, RevitLinkInstance, Transaction
from Autodesk.Revit.UI import TaskDialog

doc = __revit__.ActiveUIDocument.Document

# Collect elements
grids = FilteredElementCollector(doc).OfClass(Grid).ToElements()
levels = FilteredElementCollector(doc).OfClass(Level).ToElements()
cad_imports = FilteredElementCollector(doc).OfClass(ImportInstance).ToElements()
revit_links = FilteredElementCollector(doc).OfClass(RevitLinkInstance).ToElements()

count = 0
t = Transaction(doc, "Pin Grids, Levels, Revit Links, and CAD Imports")
t.Start()

# Pin Grids
for g in grids:
    if not g.Pinned:
        g.Pinned = True
        count += 1

# Pin Levels
for l in levels:
    if not l.Pinned:
        l.Pinned = True
        count += 1

# Pin CAD Imports
for c in cad_imports:
    if not c.Pinned:
        c.Pinned = True
        count += 1

# Pin Revit Links
for r in revit_links:
    if not r.Pinned:
        r.Pinned = True
        count += 1

t.Commit()

TaskDialog.Show("Auto-Pin Elements", "{} elements pinned (Grids, Levels, Revit Links, CAD Imports).".format(count))
