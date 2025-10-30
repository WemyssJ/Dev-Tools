# -*- coding: utf-8 -*-
"""
What's Changed? Reporter for Revit Models
Optimised: Batch overrides + skip when no changes
"""

import os, json, math, clr
clr.AddReference("System")
from pyrevit import revit, DB, script, forms
from System.IO import FileStream, FileMode, FileAccess
from System.Collections.Generic import List
from System.Windows.Markup import XamlReader
from System.Windows import Visibility
from System.Windows.Forms import FolderBrowserDialog, OpenFileDialog
import System

output = script.get_output()
doc = revit.doc
uidoc = revit.uidoc

# ---------------- SETTINGS ----------------
PARAMS_TO_CHECK = [
    "Type Name", "Type", "Height", "Perimeter", "Length", "Width", "Depth"
]

# ---------------- Helper Functions ----------------
def make_color(r, g, b):
    return DB.Color(r, g, b)

def capture_model_state(doc):
    cats_to_include = [
        DB.BuiltInCategory.OST_Walls,
        DB.BuiltInCategory.OST_Floors,
        DB.BuiltInCategory.OST_Roofs,
        DB.BuiltInCategory.OST_Ceilings,
        DB.BuiltInCategory.OST_Columns,
        DB.BuiltInCategory.OST_StructuralColumns,
        DB.BuiltInCategory.OST_StructuralFraming,
        DB.BuiltInCategory.OST_StructuralFoundation,
        DB.BuiltInCategory.OST_Doors,
        DB.BuiltInCategory.OST_Windows,
        DB.BuiltInCategory.OST_GenericModel,
        DB.BuiltInCategory.OST_Furniture,
        DB.BuiltInCategory.OST_FurnitureSystems,
        DB.BuiltInCategory.OST_Casework,
        DB.BuiltInCategory.OST_MechanicalEquipment,
        DB.BuiltInCategory.OST_PipeCurves,
        DB.BuiltInCategory.OST_DuctCurves,
        DB.BuiltInCategory.OST_CableTray,
        DB.BuiltInCategory.OST_Conduit,
        DB.BuiltInCategory.OST_StructConnections,
        DB.BuiltInCategory.OST_Stairs,
        DB.BuiltInCategory.OST_Ramps,
        DB.BuiltInCategory.OST_Railings,
        DB.BuiltInCategory.OST_CurtainWallPanels,
        DB.BuiltInCategory.OST_CurtainWallMullions,
        DB.BuiltInCategory.OST_SpecialityEquipment
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

                    all_data[elid] = {
                        "cat": el.Category.Name if el.Category else "",
                        "loc": loc_data,
                        "params": param_dict
                    }
                except:
                    continue
        except:
            continue
    return all_data

def compare_states(prev_data, current_data):
    prev_ids = set(prev_data.keys())
    curr_ids = set(current_data.keys())
    new_ids = curr_ids - prev_ids
    deleted_ids = prev_ids - curr_ids
    common_ids = prev_ids & curr_ids

    moved_ids, param_changed_ids = [], []

    for eid in common_ids:
        prev_el, curr_el = prev_data[eid], current_data[eid]
        if prev_el["loc"] and curr_el["loc"]:
            try:
                dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(prev_el["loc"], curr_el["loc"])))
                if dist > 0.001:
                    moved_ids.append(eid)
                    continue
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

    if hasattr(DB.BuiltInCategory, "OST_ImportObjectStyles"):
        imports = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_ImportObjectStyles).ToElementIds()
        if imports:
            view3d.HideElements(List[DB.ElementId](imports))

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

    disciplineBox.Items.Clear()
    for d in ["Architect", "Structures", "M&E"]:
        disciplineBox.Items.Add(d)
    disciplineBox.SelectedIndex = 0
    importToggle.IsChecked = True
    window.FindName("exportForm").Visibility = Visibility.Collapsed

    def toggle_export(sender, e):
        window.FindName("exportForm").Visibility = Visibility.Visible
        importToggle.IsChecked = False
    def toggle_import(sender, e):
        window.FindName("exportForm").Visibility = Visibility.Collapsed
        exportToggle.IsChecked = False
    exportToggle.Checked += toggle_export
    importToggle.Checked += toggle_import

    def cancel_click(sender, e):
        window.Tag = None
        window.Close()
    def ok_click(sender, e):
        if exportToggle.IsChecked:
            dlg = FolderBrowserDialog()
            if dlg.ShowDialog() == System.Windows.Forms.DialogResult.OK:
                folder = dlg.SelectedPath
                filename = "{}_{}_{}.json".format(disciplineBox.Text, jobBox.Text, revisionBox.Text)
                path = os.path.join(folder, filename)
                window.Tag = ("Export", path)
        else:
            dlg = OpenFileDialog()
            dlg.Filter = "JSON Files|*.json"
            if dlg.ShowDialog() == System.Windows.Forms.DialogResult.OK:
                window.Tag = ("Import", dlg.FileName)
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

action, file_path = result
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

# ---- Skip if nothing changed ----
if not (new_ids or moved_ids or param_changed_ids):
    forms.alert("✅ No changes detected between current model and snapshot.", exitscript=True)

# --- Create 3D view ---
view_family_type = next(vft for vft in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType)
                        if vft.ViewFamily == DB.ViewFamily.ThreeDimensional)

with revit.Transaction("Create/Reuse What's Changed 3D View"):
    # Try to find existing
    view3d = None
    existing_views = DB.FilteredElementCollector(doc).OfClass(DB.View3D).ToElements()
    for v in existing_views:
        if v.Name == "What's Changed":
            view3d = v
            break

    if view3d is None:
        # Create new
        view3d = DB.View3D.CreateIsometric(doc, view_family_type.Id)
        view3d.Name = "What's Changed"

    view3d = prepare_view(view3d, doc)

# --- Batch Apply Overrides ---
def make_override(r, g, b):
    col = make_color(r, g, b)
    ovr = DB.OverrideGraphicSettings()
    ovr.SetProjectionLineColor(col)
    ovr.SetSurfaceForegroundPatternColor(col)
    ovr.SetSurfaceForegroundPatternVisible(True)
    return ovr

def batch_override(view, ids, ovr):
    if not ids:
        return
    id_list = List[DB.ElementId]([DB.ElementId(int(i)) for i in ids])
    for eid in id_list:
        view.SetElementOverrides(eid, ovr)

ovr_new = make_override(0, 255, 0)
ovr_moved = make_override(255, 165, 0)
ovr_changed = make_override(0, 100, 255)

with forms.ProgressBar(title="Applying What's Changed Overrides...") as pb:
    with revit.Transaction("Apply Batch Overrides"):
        batch_override(view3d, new_ids, ovr_new)
        batch_override(view3d, moved_ids, ovr_moved)
        batch_override(view3d, param_changed_ids, ovr_changed)
        pb.update_progress(1, 1)

uidoc.ActiveView = view3d

# --- Summary ---
output.print_md("### ✅ What's Changed Report")
output.print_md("**New elements:** {} 🟩".format(len(new_ids)))
output.print_md("**Moved elements:** {} 🟧".format(len(moved_ids)))
output.print_md("**Parameter changes:** {} 🟦".format(len(param_changed_ids)))
output.print_md("**Deleted elements:** {} ❌".format(len(prev_data) - len(current_data)))
