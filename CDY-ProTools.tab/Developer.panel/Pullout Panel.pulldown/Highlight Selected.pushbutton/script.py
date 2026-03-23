# -*- coding: utf-8 -*-
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import *

doc   = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
view  = doc.ActiveView

selection_ids = uidoc.Selection.GetElementIds()

if not selection_ids:
    TaskDialog.Show("Highlight", "Please select elements first.")
    script.exit()

# ── Colour: use injected CDY_HIGHLIGHT_COLOR if available, else default green ─
try:
    r, g, b = CDY_HIGHLIGHT_COLOR  # injected by startup.py HighlightHandler
except NameError:
    r, g, b = 0, 200, 0            # fallback default

highlight_color = Color(r, g, b)

# ── Find solid fill pattern ───────────────────────────────────────────────────
solid_fill = None
for fp in FilteredElementCollector(doc).OfClass(FillPatternElement):
    if fp.GetFillPattern().IsSolidFill:
        solid_fill = fp
        break

if not solid_fill:
    TaskDialog.Show("Error", "Solid fill pattern not found.")
    script.exit()

# ── Build override settings ───────────────────────────────────────────────────
override = OverrideGraphicSettings()

# Projection
override.SetProjectionLineColor(highlight_color)
override.SetSurfaceForegroundPatternId(solid_fill.Id)
override.SetSurfaceForegroundPatternColor(highlight_color)

# Cut
override.SetCutLineColor(highlight_color)
override.SetCutForegroundPatternId(solid_fill.Id)
override.SetCutForegroundPatternColor(highlight_color)

# ── Apply ─────────────────────────────────────────────────────────────────────
t = Transaction(doc, "CDY: Highlight Elements")
t.Start()
for eid in selection_ids:
    view.SetElementOverrides(eid, override)
t.Commit()
