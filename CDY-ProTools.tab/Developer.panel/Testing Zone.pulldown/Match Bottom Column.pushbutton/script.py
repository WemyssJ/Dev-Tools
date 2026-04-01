# -*- coding: utf-8 -*-
"""Match Column Base Level + Offset"""

from pyrevit import revit, DB, forms
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
from Autodesk.Revit.Exceptions import OperationCanceledException

doc = revit.doc
uidoc = revit.uidoc


# -------------------------------
# Selection Filter for Columns
# -------------------------------
class ColumnSelectionFilter(ISelectionFilter):
    def AllowElement(self, element):
        if element.Category:
            return element.Category.Id.IntegerValue == int(DB.BuiltInCategory.OST_StructuralColumns)
        return False

    def AllowReference(self, reference, point):
        return True


# -------------------------------
# Pick Source Column
# -------------------------------
try:
    source_ref = uidoc.Selection.PickObject(
        ObjectType.Element,
        ColumnSelectionFilter(),
        "Pick SOURCE column"
    )
except OperationCanceledException:
    forms.alert("Cancelled")
    script.exit()

source_col = doc.GetElement(source_ref.ElementId)

# -------------------------------
# Get Parameters
# -------------------------------
base_level_param = source_col.get_Parameter(DB.BuiltInParameter.FAMILY_BASE_LEVEL_PARAM)
base_offset_param = source_col.get_Parameter(DB.BuiltInParameter.FAMILY_BASE_LEVEL_OFFSET_PARAM)

if not base_level_param or not base_offset_param:
    forms.alert("Could not read base level/offset from source column.")
    script.exit()

base_level = base_level_param.AsElementId()
base_offset = base_offset_param.AsDouble()

# -------------------------------
# Pick Target Columns
# -------------------------------
try:
    target_refs = uidoc.Selection.PickObjects(
        ObjectType.Element,
        ColumnSelectionFilter(),
        "Pick TARGET columns"
    )
except OperationCanceledException:
    forms.alert("Cancelled")
    script.exit()

target_cols = [doc.GetElement(ref.ElementId) for ref in target_refs]

# -------------------------------
# Apply Values
# -------------------------------
with revit.Transaction("Match Column Base Level + Offset"):
    for col in target_cols:
        lvl_param = col.get_Parameter(DB.BuiltInParameter.FAMILY_BASE_LEVEL_PARAM)
        off_param = col.get_Parameter(DB.BuiltInParameter.FAMILY_BASE_LEVEL_OFFSET_PARAM)

        if lvl_param and off_param:
            lvl_param.Set(base_level)
            off_param.Set(base_offset)

forms.alert("Done! Updated {} columns.".format(len(target_cols)))