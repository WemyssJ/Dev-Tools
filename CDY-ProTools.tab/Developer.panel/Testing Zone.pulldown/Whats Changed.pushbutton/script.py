# -*- coding: utf-8 -*-
"""
What's Changed? Reporter for Revit Models
Now supports exporting from linked models. Unloaded links are shown but disabled.
"""

import os, json, math, clr, re, codecs
from System import Environment
clr.AddReference("System")
from pyrevit import revit, DB, script, forms
from System.IO import FileStream, FileMode, FileAccess
from System.Windows.Input import MouseEventHandler
from System.Windows.Documents import Run
from System.Windows.Media import Brushes, SolidColorBrush, Color
from System.Windows.Markup import XamlReader
from System.Windows import Visibility
from System.Windows.Forms import FolderBrowserDialog, OpenFileDialog, ColorDialog, DialogResult
from System.Windows.Controls import ComboBoxItem
from System import Uri
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption

output = script.get_output()
doc = revit.doc
uidoc = revit.uidoc

PARAMS_TO_CHECK = ["Type Name", "Type", "Height", "Perimeter", "Length", "Width", "Depth"]


# ---------------- Helper Functions ----------------
def make_color(r, g, b):
    return DB.Color(r, g, b)

def make_override(rgb):
    col = make_color(*rgb)
    ovr = DB.OverrideGraphicSettings()
    ovr.SetProjectionLineColor(col)
    ovr.SetSurfaceForegroundPatternColor(col)
    ovr.SetSurfaceForegroundPatternVisible(True)
    return ovr

def capture_model_state(doc):
    if not doc:
        return {}
    cats_to_include = [
        DB.BuiltInCategory.OST_Walls, DB.BuiltInCategory.OST_Floors, DB.BuiltInCategory.OST_Roofs,
        DB.BuiltInCategory.OST_Ceilings, DB.BuiltInCategory.OST_Columns, DB.BuiltInCategory.OST_StructuralColumns,
        DB.BuiltInCategory.OST_StructuralFraming, DB.BuiltInCategory.OST_StructuralFoundation,
        DB.BuiltInCategory.OST_Doors, DB.BuiltInCategory.OST_Windows, DB.BuiltInCategory.OST_GenericModel,
        DB.BuiltInCategory.OST_Furniture, DB.BuiltInCategory.OST_FurnitureSystems, DB.BuiltInCategory.OST_Casework,
        DB.BuiltInCategory.OST_MechanicalEquipment, DB.BuiltInCategory.OST_PipeCurves, DB.BuiltInCategory.OST_DuctCurves,
        DB.BuiltInCategory.OST_CableTray, DB.BuiltInCategory.OST_Conduit, DB.BuiltInCategory.OST_StructConnections,
        DB.BuiltInCategory.OST_Stairs, DB.BuiltInCategory.OST_Ramps, DB.BuiltInCategory.OST_Railings,
        DB.BuiltInCategory.OST_CurtainWallPanels, DB.BuiltInCategory.OST_CurtainWallMullions, DB.BuiltInCategory.OST_SpecialityEquipment
    ]
    all_data = {}
    for bic in cats_to_include:
        try:
            collector = DB.FilteredElementCollector(doc).OfCategory(bic).WhereElementIsNotElementType()
            for el in collector:
                try:
                    elid = str(el.Id.IntegerValue)
                    loc = getattr(el, "Location", None)
                    loc_data = None
                    try:
                        if hasattr(loc, "Point") and loc.Point:
                            p = loc.Point
                            loc_data = (p.X, p.Y, p.Z)
                        elif hasattr(loc, "Curve") and loc.Curve:
                            c = loc.Curve
                            loc_data = (c.GetEndPoint(0).X, c.GetEndPoint(0).Y, c.GetEndPoint(0).Z)
                    except:
                        loc_data = None

                    param_dict = {}
                    for pname in PARAMS_TO_CHECK:
                        try:
                            p = el.LookupParameter(pname)
                            if p and p.HasValue:
                                val = p.AsValueString() or p.AsString()
                                if val:
                                    param_dict[pname] = val
                        except:
                            continue

                    all_data[elid] = {"cat": el.Category.Name if el.Category else "", "loc": loc_data, "params": param_dict}
                except:
                    continue
        except:
            continue
    return all_data

