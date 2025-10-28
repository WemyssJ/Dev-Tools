# -*- coding: utf-8 -*-
__title__ = "Transfer View Filters"
__doc__ = "Live preview: Projection/Cut line + weight + pattern, hatch FG/BG + color, Halftone, Transparency, Enable, Visibility"

import clr, sys, os, traceback
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
from System import Uri
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption

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

def revit_color_to_brush(c):
    """Convert a Revit color to a WPF SolidColorBrush safely"""
    from System.Windows.Media import Color as MediaColor, SolidColorBrush
    try:
        if not c or not c.IsValid:
            return SolidColorBrush(MediaColor.FromRgb(200, 200, 200))
        return SolidColorBrush(MediaColor.FromRgb(int(c.Red), int(c.Green), int(c.Blue)))
    except:
        return SolidColorBrush(MediaColor.FromRgb(200, 200, 200))

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

# ------------------ FilterInfo Class ------------------
class FilterInfo(INotifyPropertyChanged):
    def __init__(self, name, enabled, visible,
                 projColor, projWeight, projPatternId,
                 projFgPatternId, projFgColor, projBgPatternId, projBgColor,
                 cutColor, cutWeight, cutPatternId,
                 cutFgPatternId, cutFgColor, cutBgPatternId, cutBgColor,
                 halftone, transparency):

        self.Name = name
        self.Enabled = True if enabled else False
        self.Visible = True if visible else False

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
    enabled = get_filter_enabled(active_view, fid)
    visible = get_filter_visible(active_view, fid)

    item = FilterInfo(
        f.Name, enabled, visible,
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
    


def action_copy_viewtemplates():
    """Copy selected view templates to other open Revit models."""
    try:
        selected_viewtemplates = forms.select_viewtemplates(doc=revit.doc)
        if not selected_viewtemplates:
            forms.alert("No view templates selected.", exitscript=False)
            return

        dest_docs = forms.select_open_docs(title='Select Destination Documents')
        if not dest_docs:
            return

        for ddoc in dest_docs:
            t = DB.Transaction(ddoc, "Copy View Templates")
            t.Start()
            try:
                revit.create.copy_viewtemplates(
                    selected_viewtemplates,
                    src_doc=revit.doc,
                    dest_doc=ddoc
                )
                t.Commit()
            except Exception, e:
                t.RollBack()
                forms.alert(
                    "⚠️ Failed to copy templates to document '{}':\n{}".format(ddoc.Title, e),
                    title="Error"
                )

        forms.alert(
            "✅ {} view template(s) copied to {} document(s).".format(
                len(selected_viewtemplates), len(dest_docs)
            ),
            title="Copy Complete"
            
        )

        window.Close()

    except Exception, e:
        forms.alert("⚠️ Error copying view templates:\n\n{}".format(e), title="Error")
        window.Close()








        
# ------------------ Load XAML ------------------
xaml_path = os.path.join(os.path.dirname(__file__), "TransferVG.xaml")
with FileStream(xaml_path, FileMode.Open) as f:
    window = XamlReader.Load(f)

window.FindName("filterList").ItemsSource = filter_data

icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
if not os.path.exists(icon_path):
    print("⚠️ icon.png not found in script folder.")

bmp = BitmapImage()
bmp.BeginInit()
bmp.UriSource = Uri(icon_path)
bmp.CacheOption = BitmapCacheOption.OnLoad
bmp.EndInit()
window.FindName("headerIcon").Source = bmp

def on_ok(sender, args):
    selected = [i.Name for i in window.FindName("filterList").SelectedItems]
    window.Tag = selected
    window.Close()

def on_cancel(sender, args):
    window.Tag = None
    window.Close()

window.FindName("okBtn").Click += on_ok
window.FindName("cancelBtn").Click += on_cancel


btnCopyTemplates = window.FindName("btnCopyTemplates")
btnCopyTemplates.Click += lambda sender, args: action_copy_viewtemplates()

ok_button = window.FindName("okBtn")
filter_list = window.FindName("filterList")
ok_button.IsEnabled = False

def on_selection_changed(sender, args):
    ok_button.IsEnabled = filter_list.SelectedItems.Count > 0
filter_list.SelectionChanged += on_selection_changed

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

# ------------------ Copy Overrides Function ------------------
def copy_overrides(fid, src_view, dest_view):
    """Copy graphic overrides for a given filter ID between views/templates."""
    src_ovr = src_view.GetFilterOverrides(fid)
    ovr = OverrideGraphicSettings()

    def safe_call(label, func):
        try:
            func()
        except Exception as e:
            print("⚠️ {} failed: {}".format(label, e))

    safe_call("Projection line", lambda: (
        ovr.SetProjectionLineColor(src_ovr.ProjectionLineColor),
        ovr.SetProjectionLineWeight(src_ovr.ProjectionLineWeight),
        ovr.SetProjectionLinePatternId(src_ovr.ProjectionLinePatternId)
    ))

    safe_call("Cut line", lambda: (
        ovr.SetCutLineColor(src_ovr.CutLineColor),
        ovr.SetCutLineWeight(src_ovr.CutLineWeight),
        ovr.SetCutLinePatternId(src_ovr.CutLinePatternId)
    ))

    safe_call("Surface hatch", lambda: (
        ovr.SetSurfaceForegroundPatternColor(src_ovr.SurfaceForegroundPatternColor),
        ovr.SetSurfaceForegroundPatternId(src_ovr.SurfaceForegroundPatternId),
        ovr.SetSurfaceBackgroundPatternColor(src_ovr.SurfaceBackgroundPatternColor),
        ovr.SetSurfaceBackgroundPatternId(src_ovr.SurfaceBackgroundPatternId)
    ))

    safe_call("Cut hatch", lambda: (
        hasattr(ovr, "SetCutForegroundPatternColor") and ovr.SetCutForegroundPatternColor(src_ovr.CutForegroundPatternColor),
        hasattr(ovr, "SetCutForegroundPatternId") and ovr.SetCutForegroundPatternId(src_ovr.CutForegroundPatternId),
        hasattr(ovr, "SetCutBackgroundPatternColor") and ovr.SetCutBackgroundPatternColor(src_ovr.CutBackgroundPatternColor),
        hasattr(ovr, "SetCutBackgroundPatternId") and ovr.SetCutBackgroundPatternId(src_ovr.CutBackgroundPatternId)
    ))

    safe_call("Halftone", lambda: ovr.SetHalftone(src_ovr.Halftone))

    # Transparency compatibility (Revit 2024 vs 2025+)
    if hasattr(ovr, "SetSurfaceTransparency"):
        safe_call("Transparency (2024)", lambda: ovr.SetSurfaceTransparency(src_ovr.Transparency))
    elif hasattr(ovr, "SetTransparency"):
        safe_call("Transparency (2025+)", lambda: ovr.SetTransparency(src_ovr.Transparency))
    else:
        print("⚠️ No transparency method found on OverrideGraphicSettings")

    # Enable / Visibility
    try:
        enabled = get_filter_enabled(src_view, fid)
        visible = get_filter_visible(src_view, fid)
        if hasattr(dest_view, "SetIsFilterEnabled"):
            dest_view.SetIsFilterEnabled(fid, enabled)
        elif hasattr(dest_view, "SetFilterEnabled"):
            dest_view.SetFilterEnabled(fid, enabled)
        if hasattr(dest_view, "SetFilterVisibility"):
            dest_view.SetFilterVisibility(fid, visible)
        elif hasattr(dest_view, "SetFilterVisible"):
            dest_view.SetFilterVisible(fid, visible)
    except Exception as e:
        print("⚠️ Enable/Visibility override failed:", e)

    return ovr

# ------------------ Apply to Selected Templates ------------------
failed = []
t = DB.Transaction(doc, 'Apply View Filters to Templates')
t.Start()
for fname in selected_filters:
    fid, existing_override = filter_map[fname]
    for template in templates:
        try:
            if not template.IsFilterApplied(fid):
                template.AddFilter(fid)
            new_override = copy_overrides(fid, active_view, template)
            template.SetFilterOverrides(fid, new_override)
        except Exception as e:
            msg = "⚠️ Failed to apply filter '{}' to template '{}': {}".format(fname, template.Name, e)
            print(msg)
            failed.append(msg)
t.Commit()



# ------------------ Result ------------------
source_template_id = active_view.ViewTemplateId
if source_template_id != DB.ElementId.InvalidElementId:
    source_name = doc.GetElement(source_template_id).Name
else:
    source_name = active_view.Name

target_names = ", ".join([v.Name for v in templates])
msg = "Selected filters successfully applied from {} to {}!".format(source_name, target_names)
if failed:
    msg += "\n\nSome filters failed:\n" + "\n".join(failed[:5]) + ("\n..." if len(failed) > 5 else "")
forms.alert(msg, title="Done")
