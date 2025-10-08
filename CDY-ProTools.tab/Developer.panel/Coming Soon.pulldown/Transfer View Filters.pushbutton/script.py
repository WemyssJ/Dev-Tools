# -*- coding: utf-8 -*-
__title__ = "Transfer View Filters v5.8"
__doc__ = "Live preview: Projection/Cut line + weight + pattern, hatch FG/BG + color, Halftone, Transparency, Enable, Visibility"

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

def revit_color_to_brush(c):
    from System.Windows.Media import SolidColorBrush, Color as MediaColor
    try:
        if not c or not c.IsValid:
            return SolidColorBrush(MediaColor.FromRgb(200,200,200))
        return SolidColorBrush(MediaColor.FromRgb(c.Red, c.Green, c.Blue))
    except:
        return SolidColorBrush(MediaColor.FromRgb(200,200,200))

def get_filter_enabled(view, fid):
    try:
        if hasattr(view, "GetIsFilterEnabled"):
            return view.GetIsFilterEnabled(fid)
        elif hasattr(view, "GetFilterEnabled"):
            return view.GetFilterEnabled(fid)
        else:
            return True
    except:
        return True

def get_filter_visible(view, fid):
    try:
        if hasattr(view, "GetFilterVisibility"):
            return view.GetFilterVisibility(fid)
        elif hasattr(view, "GetFilterVisible"):
            return view.GetFilterVisible(fid)
        else:
            return True
    except:
        return True

# ------------------ Revit Options Lists ------------------
all_line_patterns = {lp.Id: lp.Name for lp in DB.FilteredElementCollector(doc).OfClass(DB.LinePatternElement)}
line_pattern_names = list(all_line_patterns.values())
all_fill_patterns = {fp.Id: fp.Name for fp in DB.FilteredElementCollector(doc).OfClass(DB.FillPatternElement)}
fill_pattern_names = list(all_fill_patterns.values())
transparency_levels = list(range(0,101,10))

# ------------------ FilterInfo Class ------------------
class FilterInfo(INotifyPropertyChanged):
    def __init__(self, name, enabled, visible,
                 projColor, projWeight, projPatternId,
                 projFgPatternId, projFgColor, projBgPatternId, projBgColor,
                 cutColor, cutWeight, cutPatternId,
                 cutFgPatternId, cutFgColor, cutBgPatternId, cutBgColor,
                 halftone, transparency):
        self.Name = name
        self.Enabled = enabled
        self.Visible = visible

        self.ProjBrush = revit_color_to_brush(projColor)
        self.ProjWeight = projWeight if projWeight>0 else 1
        self.ProjDashArray = get_dash_array(projPatternId)
        self.ProjPatternText = get_line_pattern_name(projPatternId)
        self.LinePatterns = line_pattern_names

        self.ProjFg = get_fill_pattern_name(projFgPatternId)
        self.ProjFgBrush = revit_color_to_brush(projFgColor)
        self.ProjBg = get_fill_pattern_name(projBgPatternId)
        self.ProjBgBrush = revit_color_to_brush(projBgColor)
        self.FillPatterns = fill_pattern_names

        self.CutBrush = revit_color_to_brush(cutColor)
        self.CutWeight = cutWeight if cutWeight>0 else 1
        self.CutDashArray = get_dash_array(cutPatternId)
        self.CutPatternText = get_line_pattern_name(cutPatternId)

        self.CutFg = get_fill_pattern_name(cutFgPatternId)
        self.CutFgBrush = revit_color_to_brush(cutFgColor)
        self.CutBg = get_fill_pattern_name(cutBgPatternId)
        self.CutBgBrush = revit_color_to_brush(cutBgColor)

        self.Halftone = halftone
        self.Transparency = transparency
        self.TransparencyLevels = transparency_levels

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
    fi = FilterInfo(
        f.Name, get_filter_enabled(active_view,fid), get_filter_visible(active_view,fid),
        ovr.ProjectionLineColor, ovr.ProjectionLineWeight, ovr.ProjectionLinePatternId,
        ovr.SurfaceForegroundPatternId, ovr.SurfaceForegroundPatternColor,
        ovr.SurfaceBackgroundPatternId, ovr.SurfaceBackgroundPatternColor,
        ovr.CutLineColor, ovr.CutLineWeight, ovr.CutLinePatternId,
        ovr.CutForegroundPatternId, ovr.CutForegroundPatternColor,
        ovr.CutBackgroundPatternId, ovr.CutBackgroundPatternColor,
        ovr.Halftone,
        ovr.Transparency
    )
    filter_data.Add(fi)
    filter_map[f.Name] = (fid, ovr)

# ------------------ Load XAML ------------------
xaml_path = os.path.join(os.path.dirname(__file__),"TransferVG.xaml")
with FileStream(xaml_path, FileMode.Open) as f:
    window = XamlReader.Load(f)

window.FindName("filterList").ItemsSource = filter_data