def compare_states(prev_data, current_data):
    prev_ids, curr_ids = set(prev_data.keys()), set(current_data.keys())
    new_ids, deleted_ids = curr_ids - prev_ids, prev_ids - curr_ids
    common_ids = prev_ids & curr_ids
    moved_ids, param_changed_ids = [], []

    for eid in common_ids:
        prev_el, curr_el = prev_data[eid], current_data[eid]
        if prev_el.get("loc") and curr_el.get("loc"):
            try:
                dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(prev_el["loc"], curr_el["loc"])))
                if dist > 0.001:
                    moved_ids.append(eid)
            except:
                pass
        for pname in PARAMS_TO_CHECK:
            if pname in prev_el["params"] and pname in curr_el["params"]:
                if prev_el["params"][pname] != curr_el["params"][pname]:
                    param_changed_ids.append(eid)
                    break
    return new_ids, deleted_ids, moved_ids, param_changed_ids

def prepare_view(view3d, doc):
    view3d.DisplayStyle = DB.DisplayStyle(2)
    view3d.DetailLevel = DB.ViewDetailLevel.Fine
    for cat in doc.Settings.Categories:
        try:
            if cat.CategoryType != DB.CategoryType.Model or "Analytical" in cat.Name or "Annotation" in cat.Name:
                view3d.SetCategoryHidden(cat.Id, True)
        except:
            continue
    rvt_links_cat = DB.Category.GetCategory(doc, DB.BuiltInCategory.OST_RvtLinks)
    if rvt_links_cat:
        view3d.SetCategoryHidden(rvt_links_cat.Id, True)
    view3d.IsSectionBoxActive = True
    return view3d


