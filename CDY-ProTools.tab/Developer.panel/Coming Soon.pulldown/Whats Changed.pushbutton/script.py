# -*- coding: utf-8 -*-
"""
What's Changed? Reporter for Revit Models
Optimised: Batch overrides + live color selection + improved toggle logic
"""

import os, json, math, clr
from System import Environment
clr.AddReference("System")
from pyrevit import revit, DB, script, forms
from System.IO import FileStream, FileMode, FileAccess
from System.Collections.Generic import List
from System.Windows.Markup import XamlReader
from System.Windows import Visibility
from System.Windows.Forms import FolderBrowserDialog, OpenFileDialog, ColorDialog
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
                    loc = el.Location
                    if hasattr(loc, "Point") and loc.Point:
                        loc_data = (loc.Point.X, loc.Point.Y, loc.Point.Z)
                    elif hasattr(loc, "Curve") and loc.Curve:
                        c = loc.Curve
                        loc_data = (c.GetEndPoint(0).X, c.GetEndPoint(0).Y, c.GetEndPoint(0).Z)
                    else:
                        loc_data = None

                    param_dict = {}
                    for pname in PARAMS_TO_CHECK:
                        p = el.LookupParameter(pname)
                        if p and p.HasValue:
                            val = p.AsValueString() or p.AsString()
                            if val:
                                param_dict[pname] = val

                    all_data[elid] = {"cat": el.Category.Name if el.Category else "", "loc": loc_data, "params": param_dict}
                except: continue
        except: continue
    return all_data

def compare_states(prev_data, current_data):
    prev_ids, curr_ids = set(prev_data.keys()), set(current_data.keys())
    new_ids, deleted_ids = curr_ids - prev_ids, prev_ids - curr_ids
    common_ids = prev_ids & curr_ids
    moved_ids, param_changed_ids = [], []

    for eid in common_ids:
        prev_el, curr_el = prev_data[eid], current_data[eid]
        if prev_el["loc"] and curr_el["loc"]:
            try:
                dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(prev_el["loc"], curr_el["loc"])))
                if dist > 0.001: moved_ids.append(eid)
            except: pass
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
        except: continue
    rvt_links_cat = DB.Category.GetCategory(doc, DB.BuiltInCategory.OST_RvtLinks)
    if rvt_links_cat: view3d.SetCategoryHidden(rvt_links_cat.Id, True)
    view3d.IsSectionBoxActive = True
    return view3d

