# -*- coding: utf-8 -*-
from pyrevit import revit, DB, script

doc = revit.doc
uidoc = revit.uidoc
output = script.get_output()
output.set_title("Copy Detail Number to View Name (Selected Viewports)")

# Get selected elements
selection_ids = uidoc.Selection.GetElementIds()
if not selection_ids:
    output.print_md("No elements selected. Please select one or more viewports.")
    script.exit()

# Filter for selected viewports
selected_viewports = [doc.GetElement(eid) for eid in selection_ids if isinstance(doc.GetElement(eid), DB.Viewport)]

if not selected_viewports:
    output.print_md("No viewports selected. Please select one or more viewport elements.")
    script.exit()

with revit.Transaction("Copy Detail Number to View Name (Selected Viewports)"):
    for vp in selected_viewports:
        view = doc.GetElement(vp.ViewId)
        if not view:
            output.print_md("⚠️ Could not find view for viewport ID: {}".format(vp.Id))
            continue

        detail_param = vp.LookupParameter("Detail Number")
        if detail_param:
            detail_number = detail_param.AsString()
            if detail_number:
                old_name = view.Name
                try:
                    view.Name = detail_number
                    output.print_md("✅ Set view name to `'{}'` from `'{}'` for view ID `{}`".format(
                        detail_number, old_name, view.Id
                    ))
                except Exception as e:
                    output.print_md("❌ Failed to set view name for view ID `{}`: {}".format(view.Id, str(e)))
            else:
                output.print_md("⚠️ Viewport has no detail number set.")
        else:
            output.print_md("⚠️ Could not find 'Detail Number' parameter on viewport ID `{}`".format(vp.Id))