# ---------------- UI ----------------
def show_ui(xaml_path):
    fs = FileStream(xaml_path, FileMode.Open, FileAccess.Read)
    window = XamlReader.Load(fs)
    fs.Close()

    # --- Load header icon (FIXED LOCATION) ---
    icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
    if os.path.exists(icon_path):
        try:
            bmp = BitmapImage()
            bmp.BeginInit()
            bmp.UriSource = Uri(icon_path)
            bmp.CacheOption = BitmapCacheOption.OnLoad
            bmp.EndInit()
            header_img = window.FindName("headerIcon")
            if header_img is not None:
                header_img.Source = bmp
        except:
            pass

    # --- UI Controls ---
    cancelBtn = window.FindName("cancelBtn")
    okBtn = window.FindName("okBtn")
    importToggle = window.FindName("importToggle")
    exportToggle = window.FindName("exportToggle")
    disciplineBox = window.FindName("disciplineBox")
    revisionBox = window.FindName("revisionBox")
    jobBox = window.FindName("jobBox")
    jobNumberBox = window.FindName("jobNumberBox")
    anticipatedFileName = window.FindName("anticipatedFileName")
    modelSourceBox = window.FindName("modelSourceBox")
    newRect = window.FindName("newRect")
    movedRect = window.FindName("movedRect")
    changedRect = window.FindName("changedRect")
    saveConfigBtn = window.FindName("saveConfigBtn")
    loadConfigBtn = window.FindName("loadConfigBtn")
    exportForm = window.FindName("exportForm")
    importForm = window.FindName("importForm")

    # (EVERYTHING BELOW THIS BLOCK REMAINS IDENTICAL TO YOUR ORIGINAL SCRIPT)
    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------

    # --- Auto-fill Job Info ---
    project_info = doc.ProjectInformation

    def get_param_value(el, param_name, fallback=""):
        try:
            p = el.LookupParameter(param_name)
            if p and p.HasValue:
                val = p.AsString()
                if val and val.strip():
                    return val.strip()
        except:
            pass
        return fallback

    craddys_job = get_param_value(project_info, "Craddys Job Number")
    project_number = get_param_value(project_info, "Project Number")
    job_name_default = get_param_value(project_info, "Project Name", fallback="TBC")

    parts = []
    if craddys_job:
        parts.append(craddys_job)
    if project_number:
        parts.append(project_number)

    job_number_default = "_".join(parts)
    jobBox.Text = job_name_default
    jobNumberBox.Text = job_number_default

    # --- Filename Preview & Hover ---
    def get_item_text(item, fallback=""):
        if item is None:
            return fallback
        try:
            return str(item.Content)
        except AttributeError:
            return str(item)

    def get_filename_parts():
        prefix = jobNumberBox.Text.strip() or "TBC_"
        job_name = jobBox.Text.strip() or "TBC"
        revision = revisionBox.Text.strip() or "P00"
        discipline = get_item_text(disciplineBox.SelectedItem, fallback="Discipline")
        model_name = get_item_text(modelSourceBox.SelectedItem, fallback="This Model")
        model_name_clean = model_name.replace(".rvt", "").replace(" (unloaded)", "")
        return {
            "prefix": prefix,
            "discipline": discipline,
            "job": job_name,
            "revision": revision,
            "model": model_name_clean
        }

    def update_filename_display(highlight=None, *args):
        parts = get_filename_parts()
        separator = "_"
        anticipatedFileName.Inlines.Clear()
        keys = ["prefix", "discipline", "job", "revision", "model"]
        for i, key in enumerate(keys):
            run = Run()
            run.Text = parts[key]
            if highlight == key:
                run.Foreground = Brushes.Red
            anticipatedFileName.Inlines.Add(run)
            if i < len(keys) - 1:
                anticipatedFileName.Inlines.Add(Run(separator))

    def attach_hover(ctrl, key):
        def enter(sender, e):
            update_filename_display(highlight=key)
        def leave(sender, e):
            update_filename_display(highlight=None)
        ctrl.MouseEnter += MouseEventHandler(enter)
        ctrl.MouseLeave += MouseEventHandler(leave)

    update_filename_display()
    attach_hover(jobNumberBox, "prefix")
    attach_hover(disciplineBox, "discipline")
    attach_hover(jobBox, "job")
    attach_hover(revisionBox, "revision")
    attach_hover(modelSourceBox, "model")

    jobNumberBox.TextChanged += update_filename_display
    jobBox.TextChanged += update_filename_display
    revisionBox.TextChanged += update_filename_display
    modelSourceBox.SelectionChanged += update_filename_display
    disciplineBox.SelectionChanged += update_filename_display

    # --- Discipline dropdown ---
    disciplineBox.Items.Clear()
    for d in ["Structures", "Architect", "M&E"]:
        disciplineBox.Items.Add(d)
    disciplineBox.SelectedIndex = 0

    # --- Model source dropdown ---
    modelSourceBox.Items.Clear()
    item_this = ComboBoxItem()
    item_this.Content = "This Model"
    item_this.IsEnabled = True
    modelSourceBox.Items.Add(item_this)

    link_instances = list(DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkInstance))
    seen = set()
    for link in link_instances:
        try:
            lname = link.Name
            if lname in seen:
                lname = "{} ({})".format(lname, link.Id.IntegerValue)
            seen.add(lname)
            try:
                linked_doc = link.GetLinkDocument()
            except:
                linked_doc = None
            ci = ComboBoxItem()
            if linked_doc:
                ci.Content = lname
                ci.IsEnabled = True
            else:
                ci.Content = lname + " (unloaded)"
                ci.IsEnabled = False
            modelSourceBox.Items.Add(ci)
        except:
            continue

    modelSourceBox.SelectedIndex = 0
    importToggle.IsChecked = True
    exportForm.Visibility = Visibility.Collapsed

    # --- UI Event Handlers ---
    def toggle_export(sender, e):
        exportForm.Visibility = Visibility.Visible
        importToggle.IsChecked = False
        importForm.Visibility = Visibility.Collapsed
        saveConfigBtn.Visibility = Visibility.Collapsed
        loadConfigBtn.Visibility = Visibility.Collapsed

    def toggle_import(sender, e):
        exportForm.Visibility = Visibility.Collapsed
        exportToggle.IsChecked = False
        importForm.Visibility = Visibility.Visible
        saveConfigBtn.Visibility = Visibility.Visible
        loadConfigBtn.Visibility = Visibility.Visible

    exportToggle.Checked += toggle_export
    importToggle.Checked += toggle_import

    colors = {"new": (0, 255, 0), "moved": (255, 165, 0), "changed": (0, 100, 255)}

    def pick_color(key, rect):
        dlg = ColorDialog()
        dlg.FullOpen = True
        if dlg.ShowDialog() == DialogResult.OK:
            val = dlg.Color
            colors[key] = (val.R, val.G, val.B)
            rect.Background = SolidColorBrush(Color.FromRgb(val.R, val.G, val.B))

    newRect.MouseLeftButtonDown += lambda s, e: pick_color("new", newRect)
    movedRect.MouseLeftButtonDown += lambda s, e: pick_color("moved", movedRect)
    changedRect.MouseLeftButtonDown += lambda s, e: pick_color("changed", changedRect)

    config_path = os.path.join(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                               "pyRevit", "WhatChangedColourConfig.json")

    def save_config(colors):
        colors_json = {}
        for k in colors:
            colors_json[k] = []
            for c in colors[k]:
                colors_json[k].append(int(c))
        folder = os.path.dirname(config_path)
        if not os.path.exists(folder):
            os.makedirs(folder)
        with codecs.open(config_path, 'w', 'utf-8') as f:
            json.dump(colors_json, f, indent=2)

    def load_config():
        if not os.path.exists(config_path):
            forms.alert("⚠️ No saved configuration found.", title="What's Changed?", ok=True)
            return None
        with codecs.open(config_path, 'r', 'utf-8') as f:
            colors_json = json.load(f)
        loaded_colors = {}
        for k in colors_json:
            loaded_colors[k] = tuple(colors_json[k])
        return loaded_colors

    saveConfigBtn.Click += lambda s, e: save_config(colors)

    def load_click(s, e):
        loaded = load_config()
        if loaded:
            for k in loaded:
                colors[k] = loaded[k]
            newRect.Background = SolidColorBrush(Color.FromRgb(*colors["new"]))
            movedRect.Background = SolidColorBrush(Color.FromRgb(*colors["moved"]))
            changedRect.Background = SolidColorBrush(Color.FromRgb(*colors["changed"]))

    loadConfigBtn.Click += load_click

    def cancel_click(sender, e):
        window.Tag = None
        window.Close()

    def ok_click(sender, args):
        selected_model = get_item_text(modelSourceBox.SelectedItem, fallback="This Model")
        dlg_type = "Export" if exportToggle.IsChecked else "Import"
        filename_parts = get_filename_parts()
        safe_model_name = re.sub(r'[<>:"/\\|?*]', '_', filename_parts["model"])
        prefix = "{}".format(filename_parts["prefix"])

        if dlg_type == "Export":
            dlg = FolderBrowserDialog()
            if dlg.ShowDialog() == DialogResult.OK:
                folder = dlg.SelectedPath
                filename = "{}{}_{}_{}_({}).json".format(
                    prefix,
                    filename_parts["discipline"],
                    filename_parts["job"],
                    filename_parts["revision"],
                    safe_model_name
                )
                dlg_file = os.path.join(folder, filename)
            else:
                return
        elif dlg_type == "Import":
            dlg = OpenFileDialog()
            dlg.Filter = "JSON Files|*.json"
            if dlg.ShowDialog() == DialogResult.OK:
                dlg_file = dlg.FileName
            else:
                return

        window.Tag = (dlg_type, dlg_file, colors["new"], colors["moved"], colors["changed"], selected_model)
        window.Close()

    cancelBtn.Click += cancel_click
    okBtn.Click += ok_click

    window.ShowDialog()
    return getattr(window, "Tag", None)


