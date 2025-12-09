# -*- coding: utf-8 -*-
"""
CAD Layer Quick Override (pyRevit / IronPython)
- Pick a CAD entity (DWG) and override its DWG layers in the active view or template
- Options: Hide, Set Lineweight, Set Color, Set Linestyle, Reset, GreyScale DWG
- Preserves previous override settings when applying new ones
- GreyScale DWG now applies to all layers in the selected CAD import
"""
from pyrevit import forms, revit, DB, script
from Autodesk.Revit.UI import Selection
from Autodesk.Revit.DB import OverrideGraphicSettings, ImportInstance, Color as RVColor

uidoc = revit.uidoc
doc = revit.doc


# -------------------- PICK CAD LAYER --------------------
def get_cad_layer_from_pick():
    """Pick an object on the CAD import and return (import_instance, layer_name)."""
    try:
        ref = uidoc.Selection.PickObject(
            Selection.ObjectType.PointOnElement,
            "Select an object on the CAD import"
        )
    except:
        return None, None

    picked = doc.GetElement(ref.ElementId)
    import_inst = None
    gs_id = None

    if isinstance(picked, ImportInstance):
        import_inst = picked
        try:
            geom_obj = import_inst.GetGeometryObjectFromReference(ref)
            gs_id = geom_obj.GraphicsStyleId
        except:
            gs_id = None
    else:
        parent = picked
        while parent:
            if isinstance(parent, ImportInstance):
                import_inst = parent
                break
            try:
                parent = doc.GetElement(parent.ParentId)
            except:
                parent = None
        gs_id = picked.GraphicsStyleId if picked else None

    if not import_inst or not gs_id:
        forms.alert("Could not resolve the CAD layer from your selection.")
        return None, None

    gs = doc.GetElement(gs_id)
    if not gs:
        forms.alert("Could not resolve GraphicsStyle from picked geometry.")
        return None, None

    layer_name = gs.GraphicsStyleCategory.Name
    return import_inst, layer_name


# -------------------- ACTION --------------------
def ask_action(layer_name):
    # List of choices in desired order
    choices = [
        "[Layer] Hide",
        "[Layer] Set Lineweight",
        "[Layer] Set Color",
        "[Layer] Set Linestyle",
        "[Layer] Reset Overrides",
        "[DWG] GreyScale"
    ]
    # Corresponding action codes in same order
    action_codes = ["hide", "lw", "color", "linestyle", "reset", "greyscale"]

    res = forms.SelectFromList.show(
        choices,
        title="DWG Layer: {}".format(layer_name),
        multiselect=False,
        sort=False  # prevents automatic alphabetical sorting
    )
    if not res:
        return None

    # Map selected choice to action
    index = choices.index(res)
    return action_codes[index]


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
    lw = forms.SelectFromList.show(options, title="Select Lineweight", multiselect=False)
    if not lw:
        return None
    return int(lw)


def pick_linestyle():
    patterns = {lp.Name: lp.Id for lp in DB.FilteredElementCollector(doc).OfClass(DB.LinePatternElement)}
    for name in ["Solid", "Hidden", "Center", "Dashed"]:
        if name not in patterns:
            lp = next((p for p in DB.FilteredElementCollector(doc)
                       .OfClass(DB.LinePatternElement) if p.Name == name), None)
            if lp:
                patterns[name] = lp.Id
    sel = forms.SelectFromList.show(sorted(patterns.keys()), title="Select Linestyle", multiselect=False)
    if not sel:
        return None
    return patterns[sel]


# -------------------- GREYSCALE ALL LAYERS --------------------
def greyscale_all_layers(import_inst, view_or_template):
    root_cat = import_inst.Category
    if root_cat is None:
        forms.alert("Could not access import category root.")
        return

    # Iterate directly over CategoryNameMap
    for layer_cat in root_cat.SubCategories:
        ovr = OverrideGraphicSettings()
        ovr.SetProjectionLineColor(RVColor(192, 192, 192))
        view_or_template.SetCategoryOverrides(layer_cat.Id, ovr)



# -------------------- APPLY OVERRIDE (TEMPLATE-SAFE) --------------------
def apply_override(import_inst, layer_name, action, user_inputs):
    view = doc.ActiveView
    template_id = view.ViewTemplateId

    target_view = doc.GetElement(template_id) if template_id != DB.ElementId.InvalidElementId else view
    if template_id != DB.ElementId.InvalidElementId:
        forms.alert(
            "Applying overrides directly to the view template '{}'. "
            "All views using this template will inherit these changes.".format(target_view.Name)
        )

    _apply_override_internal(target_view, import_inst, layer_name, action, user_inputs)


