# -*- coding: utf-8 -*-
"""
What's Changed? Reporter for Revit Models
Now supports exporting from linked models. Unloaded links are shown but disabled.
"""

import os, json, math, clr
import re
import codecs
from System import Environment
clr.AddReference("System")
from pyrevit import revit, DB, script, forms
from System.IO import FileStream, FileMode, FileAccess
from System.Collections.Generic import List
from System.Windows.Markup import XamlReader
from System.Windows import Visibility
from System.Windows.Forms import FolderBrowserDialog, OpenFileDialog, ColorDialog, DialogResult
from System.Windows.Controls import ComboBoxItem
from System.Windows.Media import SolidColorBrush, Color

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
            # iterate safely; avoid heavy geometry unless available
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
                        # location access sometimes throws for links/complex elements
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
    newColorBtn = window.FindName("newColorBtn")
    movedColorBtn = window.FindName("movedColorBtn")
    changedColorBtn = window.FindName("changedColorBtn")
    newRect = window.FindName("newRect")
    movedRect = window.FindName("movedRect")
    changedRect = window.FindName("changedRect")
    saveConfigBtn = window.FindName("saveConfigBtn")
    loadConfigBtn = window.FindName("loadConfigBtn")
    exportForm = window.FindName("exportForm")
    importForm = window.FindName("importForm")

    # ---------------- Auto-fill Job Info ----------------
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

    # Build combined prefix
    if craddys_job and project_number:
        job_number_default = "{}_{}_".format(craddys_job, project_number)
    elif craddys_job:
        job_number_default = "{}_".format(craddys_job)
    elif project_number:
        job_number_default = "{}_".format(project_number)
    else:
        job_number_default = "TBC_"

    # Set initial UI fields
    jobBox.Text = job_name_default
    jobNumberBox.Text = job_number_default

    # ---------------- Anticipated filename live preview ----------------
    def update_filename_preview(sender=None, e=None):
        prefix = jobNumberBox.Text.strip() or "TBC_"
        job_name = jobBox.Text.strip() or "TBC"
        revision = revisionBox.Text.strip() or "P00"

        # Get selected discipline safely
        discipline = ""
        sel_disc = disciplineBox.SelectedItem
        if sel_disc:
            try:
                discipline = str(sel_disc.Content)
            except:
                discipline = str(sel_disc)  # fallback
        if not discipline:
            discipline = "Discipline"

        # Get selected model source
        sel_item = modelSourceBox.SelectedItem
        model_name = str(sel_item.Content) if sel_item else "This Model"
        model_name_clean = model_name.replace(".rvt", "").replace(" (unloaded)", "")

        # Build preview filename
        preview = "{}{}_{}_{}_({})".format(prefix, discipline, job_name, revision, model_name_clean)

        # Update TextBlock directly (no "Anticipated filename:" prefix)
        anticipatedFileName.Text = preview


    # ---------------- Hook events ----------------
    jobNumberBox.TextChanged += update_filename_preview
    jobBox.TextChanged += update_filename_preview
    revisionBox.TextChanged += update_filename_preview
    modelSourceBox.SelectionChanged += update_filename_preview
    disciplineBox.SelectionChanged += update_filename_preview  # <-- now instant


    # ---------------- Discipline dropdown ----------------
    disciplineBox.Items.Clear()
    for d in ["Architect", "Structures", "M&E"]:
        disciplineBox.Items.Add(d)
    disciplineBox.SelectedIndex = 0

    # ---------------- Model source dropdown ----------------
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

    # ---------------- UI Event Handlers ----------------
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
            rect.Fill = SolidColorBrush(Color.FromRgb(val.R, val.G, val.B))

    newColorBtn.Click += lambda s, e: pick_color("new", newRect)
    movedColorBtn.Click += lambda s, e: pick_color("moved", movedRect)
    changedColorBtn.Click += lambda s, e: pick_color("changed", changedRect)


    config_path = os.path.join(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                               "pyRevit", "WhatChangedColourConfig.json")

    def save_config(colors):
        colors_json = {k: [int(c) for c in v] for k, v in colors.items()}
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
        return {k: tuple(v) for k, v in colors_json.items()}

    saveConfigBtn.Click += lambda s, e: save_config(colors)

    def load_click(s, e):
        loaded = load_config()
        if loaded:
            colors.update(loaded)
            newRect.Fill = SolidColorBrush(Color.FromRgb(*colors["new"]))
            movedRect.Fill = SolidColorBrush(Color.FromRgb(*colors["moved"]))
            changedRect.Fill = SolidColorBrush(Color.FromRgb(*colors["changed"]))

    loadConfigBtn.Click += load_click

    def cancel_click(sender, e):
        window.Tag = None
        window.Close()

    def ok_click(sender, args):
        sel_item = modelSourceBox.SelectedItem
        selected_model = sel_item.Content if sel_item else "This Model"

        dlg_type = "Export" if exportToggle.IsChecked else "Import"
        job_number = jobNumberBox.Text.strip()

        if dlg_type == "Export":
            dlg = FolderBrowserDialog()
            if dlg.ShowDialog() == DialogResult.OK:
                folder = dlg.SelectedPath
                safe_model_name = re.sub(r'[<>:"/\\|?*]', '_', selected_model)
                prefix = "{}_".format(job_number) if job_number else "TBC_"
                filename = "{}{}{}_{}_({}).json".format(
                    prefix,
                    disciplineBox.Text,
                    jobBox.Text,
                    revisionBox.Text,
                    safe_model_name.replace(".rvt", "")
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

# Handle linked document selection
target_doc = doc
if action == "Export" and model_choice and model_choice != "This Model":
    # strip unloaded suffix if it somehow got through
    base_choice = model_choice.replace(" (unloaded)", "")
    # find link by name (or name with id if duplicates)
    link_instance = next((l for l in DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkInstance)
                          if l.Name == base_choice or "{} ({})".format(l.Name, l.Id.IntegerValue) == base_choice), None)
    if link_instance:
        try:
            link_doc = link_instance.GetLinkDocument()
        except:
            link_doc = None
        if link_doc:
            target_doc = link_doc
        else:
            forms.alert("⚠️ The selected link '{}' is not loaded or accessible.".format(base_choice), exitscript=True)

if action == "Export":
    # capture from target_doc (this model or linked doc)
    model_state = capture_model_state(target_doc)
    # write JSON safely (IronPython-compatible)
    with codecs.open(file_path, 'w', 'utf-8') as f:
        f.write(json.dumps(model_state, ensure_ascii=False, indent=2))
    output.print_md("✅ Snapshot exported to `{}`".format(file_path))
    script.exit()
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
view_family_type = next(
    vft for vft in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType)
    if vft.ViewFamily == DB.ViewFamily.ThreeDimensional
)

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
