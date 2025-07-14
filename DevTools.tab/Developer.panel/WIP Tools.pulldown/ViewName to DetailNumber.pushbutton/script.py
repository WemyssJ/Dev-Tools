# -*- coding: utf-8 -*-
from pyrevit import revit, DB, script
import re

doc = revit.doc
uidoc = revit.uidoc
output = script.get_output()
output.set_title("Copy View Name to Detail Number (Selected Viewports)")

# Function to remove all non-alphanumeric characters
def sanitize_for_detail_number(view_name):
    # Keep letters, numbers, dashes, underscores, slashes, and dots
    return re.sub(r'[^A-Za-z0-9_\-/.]', '', view_name)


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

with revit.Transaction("Copy View Name to Detail Number (Selected Viewports)"):
    for vp in selected_viewports:
        view = doc.GetElement(vp.ViewId)
        sheet = doc.GetElement(vp.SheetId)

        if view and sheet:
            new_detail_num = sanitize_for_detail_number(view.Name)

            # Ensure uniqueness on the sheet
            other_vps = [
                doc.GetElement(vid)
                for vid in sheet.GetAllViewports()
                if vid != vp.Id
            ]
            used_detail_nums = []
            for other in other_vps:
                param = other.LookupParameter("Detail Number")
                if param:
                    used_detail_nums.append(param.AsString())

            base = new_detail_num
            i = 1
            while new_detail_num in used_detail_nums:
                new_detail_num = "{}{}".format(base, i)
                i += 1

            detail_param = vp.LookupParameter("Detail Number")
            if detail_param:
                detail_param.Set(new_detail_num)
                output.print_md("✅ Set detail number to `{}` for view `{}` on sheet `{}`".format(
                    new_detail_num, view.Name, sheet.SheetNumber
                ))
            else:
                output.print_md("⚠️ Could not find 'Detail Number' parameter on viewport with view `{}`".format(view.Name))