# ---------------- MAIN ----------------
xaml_path = os.path.join(script.get_script_path(), "whats_changed_ui.xaml")
result = show_ui(xaml_path)
if not result:
    script.exit()

action, file_path, new_col, moved_col, changed_col, model_choice = result
output.print_md("**Action:** {} | **File:** {}".format(action, file_path))


# --- LINKED DOCUMENT HANDLING ---
target_doc = doc
if action == "Export" and model_choice and model_choice != "This Model":
    base_choice = model_choice.replace(" (unloaded)", "")
    link_instance = None
    for l in DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkInstance):
        lname_check = l.Name
        if lname_check == base_choice or "{} ({})".format(l.Name, l.Id.IntegerValue) == base_choice:
            link_instance = l
            break
    if link_instance:
        try:
            link_doc = link_instance.GetLinkDocument()
        except:
            link_doc = None
        if link_doc:
            target_doc = link_doc
        else:
            forms.alert("⚠️ The selected link '{}' is not loaded or accessible.".format(base_choice), exitscript=True)

# --- Export ---
if action == "Export":
    model_state = capture_model_state(target_doc)
    with codecs.open(file_path, 'w', 'utf-8') as f:
        f.write(json.dumps(model_state, ensure_ascii=False, indent=2))
    output.print_md("✅ Snapshot exported to `{}`".format(file_path))
    script.exit()

