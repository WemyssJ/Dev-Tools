# -*- coding: utf-8 -*-
from pyrevit import revit, DB, script

doc = revit.doc
uidoc = revit.uidoc
output = script.get_output()
output.set_title("Copy Detail Number to View Name (Selected Viewports, Two-Step + Rollback)")

selection_ids = uidoc.Selection.GetElementIds()
if not selection_ids:
    output.print_md("No elements selected. Please select one or more viewports.")
    script.exit()

selected_viewports = [doc.GetElement(eid) for eid in selection_ids if isinstance(doc.GetElement(eid), DB.Viewport)]

if not selected_viewports:
    output.print_md("No viewports selected. Please select one or more viewport elements.")
    script.exit()

# Dictionary to track original -> temp name
temp_names = {}
temp_suffix = "_temp"

# STEP 1: Temporarily rename views
with revit.Transaction("Temporarily Rename Views"):
    for vp in selected_viewports:
        view = doc.GetElement(vp.ViewId)
        if view:
            try:
                original_name = view.Name
                temp_name = "{}{}".format(original_name, temp_suffix)
                view.Name = temp_name
                temp_names[view.Id.IntegerValue] = (original_name, temp_name)
            except Exception as e:
                output.print_md("⚠️ Could not temporarily rename view ID `{}`: {}".format(view.Id, str(e)))

# STEP 2: Set final names from detail numbers with rollback on failure
try:
    with revit.Transaction("Set View Name from Detail Number"):
        existing_names = set(v.Name for v in DB.FilteredElementCollector(doc).OfClass(DB.View))

        for vp in selected_viewports:
            view = doc.GetElement(vp.ViewId)
            if not view:
                output.print_md("⚠️ Could not find view for viewport ID: {}".format(vp.Id))
                continue

            detail_param = vp.LookupParameter("Detail Number")
            if not detail_param:
                output.print_md("⚠️ No 'Detail Number' found for viewport ID `{}`".format(vp.Id))
                continue

            detail_number = detail_param.AsString()
            if not detail_number:
                output.print_md("⚠️ Empty detail number for viewport ID `{}`".format(vp.Id))
                continue

            base_name = detail_number
            new_name = base_name
            i = 1
            while new_name in existing_names:
                new_name = "{}_{}".format(base_name, i)
                i += 1

            old_name, temp_name = temp_names.get(view.Id.IntegerValue, ("?", view.Name))
            try:
                view.Name = new_name
                existing_names.add(new_name)
                output.print_md("✅ Set view name from `'{}'` → `'{}'` → `'{}'` for view ID `{}`".format(
                    old_name, temp_name, new_name, view.Id.IntegerValue
                ))
            except Exception as e:
                raise Exception("❌ Failed to set view name for view ID `{}`: {}".format(view.Id, str(e)))

except Exception as e:
    output.print_md("\n❌ Error during renaming process: {}\n🔄 Rolling back to original names...".format(e))
    with revit.Transaction("Rollback View Names"):
        for vp in selected_viewports:
            view = doc.GetElement(vp.ViewId)
            if view and view.Id.IntegerValue in temp_names:
                original, temp = temp_names[view.Id.IntegerValue]
                try:
                    view.Name = original
                    output.print_md("↩️ Rolled back view ID `{}` to original name `'{}'`".format(view.Id.IntegerValue, original))
                except Exception as rollback_err:
                    output.print_md("⚠️ Failed to roll back view ID `{}`: {}".format(view.Id.IntegerValue, rollback_err))
