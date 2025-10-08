# -*- coding: utf-8 -*-
__title__ = "Transfer View Filters v5.0"
__doc__ = "Projection/Cut line + weight + pattern, hatch FG/BG + color, Halftone, Transparency"

import clr, sys, os
clr.AddReference('System')
clr.AddReference('PresentationFramework')
clr.AddReference('WindowsBase')
clr.AddReference('PresentationCore')
clr.AddReference('RevitAPI')

from System.IO import FileStream, FileMode
from System.Windows.Markup import XamlReader
from System.ComponentModel import INotifyPropertyChanged
from System.Collections.ObjectModel import ObservableCollection
from System.Windows.Media import SolidColorBrush, Color
from Autodesk.Revit.DB import *
from pyrevit import revit, DB, forms

# ------------------ Document & View ------------------
doc = __revit__.ActiveUIDocument.Document
active_view = __revit__.ActiveUIDocument.ActiveView

# ------------------ Caches ------------------
line_pattern_cache = {}
fill_pattern_cache = {}

# ------------------ Helpers ------------------
def get_fill_pattern_name(pid):
    if not pid or pid == ElementId.InvalidElementId:
        return "None"
    if pid in fill_pattern_cache:
        return fill_pattern_cache[pid]
    el = doc.GetElement(pid)
    name = el.Name if el else "None"
    fill_pattern_cache[pid] = name
    return name

def get_line_pattern_preview(pid):
    if not pid or pid == ElementId.InvalidElementId:
        return ""
    if pid in line_pattern_cache:
        return line_pattern_cache[pid]
    lpe = doc.GetElement(pid)
    if not lpe:
        return ""
    preview = ""
    try:
        for seg in lpe.GetLinePattern().Segments:
            if seg.SegmentType == LinePatternSegmentType.Dash:
                preview += "─ "
            elif seg.SegmentType == LinePatternSegmentType.Dot:
                preview += "· "
            elif seg.SegmentType == LinePatternSegmentType.Space:
                preview += "  "
            elif seg.SegmentType == LinePatternSegmentType.Solid:
                preview += "━"
    except:
        preview = lpe.Name
    line_pattern_cache[pid] = preview.strip()
    return preview.strip()

from System.Windows.Media import Color, SolidColorBrush

def revit_color_to_brush(rvt_color):
    """Convert Revit color to WPF SolidColorBrush (IronPython-compatible)."""
    if not rvt_color or not rvt_color.IsValid:
        c = Color()
        c.R = 200
        c.G = 200
        c.B = 200
        c.A = 255
        return SolidColorBrush(c)

    c = Color()
    c.R = int(rvt_color.Red)
    c.G = int(rvt_color.Green)
    c.B = int(rvt_color.Blue)
    c.A = 255
    return SolidColorBrush(c)


# ------------------ FilterInfo Class ------------------
class FilterInfo(INotifyPropertyChanged):
    def __init__(self, name, projColor, projWeight, projPatternId,
                 projFgPatternId, projFgColor, projBgPatternId, projBgColor,
                 cutColor, cutWeight, cutPatternId,
                 cutFgPatternId, cutFgColor, cutBgPatternId, cutBgColor,
                 halftone, transparency):

        self.Name = name

        # Projection Line
        self.ProjBrush = revit_color_to_brush(projColor)
        self.ProjWeight = projWeight
        self.ProjPattern = get_line_pattern_preview(projPatternId)

        # Projection Hatch
        self.ProjFg = get_fill_pattern_name(projFgPatternId)
        self.ProjFgBrush = revit_color_to_brush(projFgColor)
        self.ProjBg = get_fill_pattern_name(projBgPatternId)
        self.ProjBgBrush = revit_color_to_brush(projBgColor)

        # Cut Line
        self.CutBrush = revit_color_to_brush(cutColor)
        self.CutWeight = cutWeight
        self.CutPattern = get_line_pattern_preview(cutPatternId)

        # Cut Hatch
        self.CutFg = get_fill_pattern_name(cutFgPatternId)
        self.CutFgBrush = revit_color_to_brush(cutFgColor)
        self.CutBg = get_fill_pattern_name(cutBgPatternId)
        self.CutBgBrush = revit_color_to_brush(cutBgColor)

        # Halftone / Transparency
        self.Halftone = halftone
        self.Transparency = transparency

    # Dummy INotifyPropertyChanged methods
    def add_PropertyChanged(self, handler): pass
    def remove_PropertyChanged(self, handler): pass

# ------------------ Collect Filters ------------------
try:
    applied_filters = active_view.GetFilters()
except:
    forms.alert("This view does not support VG Overrides.", exitscript=True)

if not applied_filters:
    forms.alert("No filters applied.", exitscript=True)

filter_map = {}
filter_data = ObservableCollection[FilterInfo]()

for fid in applied_filters:
    f = doc.GetElement(fid)
    ovr = active_view.GetFilterOverrides(fid)

    item = FilterInfo(
        f.Name,
        ovr.ProjectionLineColor, ovr.ProjectionLineWeight, ovr.ProjectionLinePatternId,
        ovr.SurfaceForegroundPatternId, ovr.SurfaceForegroundPatternColor,
        ovr.SurfaceBackgroundPatternId, ovr.SurfaceBackgroundPatternColor,
        ovr.CutLineColor, ovr.CutLineWeight, ovr.CutLinePatternId,
        ovr.CutForegroundPatternId, ovr.CutForegroundPatternColor,
        ovr.CutBackgroundPatternId, ovr.CutBackgroundPatternColor,
        ovr.Halftone,
        ovr.Transparency
    )

    filter_data.Add(item)
    filter_map[f.Name] = (fid, ovr)

# ------------------ Load XAML ------------------
xaml_path = os.path.join(os.path.dirname(__file__), "TransferVG.xaml")
with FileStream(xaml_path, FileMode.Open) as f:
    window = XamlReader.Load(f)

window.FindName("filterList").ItemsSource = filter_data

# ------------------ Buttons ------------------
def on_ok(sender, args):
    selected = [i.Name for i in window.FindName("filterList").SelectedItems]
    window.Tag = selected
    window.Close()

def on_cancel(sender, args):
    window.Tag = None
    window.Close()

window.FindName("okBtn").Click += on_ok
window.FindName("cancelBtn").Click += on_cancel

window.ShowDialog()
selected_filters = window.Tag
if not selected_filters:
    sys.exit()

# ------------------ Select Target Templates ------------------
all_views = DB.FilteredElementCollector(doc).OfClass(DB.View).ToElements()
template_ids_in_use = {v.ViewTemplateId for v in all_views if v.ViewTemplateId != DB.ElementId.InvalidElementId}
used_templates = [doc.GetElement(tid) for tid in template_ids_in_use]

if not used_templates:
    forms.alert("No view templates currently in use.", exitscript=True)

templates = forms.SelectFromList.show(
    used_templates, multiselect=True, title='Select In-Use View Templates', name_attr='Name'
)
if not templates:
    sys.exit()

# ------------------ Apply Overrides ------------------
def copy_overrides(src_override):
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
