# -*- coding: utf-8 -*-
"""
Export/Import only editable/writeable Element Parameters to/from Excel (CSV)

Shift-Click: Import parameters from CSV back into Revit by ElementId automatically.
"""

import os
import os.path as op
import csv
from pyrevit import forms, revit, DB, script
from pyrevit import coreutils

logger = script.get_logger()
output = script.get_output()

# Helper functions
def is_editable(param):
    """Return True if parameter is writeable/editable"""
    try:
        return not param.IsReadOnly and param.Definition.Name not in {
            "Category", "Family", "Type Name", "Base Constraint", "G.Associated Level",
            "Workset", "Level", "Phase Created", "Phase Demolished", "Constraints",
            "Rebar Cover", "Unconnected Height"
        }
    except:
        return False

def get_param_value(param):
    try:
        if param.StorageType == DB.StorageType.String:
            return param.AsString() or ""
        elif param.StorageType == DB.StorageType.Integer:
            return str(param.AsInteger())
        elif param.StorageType == DB.StorageType.Double:
            return str(param.AsDouble())
        elif param.StorageType == DB.StorageType.ElementId:
            return str(param.AsElementId().IntegerValue)
    except:
        return ""
    return ""

def set_param_value(param, value):
    try:
        if param.StorageType == DB.StorageType.String:
            param.Set(value)
        elif param.StorageType == DB.StorageType.Integer:
            param.Set(int(value))
        elif param.StorageType == DB.StorageType.Double:
            param.Set(float(value))
        elif param.StorageType == DB.StorageType.ElementId:
            param.Set(DB.ElementId(int(value)))
        return True
    except:
        return False

# EXPORT
if not __shiftclick__:
    # Get selected elements
    selection = [revit.doc.GetElement(elid) for elid in revit.uidoc.Selection.GetElementIds()]
    if not selection:
        forms.alert("Please select elements first.", exitscript=True)

    # Ask user for file name to export
    file_path = forms.save_file(file_ext="csv", title="Select Export File Name")
    if not file_path:
        forms.alert("No file selected, exiting.", exitscript=True)

    # Gather all editable parameters
    all_param_names = set()
    for el in selection:
        for p in el.Parameters:
            if is_editable(p):
                all_param_names.add(p.Definition.Name)
    all_param_names = sorted(all_param_names)

    header = ["ElementId", "Name"] + list(all_param_names)

    with open(file_path, "wb") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for el in selection:
            row = [el.Id.IntegerValue, el.Name]
            param_dict = {p.Definition.Name: get_param_value(p) 
                          for p in el.Parameters if is_editable(p)}
            for pname in all_param_names:
                row.append(param_dict.get(pname, ""))
            writer.writerow(row)

    output.print_md("**Export complete!** CSV saved to:\n{}".format(file_path))

# IMPORT
else:
    # Ask user which CSV file to import
    file_path = forms.pick_file(file_ext="csv", title="Select CSV file to import")
    if not file_path or not op.exists(file_path):
        forms.alert("CSV file not found or not selected.", exitscript=True)

    with open(file_path, "rb") as f:
        reader = csv.reader(f)
        rows = list(reader)

    header = rows[0]
    elementid_idx = header.index("ElementId")
    param_indices = {name: idx for idx, name in enumerate(header) if name not in ["ElementId", "Name"]}

    t = DB.Transaction(revit.doc, "Import Parameters from CSV")
    t.Start()
    for row in rows[1:]:
        try:
            el_id = int(row[elementid_idx])
            el = revit.doc.GetElement(DB.ElementId(el_id))
            if not el:
                logger.warning("ElementId {} not found in project.".format(el_id))
                continue
            for pname, idx in param_indices.items():
                param = el.LookupParameter(pname)
                if param and is_editable(param):
                    set_param_value(param, row[idx])
        except Exception as ex:
            logger.warning("Failed to set parameter for element {}: {}".format(el_id, ex))
    t.Commit()
    output.print_md("**Import complete!** Parameters updated in Revit by ElementId.")
