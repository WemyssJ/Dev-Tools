# -*- coding: utf-8 -*-
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import *

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
view = doc.ActiveView

selection_ids = uidoc.Selection.GetElementIds()

if not selection_ids:
    TaskDialog.Show("Revit Green", "Please select elements first.")
    script.exit()

# Slightly softer Revit-style green
green = Color(0, 200, 0)

# Get solid fill pattern
solid_fill = None
for fp in FilteredElementCollector(doc).OfClass(FillPatternElement):
    if fp.GetFillPattern().IsSolidFill:
        solid_fill = fp
        break

if not solid_fill:
    TaskDialog.Show("Error", "Solid fill pattern not found.")
    script.exit()

# Create override settings
override = OverrideGraphicSettings()

# --- PROJECTION ---
override.SetProjectionLineColor(green)
override.SetSurfaceForegroundPatternId(solid_fill.Id)
override.SetSurfaceForegroundPatternColor(green)

# --- CUT ---
override.SetCutLineColor(green)
override.SetCutForegroundPatternId(solid_fill.Id)
override.SetCutForegroundPatternColor(green)

# Apply overrides
t = Transaction(doc, "Make Elements Revit Green (Full)")
t.Start()

for eid in selection_ids:
    view.SetElementOverrides(eid, override)

t.Commit()