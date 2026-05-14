# -*- coding: utf-8 -*-
"""
CAD Layer Quick Override (pyRevit / IronPython)

- Pick MULTIPLE objects on a CAD import (ESC to finish)
- Resolve all picked objects to DWG layers
- Apply overrides to all resolved layers

Actions:
- Hide
- Set Lineweight
- Set Color
- Set Linestyle
- Reset Overrides
- GreyScale (all layers)

Notes:
- Preserves existing overrides
- Template-safe
"""

from pyrevit import forms, revit, DB, script
from Autodesk.Revit.UI import Selection
from Autodesk.Revit.DB import (
    OverrideGraphicSettings,
    ImportInstance,
    Color as RVColor
)

##############################################################################################
# TELEMETRY IMPORTS #
##############################################################################################
# Only works IF specified TELEMETRY_JSON path exists within %AppData%\pyRevit\Extensions\BIMTools.extension\lib\telemetry_auto.py"
# Records tool usage by date & revit version
import os, sys

# Add lib folder for telemetry_auto
lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'lib'))
if lib_path not in sys.path:
    sys.path.append(lib_path)

import telemetry_auto

tool_name = os.path.basename(os.path.dirname(__file__)) 
TOOL_NAME = tool_name.replace(".pushbutton", "")
telemetry_auto.log_tool_usage(TOOL_NAME)
##############################################################################################

uidoc = revit.uidoc
doc = revit.doc


# -------------------- PICK MULTIPLE DWG OBJECTS --------------------
def pick_multiple_cad_layers():
    """
    Pick multiple objects on a CAD import.
    ESC finishes selection.
    Returns (import_instance, list_of_layer_names)
    """
    layers = set()
    import_inst = None

    forms.alert(
        "Pick objects on the DWG.\n"
        "Press ESC when finished.",
        title="DWG Layer Selection"
    )

    while True:
        try:
            ref = uidoc.Selection.PickObject(
                Selection.ObjectType.PointOnElement,
                "Pick DWG geometry (ESC to finish)"
            )
        except:
            break  # ESC exits loop

        elem = doc.GetElement(ref.ElementId)

        if isinstance(elem, ImportInstance):
            import_inst = elem
            try:
                geom = import_inst.GetGeometryObjectFromReference(ref)
                gs_id = geom.GraphicsStyleId
            except:
                continue
        else:
            parent = elem
            while parent:
                if isinstance(parent, ImportInstance):
                    import_inst = parent
                    break
                try:
                    parent = doc.GetElement(parent.ParentId)
                except:
                    parent = None

            gs_id = elem.GraphicsStyleId if elem else None

        if not import_inst or not gs_id:
            continue

        gs = doc.GetElement(gs_id)
        if not gs:
            continue

        layer_name = gs.GraphicsStyleCategory.Name
        layers.add(layer_name)

    if not import_inst or not layers:
        return None, None

    return import_inst, list(layers)


# -------------------- ACTION --------------------
def ask_action(layer_names):
    choices = [
        "[Layer] Hide",
        "[Layer] Set Lineweight",
        "[Layer] Set Color",
        "[Layer] Set Linestyle",
        "[Layer] Reset Overrides",
        "[DWG] GreyScale"
    ]
    action_codes = ["hide", "lw", "color", "linestyle", "reset", "greyscale"]

    res = forms.SelectFromList.show(
        choices,
        title="DWG Layers:\n{}".format(", ".join(sorted(layer_names))),
        multiselect=False,
        sort=False
    )

    if not res:
        return None

    return action_codes[choices.index(res)]


# -------------------- USER INPUTS --------------------
def pick_color():
    from System.Windows.Forms import ColorDialog, DialogResult
    cd = ColorDialog()
    cd.FullOpen = True
    if cd.ShowDialog() != DialogResult.OK:
        return None
    c = cd.Color
    return RVColor(c.R, c.G, c.B)


def pick_lineweight():
    options = [str(i) for i in range(1, 17)]
    lw = forms.SelectFromList.show(
        options,
        title="Select Lineweight",
        multiselect=False
    )
    return int(lw) if lw else None


