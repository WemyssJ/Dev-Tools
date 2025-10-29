# -*- coding: utf-8 -*-
"""
What's Changed? Reporter for Revit Models
UI-based Export / Import with color-coded 3D view
"""

import os, json, math, clr
from pyrevit import revit, DB, script
from System.IO import StreamWriter, FileStream, FileMode, FileAccess
from System.Collections.Generic import List
from System.Windows import Application
from System.Windows.Markup import XamlReader
from System.Windows.Forms import FolderBrowserDialog, OpenFileDialog
import System

output = script.get_output()
doc = revit.doc
uidoc = revit.uidoc

# --- Helper functions -------------------------------------------------------

def make_color(r, g, b):
    return DB.Color(r, g, b)

def capture_model_state(doc):
    """Capture all 3D element IDs, categories, locations and key parameters"""
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
                    for p in el.Parameters:
                        if p.Definition and p.Definition.Name and p.HasValue:
                            try:
                                param_dict[p.Definition.Name] = p.AsValueString() or str(p.AsString())
                            except:
                                pass

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
    """Compare two model states"""
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
                dist = math.sqrt(sum([(a - b) ** 2 for a, b in zip(prev_el["loc"], curr_el["loc"])]))
                if dist > 0.001:
                    moved_ids.append(eid)
                    continue
            except:
                pass

        for k, v in prev_el["params"].items():
            if k in curr_el["params"] and curr_el["params"][k] != v:
                param_changed_ids.append(eid)
                break

    return new_ids, deleted_ids, moved_ids, param_changed_ids

def prepare_view(view3d, doc):
    """Configure clean interrogation-ready 3D view"""
    view3d.DisplayStyle = DB.DisplayStyle(2)
    view3d.DetailLevel = DB.ViewDetailLevel.Fine

    section_box_cat = DB.Category.GetCategory(doc, DB.BuiltInCategory.OST_VolumeOfInterest)

    for cat in doc.Settings.Categories:
        try:
            if cat.Id == section_box_cat.Id:
                continue
            if cat.CategoryType != DB.CategoryType.Model or "Analytical" in cat.Name or "Annotation" in cat.Name:
                view3d.SetCategoryHidden(cat.Id, True)
        except:
            continue

    rvt_links_cat = DB.Category.GetCategory(doc, DB.BuiltInCategory.OST_RvtLinks)
    if rvt_links_cat:
        view3d.SetCategoryHidden(rvt_links_cat.Id, True)

    imports = DB.FilteredElementCollector(doc).OfClass(DB.ImportInstance).ToElementIds()
    if imports:
        view3d.HideElements(List[DB.ElementId](imports))

    if not view3d.IsSectionBoxActive:
        view3d.IsSectionBoxActive = True

    scope_boxes = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_VolumeOfInterest)\
                    .WhereElementIsNotElementType().ToElements()
    if scope_boxes:
        try:
            sb_param = view3d.get_Parameter(DB.BuiltInParameter.VIEWER_VOLUME_OF_INTEREST_CROP)
            if sb_param and not sb_param.IsReadOnly:
                sb_param.Set(scope_boxes[0].Id)
        except:
            pass

    return view3d

# --- WPF UI -----------------------------------------------------------------

def show_ui(xaml_path):
    fs = FileStream(xaml_path, FileMode.Open, FileAccess.Read)
    window = XamlReader.Load(fs)
    fs.Close()

    # Fetch controls
    cancelBtn = window.FindName("cancelBtn")
    okBtn = window.FindName("okBtn")
    exportRadio = window.FindName("exportRadio")
    importRadio = window.FindName("importRadio")
    disciplineBox = window.FindName("disciplineBox")
    revisionBox = window.FindName("revisionBox")
    jobBox = window.FindName("jobBox")

    def cancel_click(sender, e):
        window.Tag = None
        window.Close()

    def ok_click(sender, e):
        action = 'Export' if exportRadio.IsChecked else 'Import'
        discipline = disciplineBox.Text
        revision = revisionBox.Text
        job = jobBox.Text

        if action == 'Export':
            dlg = FolderBrowserDialog()
            if dlg.ShowDialog() == System.Windows.Forms.DialogResult.OK:
                folder = dlg.SelectedPath
                filename = "{}_{}_{}.json".format(discipline, job, revision)
                path = os.path.join(folder, filename)
                window.Tag = ('Export', path)
        elif action == 'Import':
            dlg = OpenFileDialog()
            dlg.Filter = "JSON Files|*.json"
            if dlg.ShowDialog() == System.Windows.Forms.DialogResult.OK:
                path = dlg.FileName
                window.Tag = ('Import', path)

        window.Close()

    cancelBtn.Click += cancel_click
    okBtn.Click += ok_click

    # Instead of Application().Run(window), just:
    window.ShowDialog()  

    return getattr(window, 'Tag', None)


