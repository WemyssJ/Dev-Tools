# -*- coding: utf-8 -*-
__title__ = "Transfer View Filters v2.3"
__doc__ = "White/light theme, working color previews & RGB tooltips, multi-select, Revit 2024"

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
from System.Windows.Media import SolidColorBrush, Color, Colors
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
                preview += "- "
            elif seg.SegmentType == LinePatternSegmentType.Dot:
                preview += "· "
            elif seg.SegmentType == LinePatternSegmentType.Space:
                preview += "  "
            elif seg.SegmentType == LinePatternSegmentType.Solid:
                preview += "─"
    except:
        preview = lpe.Name
    line_pattern_cache[pid] = preview.strip()
    return preview.strip()

from System.Windows.Media import SolidColorBrush, Color, Colors

def revit_color_to_brush(c):
    if not c or not c.IsValid:
        return SolidColorBrush(Colors.LightGray)
    r = max(0, min(255, int(c.Red)))
    g = max(0, min(255, int(c.Green)))
    b = max(0, min(255, int(c.Blue)))
    # Correct WPF Color creation
    wpf_color = Color.FromRgb(r, g, b)
    return SolidColorBrush(wpf_color)

def revit_color_to_text(c):
    if not c or not c.IsValid:
        return "Invalid"
    return "R:{} G:{} B:{}".format(int(c.Red), int(c.Green), int(c.Blue))

# ------------------ Data Class ------------------
class FilterInfo(INotifyPropertyChanged):
    def __init__(self, name, projColor, cutColor, projPattern, cutPattern, surfFg, cutFg, transparency, halftone):
        self.Name = name
        self._projBrush = revit_color_to_brush(projColor)
        self._cutBrush = revit_color_to_brush(cutColor)
        self._projColorText = revit_color_to_text(projColor)
        self._cutColorText = revit_color_to_text(cutColor)
        self.ProjPattern = projPattern
        self.CutPattern = cutPattern
        self.SurfFg = surfFg
        self.CutFg = cutFg
        self.Transparency = transparency
        self.Halftone = halftone

    @property
    def ProjBrush(self):
        return self._projBrush

    @property
    def CutBrush(self):
        return self._cutBrush

    @property
    def ProjColorText(self):
        return self._projColorText

    @property
    def CutColorText(self):
        return self._cutColorText

    def add_PropertyChanged(self, handler): pass
    def remove_PropertyChanged(self, handler): pass

# ------------------ Collect Filters ------------------
try:
    applied_filters = active_view.GetFilters()
except:
    forms.alert("Active view does not support VG overrides. Open a Plan, Section, or 3D view.", exitscript=True)

if not applied_filters:
    forms.alert("No filters applied to the active view.", exitscript=True)

filter_map = {}
filter_data = ObservableCollection[FilterInfo]()

for fid in applied_filters:
    f = doc.GetElement(fid)
    ovr = active_view.GetFilterOverrides(fid)
    item = FilterInfo(
        f.Name,
        ovr.ProjectionLineColor,
        ovr.CutLineColor,
        get_line_pattern_preview(ovr.ProjectionLinePatternId),
        get_line_pattern_preview(ovr.CutLinePatternId),
        get_fill_pattern_name(ovr.SurfaceForegroundPatternId),
        get_fill_pattern_name(ovr.CutForegroundPatternId),
        ovr.Transparency,
        ovr.Halftone
    )
    filter_data.Add(item)
    filter_map[f.Name] = (fid, ovr)

# ------------------ Load XAML ------------------
xaml_path = os.path.join(os.path.dirname(__file__), "TransferVG.XAML")
with FileStream(xaml_path, FileMode.Open) as fs:
    window = XamlReader.Load(fs)

window.FindName("filterList").ItemsSource = filter_data

# ------------------ Button Handlers ------------------
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

# ------------------ Collect View Templates ------------------
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
