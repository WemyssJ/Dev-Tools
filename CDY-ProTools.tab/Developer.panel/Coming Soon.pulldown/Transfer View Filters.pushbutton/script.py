# -*- coding: utf-8 -*-
__title__   = "Transfer View Filters"
__doc__     = """Version = 1.6
Date    = 08.20.2025
Optimized version with caching and minimal API calls.
Only shows templates currently in use by at least one view.
"""

import sys
import clr
clr.AddReference('System')
clr.AddReference('RevitAPI')

from Autodesk.Revit.DB import *
from pyrevit import revit, DB, forms

#============================================ VARIABLES
doc = __revit__.ActiveUIDocument.Document
active_view = __revit__.ActiveUIDocument.ActiveView

#============================================ CACHES
line_pattern_cache = {}
fill_pattern_cache = {}
color_cache = {}

#============================================ HELPERS

def color_to_rgb_square(c):
    """Cache Revit Color objects to avoid repeated processing."""
    if not c or not c.IsValid:
        return "⬜ None"
    key = (c.Red, c.Green, c.Blue)
    if key in color_cache:
        return color_cache[key]
    rgbval = "({0}, {1}, {2})".format(c.Red, c.Green, c.Blue)
    swatch = u"\u2588\u2588 " + rgbval
    color_cache[key] = swatch
    return swatch


def get_line_pattern_preview(pid):
    """Cache LinePatternElement previews."""
    if not pid or pid == ElementId.InvalidElementId:
        return "None"
    if pid in line_pattern_cache:
        return line_pattern_cache[pid]
    lpe = doc.GetElement(pid)
    if not lpe:
        return "None"  # <-- safeguard
    preview = ""
    try:
        for seg in lpe.GetLinePattern().Segments:
            if seg.SegmentType == LinePatternSegmentType.Dash:
                preview += "- "
            elif seg.SegmentType == LinePatternSegmentType.Dot:
                preview += "· "
            elif seg.SegmentType == LinePatternSegmentType.Space:
                preview += "  "
            elif seg.SegmentType == LinePatternSegmentType.Solid:
                preview += "─"
    except:
        preview = lpe.Name if lpe else "None"
    line_pattern_cache[pid] = preview.strip()
    return line_pattern_cache[pid]

def get_fill_pattern_name(pid):
    """Cache FillPatternElement names."""
    if not pid or pid == ElementId.InvalidElementId:
        return "None"
    if pid in fill_pattern_cache:
        return fill_pattern_cache[pid]
    el = doc.GetElement(pid)
    name = el.Name if el else "None"
    fill_pattern_cache[pid] = name
    return name

def copy_overrides(src_override):
    """Build a new OverrideGraphicSettings object from existing one."""
    ovr = OverrideGraphicSettings()
    ovr.SetCutLineColor(src_override.CutLineColor)
    ovr.SetProjectionLineColor(src_override.ProjectionLineColor)
    ovr.SetCutLineWeight(src_override.CutLineWeight)
    ovr.SetProjectionLineWeight(src_override.ProjectionLineWeight)
    ovr.SetCutLinePatternId(src_override.CutLinePatternId)
    ovr.SetProjectionLinePatternId(src_override.ProjectionLinePatternId)
    ovr.SetCutForegroundPatternId(src_override.CutForegroundPatternId)
    ovr.SetCutForegroundPatternColor(src_override.CutForegroundPatternColor)
    ovr.SetCutBackgroundPatternId(src_override.CutBackgroundPatternId)
    ovr.SetCutBackgroundPatternColor(src_override.CutBackgroundPatternColor)
    ovr.SetSurfaceForegroundPatternId(src_override.SurfaceForegroundPatternId)
    ovr.SetSurfaceForegroundPatternColor(src_override.SurfaceForegroundPatternColor)
    ovr.SetSurfaceBackgroundPatternId(src_override.SurfaceBackgroundPatternId)
    ovr.SetSurfaceBackgroundPatternColor(src_override.SurfaceBackgroundPatternColor)
    ovr.SetHalftone(src_override.Halftone)
    ovr.SetSurfaceTransparency(src_override.Transparency)
    return ovr

#============================================ MAIN

# Get applied filters
applied_filters = active_view.GetFilters()
if not applied_filters:
    forms.alert("No filters are applied to the active view.", exitscript=True)

filter_map = {}
items = []

for fid in applied_filters:
    f = doc.GetElement(fid)
    ovr = active_view.GetFilterOverrides(fid)
    
    # Use cached helpers
    proj_color = color_to_rgb_square(ovr.ProjectionLineColor)
    cut_color  = color_to_rgb_square(ovr.CutLineColor)
    proj_pattern = get_line_pattern_preview(ovr.ProjectionLinePatternId)
    cut_pattern  = get_line_pattern_preview(ovr.CutLinePatternId)
    surf_fg = get_fill_pattern_name(ovr.SurfaceForegroundPatternId)
    surf_bg = get_fill_pattern_name(ovr.SurfaceBackgroundPatternId)
    cut_fg  = get_fill_pattern_name(ovr.CutForegroundPatternId)
    cut_bg  = get_fill_pattern_name(ovr.CutBackgroundPatternId)

    desc = "[{0}]\nProj: {1}, Wt:{2}, Pat:{3}\nCut: {4}, Wt:{5}, Pat:{6}\nSurface Fg:{7}, Bg:{8} | Cut Fg:{9}, Bg:{10}\nTransparency:{11}% | Halftone:{12}".format(
        f.Name,
        proj_color,
        ovr.ProjectionLineWeight,
        proj_pattern,
        cut_color,
        ovr.CutLineWeight,
        cut_pattern,
        surf_fg,
        surf_bg,
        cut_fg,
        cut_bg,
        ovr.Transparency,
        ovr.Halftone
    )

    items.append(desc)
    filter_map[f.Name] = (fid, ovr)

# Select filters
selected_descs = forms.SelectFromList.show(
    items, multiselect=True, title="Select Filters from Active View (with overrides)"
)
if not selected_descs:
    sys.exit()

selected_filters = [desc.split("\n")[0].strip("[]") for desc in selected_descs]

# Collect only view templates that are actually assigned to views
all_views = DB.FilteredElementCollector(doc).OfClass(DB.View).ToElements()
template_ids_in_use = set()

for v in all_views:
    tid = v.ViewTemplateId
    if tid and tid != DB.ElementId.InvalidElementId:
        template_ids_in_use.add(tid)

used_templates = [doc.GetElement(tid) for tid in template_ids_in_use]

if not used_templates:
    forms.alert("No view templates are currently in use.", exitscript=True)

# Let user pick only from in-use templates
templates = forms.SelectFromList.show(
    used_templates,
    multiselect=True,
    title='Select In-Use View Templates',
    name_attr='Name'
)
if not templates:
    sys.exit()

# Apply overrides in a single transaction
t = DB.Transaction(doc, 'Apply View Filters to Templates')
t.Start()
for fname in selected_filters:
    fid, existing_override = filter_map[fname]
    for template in templates:
        if not template.IsFilterApplied(fid):
            template.AddFilter(fid)
        template.SetFilterOverrides(fid, copy_overrides(existing_override))
t.Commit()
forms.alert("Filters successfully applied!", title="Done")
