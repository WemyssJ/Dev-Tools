# -*- coding: utf-8 -*-
"""
Excel → Revit Parameter Import / Export
Compatible with Revit 2023+
-------------------------------------------------------
When clicked: Prompts to choose Import or Export
Exports selected elements to CSV or imports CSV values into Revit
-------------------------------------------------------
"""

from Autodesk.Revit.DB import (
    UnitUtils,
    SpecTypeId,
    UnitTypeId,
    Transaction,
)
from pyrevit import revit, forms, script, DB
import csv
import os

output = script.get_output()
logger = script.get_logger()


# ----------------------------------------------------------------------
# UNIT CONVERSION HELPERS
# ----------------------------------------------------------------------
def convert_from_internal(val_internal, param):
    try:
        spec = param.Definition.GetDataType()
        if spec == SpecTypeId.Length:
            return UnitUtils.ConvertFromInternalUnits(val_internal, UnitTypeId.Meters)
        elif spec == SpecTypeId.Area:
            return UnitUtils.ConvertFromInternalUnits(val_internal, UnitTypeId.SquareMeters)
        elif spec == SpecTypeId.Volume:
            return UnitUtils.ConvertFromInternalUnits(val_internal, UnitTypeId.CubicMeters)
        elif spec == SpecTypeId.Angle:
            return UnitUtils.ConvertFromInternalUnits(val_internal, UnitTypeId.Degrees)
        elif spec == SpecTypeId.Force:
            return UnitUtils.ConvertFromInternalUnits(val_internal, UnitTypeId.Kilonewtons)
        elif spec == SpecTypeId.Moment:
            return UnitUtils.ConvertFromInternalUnits(val_internal, UnitTypeId.KilonewtonMeters)
        elif spec == SpecTypeId.Stress:
            return UnitUtils.ConvertFromInternalUnits(val_internal, UnitTypeId.KilonewtonsPerSquareMeter)
        elif spec == SpecTypeId.Displacement:
            return UnitUtils.ConvertFromInternalUnits(val_internal, UnitTypeId.Millimeters)
        else:
            return val_internal
    except Exception as ex:
        logger.warning("Unit conversion failed for '{}': {}".format(param.Definition.Name, ex))
        return val_internal


def convert_to_internal(val_display, param):
    try:
        val = float(val_display)
    except Exception:
        return val_display

    try:
        spec = param.Definition.GetDataType()
        if spec == SpecTypeId.Length:
            return UnitUtils.ConvertToInternalUnits(val, UnitTypeId.Meters)
        elif spec == SpecTypeId.Area:
            return UnitUtils.ConvertToInternalUnits(val, UnitTypeId.SquareMeters)
        elif spec == SpecTypeId.Volume:
            return UnitUtils.ConvertToInternalUnits(val, UnitTypeId.CubicMeters)
        elif spec == SpecTypeId.Angle:
            return UnitUtils.ConvertToInternalUnits(val, UnitTypeId.Degrees)
        elif spec == SpecTypeId.Force:
            return UnitUtils.ConvertToInternalUnits(val, UnitTypeId.Kilonewtons)
        elif spec == SpecTypeId.Moment:
            return UnitUtils.ConvertToInternalUnits(val, UnitTypeId.KilonewtonMeters)
        elif spec == SpecTypeId.Stress:
            return UnitUtils.ConvertToInternalUnits(val, UnitTypeId.KilonewtonsPerSquareMeter)
        elif spec == SpecTypeId.Displacement:
            return UnitUtils.ConvertToInternalUnits(val, UnitTypeId.Millimeters)
        else:
            return val
    except Exception as ex:
        logger.warning("Unit conversion failed for '{}': {}".format(param.Definition.Name, ex))
        return val_display


def is_editable(param):
    try:
        return not param.IsReadOnly and param.Definition.Name not in [
            "Category", "Family", "Type Name", "Level", "Phase Created",
            "Phase Demolished", "Workset", "Constraints", "Base Constraint",
            "Rebar Cover", "Unconnected Height"
        ]
    except Exception:
        return False