# ------------------ Copy Overrides Function ------------------
def copy_overrides_from_filterinfo(fid, fi, dest_view):
    ovr = OverrideGraphicSettings()

    # Projection line
    ovr.SetProjectionLineColor(Color(fi.ProjBrush.Color.R,fi.ProjBrush.Color.G,fi.ProjBrush.Color.B))
    ovr.SetProjectionLineWeight(fi.ProjWeight)
    pattern_id = next((k for k,v in all_line_patterns.items() if v==fi.ProjPatternText), ElementId.InvalidElementId)
    ovr.SetProjectionLinePatternId(pattern_id)

    # Cut line
    ovr.SetCutLineColor(Color(fi.CutBrush.Color.R,fi.CutBrush.Color.G,fi.CutBrush.Color.B))
    ovr.SetCutLineWeight(fi.CutWeight)
    pattern_id = next((k for k,v in all_line_patterns.items() if v==fi.CutPatternText), ElementId.InvalidElementId)
    ovr.SetCutLinePatternId(pattern_id)

    # Surface hatch
    fg_id = next((k for k,v in all_fill_patterns.items() if v==fi.ProjFg), ElementId.InvalidElementId)
    bg_id = next((k for k,v in all_fill_patterns.items() if v==fi.ProjBg), ElementId.InvalidElementId)
    ovr.SetSurfaceForegroundPatternId(fg_id)
    ovr.SetSurfaceBackgroundPatternId(bg_id)
    ovr.SetSurfaceForegroundPatternColor(Color(fi.ProjFgBrush.Color.R,fi.ProjFgBrush.Color.G,fi.ProjFgBrush.Color.B))
    ovr.SetSurfaceBackgroundPatternColor(Color(fi.ProjBgBrush.Color.R,fi.ProjBgBrush.Color.G,fi.ProjBgBrush.Color.B))

    # Halftone / Transparency
    ovr.SetHalftone(fi.Halftone)
    ovr.SetSurfaceTransparency(fi.Transparency)

    # Enable + Visibility
    if hasattr(dest_view,"SetIsFilterEnabled"):
        dest_view.SetIsFilterEnabled(fid, fi.Enabled)
    elif hasattr(dest_view,"SetFilterEnabled"):
        dest_view.SetFilterEnabled(fid, fi.Enabled)

    if hasattr(dest_view,"SetFilterVisibility"):
        dest_view.SetFilterVisibility(fid, fi.Visible)
    elif hasattr(dest_view,"SetFilterVisible"):
        dest_view.SetFilterVisible(fid, fi.Visible)

    return ovr

# ------------------ Button Handlers ------------------
def on_ok(sender,args):
    selected = [i.Name for i in window.FindName("filterList").SelectedItems]
    window.Tag = selected
    window.Close()

def on_cancel(sender,args):
    window.Tag = None
    window.Close()

def on_apply_current(sender,args):
    template_id = active_view.ViewTemplateId
    if template_id==ElementId.InvalidElementId:
        forms.alert("Active view does not have a view template.", exitscript=True)
        return
    template = doc.GetElement(template_id)
    t = DB.Transaction(doc,"Apply Filter Changes to Current Template")
    t.Start()
    for fi in filter_data:
        fid,_ = filter_map[fi.Name]
        if not template.IsFilterApplied(fid):
            template.AddFilter(fid)
        new_ovr = copy_overrides_from_filterinfo(fid,fi,template)
        template.SetFilterOverrides(fid,new_ovr)
    t.Commit()
    forms.alert("Changes applied to current view template: {}".format(template.Name), title="Done")

# ------------------ Hook Buttons ------------------
window.FindName("okBtn").Click += on_ok
window.FindName("cancelBtn").Click += on_cancel
window.FindName("applyCurrentBtn").Click += on_apply_current

# ------------------ Show Window ------------------
window.ShowDialog()

selected_filters = window.Tag
if not selected_filters:
    sys.exit()

# ------------------ Select Target Templates ------------------
all_views = DB.FilteredElementCollector(doc).OfClass(DB.View).ToElements()
template_ids_in_use = {v.ViewTemplateId for v in all_views if v.ViewTemplateId!=ElementId.InvalidElementId}
used_templates = [doc.GetElement(tid) for tid in template_ids_in_use]
if not used_templates:
    forms.alert("No view templates currently in use.", exitscript=True)

templates = forms.SelectFromList.show(used_templates, multiselect=True, title="Select In-Use View Templates", name_attr="Name")
if not templates:
    sys.exit()

# ------------------ Apply to Selected Templates ------------------
t = DB.Transaction(doc,"Apply View Filters to Templates")
t.Start()
for fname in selected_filters:
    fid,_ = filter_map[fname]
    for template in templates:
        if not template.IsFilterApplied(fid):
            template.AddFilter(fid)
        fi = next(f for f in filter_data if f.Name==fname)
        new_override = copy_overrides_from_filterinfo(fid,fi,template)
        template.SetFilterOverrides(fid,new_override)
t.Commit()

source_template_id = active_view.ViewTemplateId
source_name = doc.GetElement(source_template_id).Name if source_template_id!=ElementId.InvalidElementId else active_view.Name
target_names = ", ".join([v.Name for v in templates])
forms.alert("Selected filters successfully applied from {} to {}!".format(source_name,target_names), title="Done")
