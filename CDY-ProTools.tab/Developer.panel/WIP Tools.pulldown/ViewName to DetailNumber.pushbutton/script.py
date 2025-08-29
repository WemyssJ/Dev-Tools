# -*- coding: utf-8 -*-
from pyrevit import revit, DB, script
import re

doc = revit.doc
uidoc = revit.uidoc
output = script.get_output()
output.set_title("Copy View Name to Detail Number (Selected Viewports, Two-Step + Rollback)")

def sanitize_for_detail_number(view_name):
    return re.sub(r'[^A-Za-z0-9_\-/.]', '', view_name)

selection_ids = uidoc.Selection.GetElementIds()
if not selection_ids:
    output.print_md("No elements selected. Please select one or more viewports.")
    script.exit()

selected_viewports = [doc.GetElement(eid) for eid in selection_ids if isinstance(doc.GetElement(eid), DB.Viewport)]

if not selected_viewports:
    output.print_md("No viewports selected. Please select one or more viewport elements.")
    script.exit()

temp_suffix = "_temp"
temp_map = {}

# STEP 1: Apply temporary unique names
with revit.Transaction("Temporarily Rename Detail Numbers"):
    for vp in selected_viewports:
        detail_param = vp.LookupParameter("Detail Number")
        if detail_param:
            original = detail_param.AsString()
            temp_name = "{}{}".format(original if original else "TEMP", temp_suffix)
            detail_param.Set(temp_name)
            temp_map[vp.Id.IntegerValue] = (original, temp_name)

# STEP 2: Apply final sanitized names with rollback logic
try:
    with revit.Transaction("Set Detail Number from View Name"):
        for vp in selected_viewports:
            view = doc.GetElement(vp.ViewId)
            sheet = doc.GetElement(vp.SheetId)
            detail_param = vp.LookupParameter("Detail Number")

            if view and sheet and detail_param:
                base_detail = sanitize_for_detail_number(view.Name)

                other_vps = [
                    doc.GetElement(vid)
                    for vid in sheet.GetAllViewports()
                    if vid != vp.Id
                ]
                used_detail_nums = [
                    other.LookupParameter("Detail Number").AsString()
                    for other in other_vps if other.LookupParameter("Detail Number")
                ]

                new_detail_num = base_detail
                i = 1
                while new_detail_num in used_detail_nums:
                    new_detail_num = "{}{}".format(base_detail, i)
                    i += 1

                original, temp_name = temp_map.get(vp.Id.IntegerValue, ("?", "?"))
                detail_param.Set(new_detail_num)
                output.print_md("✅ Set detail number: `{}` → `{}` → `{}` for view `{}` on sheet `{}`".format(
                    original, temp_name, new_detail_num, view.Name, sheet.SheetNumber
                ))

except Exception as e:
    output.print_md("❌ Error occurred during final renaming: {}. Rolling back to original detail numbers...".format(str(e)))
    with revit.Transaction("Rollback to Original Detail Numbers"):
        for vp in selected_viewports:
            detail_param = vp.LookupParameter("Detail Number")
            if detail_param:
                original, temp_name = temp_map.get(vp.Id.IntegerValue, (None, None))
                if original is not None:
                    detail_param.Set(original)
                    output.print_md("↩️ Rolled back view ID `{}` to original detail number `{}`".format(vp.Id.IntegerValue, original))
                else:
                    output.print_md("⚠️ No original value found to roll back for view ID `{}`".format(vp.Id.IntegerValue))