def get_param_value(param):
    try:
        if param.StorageType == DB.StorageType.String:
            return param.AsString() or ""
        elif param.StorageType == DB.StorageType.Integer:
            return str(param.AsInteger())
        elif param.StorageType == DB.StorageType.ElementId:
            return str(param.AsElementId().IntegerValue)
        elif param.StorageType == DB.StorageType.Double:
            return str(convert_from_internal(param.AsDouble(), param))
    except Exception as ex:
        logger.warning("Failed to read '{}': {}".format(param.Definition.Name, ex))
        return ""
    return ""


def set_param_value(param, value):
    try:
        if param.StorageType == DB.StorageType.String:
            param.Set(value)
        elif param.StorageType == DB.StorageType.Integer:
            param.Set(int(value))
        elif param.StorageType == DB.StorageType.ElementId:
            param.Set(DB.ElementId(int(value)))
        elif param.StorageType == DB.StorageType.Double:
            param.Set(convert_to_internal(value, param))
        return True
    except Exception as ex:
        logger.warning("Failed to set '{}': {}".format(param.Definition.Name, ex))
        return False


# ----------------------------------------------------------------------
# USER MODE SELECTION
# ----------------------------------------------------------------------
mode = forms.alert(
    "Would you like to Export selected elements to CSV or Import parameters from CSV?",
    options=["Export to CSV", "Import from CSV", "Cancel"],
    title="Revit Parameter Import/Export"
)

if not mode or mode == "Cancel":
    script.exit()


# ----------------------------------------------------------------------
# EXPORT MODE
# ----------------------------------------------------------------------
if mode == "Export to CSV":
    selection = [revit.doc.GetElement(elid) for elid in revit.uidoc.Selection.GetElementIds()]
    if not selection:
        forms.alert("Please select elements to export.", exitscript=True)

    file_path = forms.save_file(file_ext="csv", title="Save exported CSV file as...")
    if not file_path:
        forms.alert("No file selected. Exiting.", exitscript=True)

    all_param_names = sorted(list(set(
        [p.Definition.Name for el in selection for p in el.Parameters if is_editable(p)]
    )))

    header = ["ElementId", "Name"] + all_param_names

    with open(file_path, "wb") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for el in selection:
            row = [el.Id.IntegerValue, el.Name]
            param_dict = dict()
            for p in el.Parameters:
                if is_editable(p):
                    param_dict[p.Definition.Name] = get_param_value(p)
            for pname in all_param_names:
                row.append(param_dict.get(pname, ""))
            writer.writerow(row)

    forms.alert("Export complete!\n\nCSV saved to:\n{}".format(file_path))


# ----------------------------------------------------------------------
# IMPORT MODE
# ----------------------------------------------------------------------
elif mode == "Import from CSV":
    file_path = forms.pick_file(file_ext="csv", title="Select CSV file to import")
    if not file_path or not os.path.exists(file_path):
        forms.alert("CSV file not found or not selected.", exitscript=True)

    with open(file_path, "rb") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        forms.alert("CSV file is empty.", exitscript=True)

    header = rows[0]
    elementid_idx = header.index("ElementId")
    param_indices = dict((name, idx) for idx, name in enumerate(header) if name not in ["ElementId", "Name"])

    t = Transaction(revit.doc, "Import Parameters from CSV")
    t.Start()

    updated = 0
    for row in rows[1:]:
        try:
            el_id = int(row[elementid_idx])
            el = revit.doc.GetElement(DB.ElementId(el_id))
            if not el:
                continue
            for pname, idx in param_indices.items():
                param = el.LookupParameter(pname)
                if param and is_editable(param):
                    set_param_value(param, row[idx])
            updated += 1
        except Exception as ex:
            logger.warning("Failed element {}: {}".format(row[0], ex))

    t.Commit()

    forms.alert("Import complete!\n\nUpdated parameters for {} elements.".format(updated))