# --- Import ---
elif action == "Import":
    if not os.path.exists(file_path):
        forms.alert("⚠️ File not found: `{}`".format(file_path), exitscript=True)
    with codecs.open(file_path, 'r', 'utf-8') as f:
        prev_data = json.load(f)

current_data = capture_model_state(doc)
new_ids, deleted_ids, moved_ids, param_changed_ids = compare_states(prev_data, current_data)

if not (new_ids or moved_ids or param_changed_ids):
    forms.alert("✅ No changes detected between current model and snapshot.", exitscript=True)

# --- 3D View ---
view_family_type = None
for vft in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType):
    if vft.ViewFamily == DB.ViewFamily.ThreeDimensional:
        view_family_type = vft
        break

with revit.Transaction("Create/Reuse What's Changed 3D View"):
    view3d = None
    for v in DB.FilteredElementCollector(doc).OfClass(DB.View3D).ToElements():
        if v.Name == "What's Changed":
            view3d = v
            break
    if view3d is None:
        view3d = DB.View3D.CreateIsometric(doc, view_family_type.Id)
        view3d.Name = "What's Changed"
    view3d = prepare_view(view3d, doc)

# --- Apply Overrides ---
ovr_new = make_override(new_col)
ovr_moved = make_override(moved_col)
ovr_changed = make_override(changed_col)

with revit.Transaction("Apply Overrides"):
    for eid in new_ids:
        try:
            view3d.SetElementOverrides(DB.ElementId(int(eid)), ovr_new)
        except:
            continue
    for eid in moved_ids:
        try:
            view3d.SetElementOverrides(DB.ElementId(int(eid)), ovr_moved)
        except:
            continue
    for eid in param_changed_ids:
        try:
            view3d.SetElementOverrides(DB.ElementId(int(eid)), ovr_changed)
        except:
            continue

uidoc.ActiveView = view3d

def rgb_block(rgb, size=15):
    r, g, b = rgb
    return '<span style="display:inline-block;width:{}px;height:{}px;background-color:rgb({},{},{});margin-right:5px;border:1px solid #000;"></span>'.format(
        size, size, r, g, b)

output.print_md("### ✅ What's Changed Report")
output.print_html("<b>New elements:</b> {} {}".format(rgb_block(new_col), len(new_ids)))
output.print_html("<b>Moved elements:</b> {} {}".format(rgb_block(moved_col), len(moved_ids)))
output.print_html("<b>Parameter changes:</b> {} {}".format(rgb_block(changed_col), len(param_changed_ids)))
deleted_ids = set(prev_data.keys()) - set(current_data.keys())
output.print_md("**Deleted elements:** {} ❌".format(len(deleted_ids)))
