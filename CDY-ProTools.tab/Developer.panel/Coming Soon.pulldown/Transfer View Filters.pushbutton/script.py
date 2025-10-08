# -*- coding: utf-8 -*-
__title__ = "Transfer View Filters v5.2"
__doc__ = "Live preview: Projection/Cut line + weight + pattern, hatch FG/BG + color, Halftone, Transparency"

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
from System.Windows.Media import SolidColorBrush, Color, DoubleCollection
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
        return "No Override"
    if pid in fill_pattern_cache:
        return fill_pattern_cache[pid]
    el = doc.GetElement(pid)
    name = el.Name if el else "No Override"
    fill_pattern_cache[pid] = name
    return name

def get_line_pattern_name(pid):
    if not pid or pid == ElementId.InvalidElementId:
        return "No Override"
    if pid in line_pattern_cache:
        return line_pattern_cache[pid]
    el = doc.GetElement(pid)
    name = el.Name if el else "No Override"
    line_pattern_cache[pid] = name
    return name

def get_dash_array(pid):
    """Return WPF-compatible dash array for a Revit LinePatternElement"""
    if not pid or pid == ElementId.InvalidElementId:
        return None
    lpe = doc.GetElement(pid)
    if not lpe:
        return None
    dash = DoubleCollection()
    try:
        for seg in lpe.GetLinePattern().Segments:
            if seg.SegmentType == LinePatternSegmentType.Dash:
                dash.Add(seg.Length)
            elif seg.SegmentType == LinePatternSegmentType.Dot:
                dash.Add(0.0)
                dash.Add(seg.Length)
    except:
        return None
    return dash if len(dash) else None

from System.Windows.Media import SolidColorBrush, Color

def revit_color_to_brush(c):
    """Convert a Revit color to a WPF SolidColorBrush in IronPython."""
    if not c or not c.IsValid:
        # fallback light gray
        col = Color.FromArgb(255, 200, 200, 200)
    else:
        col = Color.FromArgb(255, int(c.Red), int(c.Green), int(c.Blue))
    return SolidColorBrush(col)

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
        self.ProjWeight = projWeight if projWeight > 0 else 1
        self.ProjDashArray = get_dash_array(projPatternId)
        self.ProjPatternText = get_line_pattern_name(projPatternId)

        # Projection Hatch
        self.ProjFg = get_fill_pattern_name(projFgPatternId)
        self.ProjFgBrush = revit_color_to_brush(projFgColor)
        self.ProjBg = get_fill_pattern_name(projBgPatternId)
        self.ProjBgBrush = revit_color_to_brush(projBgColor)

        # Cut Line
        self.CutBrush = revit_color_to_brush(cutColor)
        self.CutWeight = cutWeight if cutWeight > 0 else 1
        self.CutDashArray = get_dash_array(cutPatternId)
        self.CutPatternText = get_line_pattern_name(cutPatternId)

        # Cut Hatch
        self.CutFg = get_fill_pattern_name(cutFgPatternId)
        self.CutFgBrush = revit_color_to_brush(cutFgColor)
        self.CutBg = get_fill_pattern_name(cutBgPatternId)
        self.CutBgBrush = revit_color_to_brush(cutBgColor)

        # Halftone / Transparency
        self.Halftone = halftone
        self.Transparency = transparency

    # Dummy INotifyPropertyChanged
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

    # Projection line
    try:
        ovr.SetProjectionLineColor(src_override.ProjectionLineColor)
        ovr.SetProjectionLineWeight(src_override.ProjectionLineWeight)
        ovr.SetProjectionLinePatternId(src_override.ProjectionLinePatternId)
    except:
        pass

    # Cut line
    try:
        ovr.SetCutLineColor(src_override.CutLineColor)
        ovr.SetCutLineWeight(src_override.CutLineWeight)
        ovr.SetCutLinePatternId(src_override.CutLinePatternId)
    except:
        pass

    # Surface hatch
    try:
        ovr.SetSurfaceForegroundPatternColor(src_override.SurfaceForegroundPatternColor)
        ovr.SetSurfaceForegroundPatternId(src_override.SurfaceForegroundPatternId)
        ovr.SetSurfaceBackgroundPatternColor(src_override.SurfaceBackgroundPatternColor)
        ovr.SetSurfaceBackgroundPatternId(src_override.SurfaceBackgroundPatternId)
    except:
        pass

    # Halftone / Transparency
    try:
        ovr.SetHalftone(src_override.Halftone)
        ovr.SetSurfaceTransparency(src_override.Transparency)
    except:
        pass

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