def pick_linestyle():
    patterns = {
        lp.Name: lp.Id
        for lp in DB.FilteredElementCollector(doc)
        .OfClass(DB.LinePatternElement)
    }

    sel = forms.SelectFromList.show(
        sorted(patterns.keys()),
        title="Select Linestyle",
        multiselect=False
    )

    return patterns.get(sel)


# -------------------- GREYSCALE ALL --------------------
def greyscale_all_layers(import_inst, view_or_template):
    root_cat = import_inst.Category
    if not root_cat:
        return

    for layer_cat in root_cat.SubCategories:
        ovr = OverrideGraphicSettings()
        ovr.SetProjectionLineColor(RVColor(192, 192, 192))
        view_or_template.SetCategoryOverrides(layer_cat.Id, ovr)


# -------------------- APPLY OVERRIDES --------------------
def apply_override(import_inst, layer_names, action, user_inputs):
    view = doc.ActiveView
    template_id = view.ViewTemplateId

    target = (
        doc.GetElement(template_id)
        if template_id != DB.ElementId.InvalidElementId
        else view
    )

    if template_id != DB.ElementId.InvalidElementId:
        forms.alert(
            "Applying overrides directly to the view template '{}'.\n"
            "All views using this template will inherit these changes."
            .format(target.Name)
        )

    root_cat = import_inst.Category
    if not root_cat:
        return

    if action == "greyscale":
        greyscale_all_layers(import_inst, target)
        return

    for layer_name in layer_names:
        try:
            layer_cat = root_cat.SubCategories.get_Item(layer_name)
        except:
            continue

        if not layer_cat:
            continue

        existing = target.GetCategoryOverrides(layer_cat.Id)
        ovr = OverrideGraphicSettings()

        if existing:
            if existing.ProjectionLineColor.IsValid:
                ovr.SetProjectionLineColor(existing.ProjectionLineColor)
            if existing.ProjectionLineWeight >= 0:
                ovr.SetProjectionLineWeight(existing.ProjectionLineWeight)
            if existing.ProjectionLinePatternId != DB.ElementId.InvalidElementId:
                ovr.SetProjectionLinePatternId(existing.ProjectionLinePatternId)
            if existing.Halftone:
                ovr.SetHalftone(True)

        if action == "hide":
            target.SetCategoryHidden(layer_cat.Id, True)

        elif action == "color":
            ovr.SetProjectionLineColor(user_inputs["color"])
            target.SetCategoryOverrides(layer_cat.Id, ovr)

        elif action == "lw":
            ovr.SetProjectionLineWeight(user_inputs["lw"])
            target.SetCategoryOverrides(layer_cat.Id, ovr)

        elif action == "linestyle":
            ovr.SetProjectionLinePatternId(user_inputs["ls_id"])
            target.SetCategoryOverrides(layer_cat.Id, ovr)

        elif action == "reset":
            target.SetCategoryOverrides(layer_cat.Id, OverrideGraphicSettings())
            target.SetCategoryHidden(layer_cat.Id, False)


# -------------------- MAIN --------------------
import_inst, layers = pick_multiple_cad_layers()
if not import_inst or not layers:
    script.exit()

action = ask_action(layers)
if not action:
    script.exit()

user_inputs = {}

if action == "color":
    user_inputs["color"] = pick_color()
    if not user_inputs["color"]:
        script.exit()

elif action == "lw":
    user_inputs["lw"] = pick_lineweight()
    if user_inputs["lw"] is None:
        script.exit()

elif action == "linestyle":
    user_inputs["ls_id"] = pick_linestyle()
    if not user_inputs["ls_id"]:
        script.exit()

t = DB.Transaction(doc, "CAD Layer Quick Override (Multi-Pick)")
t.Start()
try:
    apply_override(import_inst, layers, action, user_inputs)
    t.Commit()
except Exception as ex:
    t.RollBack()
    forms.alert("Error applying override:\n{}".format(ex))