# --- MAIN -------------------------------------------------------------------

xaml_path = os.path.join(script.get_script_path(), "whats_changed_ui.xaml")
result = show_ui(xaml_path)

if not result:
    script.exit()

action, file_path = result
output.print_md("**Action:** {} | **File:** {}".format(action, file_path))

if action == 'Export':
    model_state = capture_model_state(doc)
    json_text = json.dumps(model_state, ensure_ascii=False, indent=2)
    with open(file_path, 'w') as f:
        f.write(json_text)
    output.print_md("✅ Snapshot exported to `{}`".format(file_path))
    script.exit()

elif action == 'Import':
    if not os.path.exists(file_path):
        output.print_md("⚠️ File not found: `{}`".format(file_path))
        script.exit()
    with open(file_path, 'r') as f:
        prev_data = json.load(f)

current_data = capture_model_state(doc)
new_ids, deleted_ids, moved_ids, param_changed_ids = compare_states(prev_data, current_data)

# --- Create 3D view ---
view_family_type = next(vft for vft in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType)
                        if vft.ViewFamily == DB.ViewFamily.ThreeDimensional)

with revit.Transaction("Create What's Changed 3D View"):
    view3d = DB.View3D.CreateIsometric(doc, view_family_type.Id)
    view3d.Name = "What's Changed"
    view3d = prepare_view(view3d, doc)

# --- Apply Color Overrides ---
def make_override(r, g, b):
    col = make_color(r, g, b)
    ovr = DB.OverrideGraphicSettings()
    ovr.SetProjectionLineColor(col)
    ovr.SetSurfaceForegroundPatternColor(col)
    ovr.SetSurfaceForegroundPatternVisible(True)
    return ovr

ovr_green = make_override(0, 255, 0)
ovr_orange = make_override(255, 165, 0)
ovr_blue = make_override(0, 100, 255)
ovr_halftone = DB.OverrideGraphicSettings()
ovr_halftone.SetHalftone(True)

with revit.Transaction("Apply What's Changed Overrides"):
    for eid, eldata in current_data.items():
        el = doc.GetElement(DB.ElementId(int(eid)))
        if not el:
            continue
        if eid in new_ids:
            view3d.SetElementOverrides(el.Id, ovr_green)
        elif eid in moved_ids:
            view3d.SetElementOverrides(el.Id, ovr_orange)
        elif eid in param_changed_ids:
            view3d.SetElementOverrides(el.Id, ovr_blue)
        else:
            view3d.SetElementOverrides(el.Id, ovr_halftone)

# --- Summary Report ---
output.print_md("### ✅ What's Changed Report")
output.print_md("**New elements:** {} 🟩".format(len(new_ids)))
output.print_md("**Moved elements:** {} 🟧".format(len(moved_ids)))
output.print_md("**Parameter changes:** {} 🟦".format(len(param_changed_ids)))
output.print_md("**Deleted elements:** {} ❌".format(len(prev_data) - len(current_data)))
output.print_md("---")
output.print_md("**Legend:**\n🟩 Green = New\n🟧 Orange = Moved\n🟦 Blue = Parameter changed\nHalftone = Unchanged")

uidoc.ActiveView = view3d
output.print_md("👀 View created: **'What's Changed'** — ready for interrogation.")
