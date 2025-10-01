from pyrevit import revit, DB, forms

link_instance = revit.pick_element("Select a CAD import (DWG/DXF)")
if not link_instance:
    forms.alert("No link selected.", title="Error")
    script.exit()

doc = revit.doc
active_view = revit.active_view

# Get the view template
template_id = active_view.ViewTemplateId
if template_id == DB.ElementId.InvalidElementId:
    forms.alert("Active view has no template.", title="Error")
    script.exit()
view_template = doc.GetElement(template_id)

t = DB.Transaction(doc, "Override DWG Layers in Template")
try:
    t.Start()

    # Override settings
    ogs = DB.OverrideGraphicSettings()
    ogs.SetProjectionLineColor(DB.Color(0, 0, 0))
    ogs.SetHalftone(True)

    # Override main imported category
    view_template.SetCategoryOverrides(link_instance.Category.Id, ogs)

    # Override all DWG layers
    for gs in DB.FilteredElementCollector(doc).OfClass(DB.GraphicsStyle):
        # Only consider imported layers belonging to this link
        if gs.GraphicsStyleCategory and gs.GraphicsStyleCategory.Name.startswith("Layer:"):
            try:
                view_template.SetSubcategoryOverrides(link_instance.Category.Id, gs.Id, ogs)
            except:
                pass

    t.Commit()
    forms.alert("DWG layers in template overridden to black + halftone.", title="Done")

except Exception as e:
    t.RollBack()
    forms.alert("Transaction failed: {}".format(str(e)), title="Error")