# ---------------- UI ----------------
def show_ui(xaml_path):
    from System.Windows.Markup import XamlReader
    from System.IO import FileStream, FileMode, FileAccess
    from System.Windows import Visibility
    from System.Windows.Forms import ColorDialog, DialogResult
    from System.Windows.Media import SolidColorBrush, Color

    fs = FileStream(xaml_path, FileMode.Open, FileAccess.Read)
    window = XamlReader.Load(fs)
    fs.Close()

    # --- Find controls ---
    cancelBtn = window.FindName("cancelBtn")
    okBtn = window.FindName("okBtn")
    importToggle = window.FindName("importToggle")
    exportToggle = window.FindName("exportToggle")
    disciplineBox = window.FindName("disciplineBox")
    revisionBox = window.FindName("revisionBox")
    jobBox = window.FindName("jobBox")
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

    # --- Populate discipline drop-down ---
    disciplineBox.Items.Clear()
    for d in ["Architect", "Structures", "M&E"]:
        disciplineBox.Items.Add(d)
    disciplineBox.SelectedIndex = 0

    # --- Default toggle states ---
    importToggle.IsChecked = True
    exportForm.Visibility = Visibility.Collapsed
    saveConfigBtn.Visibility = Visibility.Visible
    loadConfigBtn.Visibility = Visibility.Visible

    # --- Toggle handlers ---
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

    # --- Color picking ---
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

    # --- Save / Load Config ---
    config_path = os.path.join(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                           "pyRevit", "WhatChangedColourConfig.json")

    def save_config(colors):
        # Convert each color component to a plain Python int
        colors_json = {k: [int(c) for c in v] for k, v in colors.items()}
        folder = os.path.dirname(config_path)
        if not os.path.exists(folder):
            os.makedirs(folder)
        with open(config_path, 'w') as f:
            json.dump(colors_json, f, indent=2)

    def load_config():
        if not os.path.exists(config_path):
            forms.alert("⚠️ No saved configuration found.", title="What's Changed?", ok=True)
            return None
        with open(config_path, 'r') as f:
            colors_json = json.load(f)
        return {k: tuple(v) for k, v in colors_json.items()}

    saveConfigBtn = window.FindName("saveConfigBtn")
    loadConfigBtn = window.FindName("loadConfigBtn")

    saveConfigBtn.Click += lambda s, e: save_config(colors)

    def load_click(s, e):
        loaded = load_config()
        if loaded:
            colors.update(loaded)
            # Update rectangles
            newRect.Fill = SolidColorBrush(Color.FromRgb(*colors["new"]))
            movedRect.Fill = SolidColorBrush(Color.FromRgb(*colors["moved"]))
            changedRect.Fill = SolidColorBrush(Color.FromRgb(*colors["changed"]))
    loadConfigBtn.Click += load_click

    # --- Cancel / OK ---
    def cancel_click(sender, e):
        window.Tag = None
        window.Close()

    def ok_click(sender, e):
        dlg_type = "Export" if exportToggle.IsChecked else "Import"
        dlg_file = ""
        if dlg_type == "Export":
            from System.Windows.Forms import FolderBrowserDialog
            dlg = FolderBrowserDialog()
            if dlg.ShowDialog() == DialogResult.OK:
                folder = dlg.SelectedPath
                filename = "{}_{}_{}.json".format(disciplineBox.Text, jobBox.Text, revisionBox.Text)
                dlg_file = os.path.join(folder, filename)
        else:
            from System.Windows.Forms import OpenFileDialog
            dlg = OpenFileDialog()
            dlg.Filter = "JSON Files|*.json"
            if dlg.ShowDialog() == DialogResult.OK:
                dlg_file = dlg.FileName

        window.Tag = (dlg_type, dlg_file, colors["new"], colors["moved"], colors["changed"])
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

action, file_path, new_col, moved_col, changed_col = result
output.print_md("**Action:** {} | **File:** {}".format(action, file_path))

if action == "Export":
    model_state = capture_model_state(doc)
    with open(file_path, 'w') as f:
        f.write(json.dumps(model_state, ensure_ascii=False, indent=2))
    output.print_md("✅ Snapshot exported to `{}`".format(file_path))
    script.exit()
elif action == "Import":
    if not os.path.exists(file_path):
        forms.alert("⚠️ File not found: `{}`".format(file_path), exitscript=True)
    with open(file_path, 'r') as f:
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
    for eid in new_ids: view3d.SetElementOverrides(DB.ElementId(int(eid)), ovr_new)
    for eid in moved_ids: view3d.SetElementOverrides(DB.ElementId(int(eid)), ovr_moved)
    for eid in param_changed_ids: view3d.SetElementOverrides(DB.ElementId(int(eid)), ovr_changed)

uidoc.ActiveView = view3d

# --- Summary ---
def rgb_block(rgb, size=15):
    """Returns HTML span with background color matching RGB tuple."""
    r, g, b = rgb
    return '<span style="display:inline-block;width:{}px;height:{}px;background-color:rgb({},{},{});margin-right:5px;border:1px solid #000;"></span>'.format(
        size, size, r, g, b)

output.print_md("### ✅ What's Changed Report")

# Use the colors from the config/overrides
output.print_html("<b>New elements:</b> {} {}".format(rgb_block(new_col), len(new_ids)))
output.print_html("<b>Moved elements:</b> {} {}".format(rgb_block(moved_col), len(moved_ids)))
output.print_html("<b>Parameter changes:</b> {} {}".format(rgb_block(changed_col), len(param_changed_ids)))


deleted_ids = set(prev_data.keys()) - set(current_data.keys())
# Keep the deleted emoji (red cross) or make a red block
output.print_md("**Deleted elements:** {} ❌".format(len(deleted_ids)))