def _apply_override_internal(view_or_template, import_inst, layer_name, action, user_inputs):
    root_cat = import_inst.Category
    if root_cat is None:
        forms.alert("Could not access import category root.")
        return

    # Handle greyscale all layers
    if action == "greyscale":
        greyscale_all_layers(import_inst, view_or_template)
        return

    try:
        layer_cat = root_cat.SubCategories.get_Item(layer_name)
    except:
        layer_cat = None

    if not layer_cat:
        forms.alert("DWG layer not found as a subcategory: {}".format(layer_name))
        return

    existing = view_or_template.GetCategoryOverrides(layer_cat.Id)
    ovr = OverrideGraphicSettings()

    if existing:
        if existing.ProjectionLineColor.IsValid:
            ovr.SetProjectionLineColor(existing.ProjectionLineColor)
        if existing.ProjectionLineWeight >= 0:
            ovr.SetProjectionLineWeight(existing.ProjectionLineWeight)
        if existing.ProjectionLinePatternId != DB.ElementId.InvalidElementId:
            ovr.SetProjectionLinePatternId(existing.ProjectionLinePatternId)
        if existing.CutLineColor.IsValid:
            ovr.SetCutLineColor(existing.CutLineColor)
        if existing.CutLineWeight >= 0:
            ovr.SetCutLineWeight(existing.CutLineWeight)
        if existing.CutLinePatternId != DB.ElementId.InvalidElementId:
            ovr.SetCutLinePatternId(existing.CutLinePatternId)
        if existing.SurfaceForegroundPatternId != DB.ElementId.InvalidElementId:
            ovr.SetSurfaceForegroundPatternId(existing.SurfaceForegroundPatternId)
        if existing.SurfaceForegroundPatternColor.IsValid:
            ovr.SetSurfaceForegroundPatternColor(existing.SurfaceForegroundPatternColor)
        if existing.SurfaceBackgroundPatternId != DB.ElementId.InvalidElementId:
            ovr.SetSurfaceBackgroundPatternId(existing.SurfaceBackgroundPatternId)
        if existing.SurfaceBackgroundPatternColor.IsValid:
            ovr.SetSurfaceBackgroundPatternColor(existing.SurfaceBackgroundPatternColor)
        if existing.Transparency > 0:
            ovr.SetSurfaceTransparency(existing.Transparency)
        if existing.Halftone:
            ovr.SetHalftone(True)

    if action == "hide":
        view_or_template.SetCategoryHidden(layer_cat.Id, True)
    elif action == "color":
        rgb = user_inputs.get("color")
        if not rgb:
            forms.alert("No color selected.")
            return
        ovr.SetProjectionLineColor(rgb)
        view_or_template.SetCategoryOverrides(layer_cat.Id, ovr)
    elif action == "lw":
        lw = user_inputs.get("lw")
        if not lw:
            forms.alert("No lineweight selected.")
            return
        ovr.SetProjectionLineWeight(int(lw))
        view_or_template.SetCategoryOverrides(layer_cat.Id, ovr)
    elif action == "linestyle":
        ls_id = user_inputs.get("ls_id")
        if not ls_id:
            forms.alert("No linestyle selected.")
            return
        ovr.SetProjectionLinePatternId(ls_id)
        view_or_template.SetCategoryOverrides(layer_cat.Id, ovr)
    elif action == "reset":
        view_or_template.SetCategoryOverrides(layer_cat.Id, OverrideGraphicSettings())
        view_or_template.SetCategoryHidden(layer_cat.Id, False)


# -------------------- MAIN --------------------
import_inst, layer = get_cad_layer_from_pick()
if not import_inst or not layer:
    script.exit()

action = ask_action(layer)
if not action:
    script.exit()

user_inputs = {}
if action == "color":
    c = pick_color()
    if not c:
        script.exit()
    user_inputs["color"] = c
elif action == "lw":
    lw = pick_lineweight()
    if lw is None:
        script.exit()
    user_inputs["lw"] = lw
elif action == "linestyle":
    ls = pick_linestyle()
    if not ls:
        script.exit()
    user_inputs["ls_id"] = ls

t = DB.Transaction(doc, "CAD Layer Quick Override")
t.Start()
try:
    apply_override(import_inst, layer, action, user_inputs)
    t.Commit()
except Exception as ex:
    t.RollBack()
    forms.alert("Error applying override:\n{}".format(ex))
