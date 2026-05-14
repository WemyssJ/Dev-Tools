# -*- coding: utf-8 -*-
#
# PYREVIT / REVIT PYTHON SHELL
# FIND DOUBLE-STACKED STRUCTURAL ELEMENTS
#
# Checks ONLY:
# - Structural Framing
# - Structural Columns
# - Structural Connections
#
# Includes:
# - PyRevit progress bar
# - Cancel support
# - Automatic selection of duplicates
#

from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import *

from pyrevit import forms

import clr
from collections import defaultdict

clr.AddReference("System")
from System.Collections.Generic import List

# -------------------------------------------------------------------
# REVIT REFERENCES
# -------------------------------------------------------------------

uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

# -------------------------------------------------------------------
# SETTINGS
# -------------------------------------------------------------------

TOLERANCE = 0.001  # feet (~0.3mm)

TARGET_CATEGORIES = [
    BuiltInCategory.OST_StructuralFraming,
    BuiltInCategory.OST_StructuralColumns,
    BuiltInCategory.OST_StructConnections
]

# -------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------

def round_xyz(xyz):
    return (
        round(xyz.X / TOLERANCE),
        round(xyz.Y / TOLERANCE),
        round(xyz.Z / TOLERANCE)
    )


def get_bbox_data(element):

    bbox = element.get_BoundingBox(None)

    if not bbox:
        return None

    min_pt = bbox.Min
    max_pt = bbox.Max

    centre = XYZ(
        (min_pt.X + max_pt.X) / 2.0,
        (min_pt.Y + max_pt.Y) / 2.0,
        (min_pt.Z + max_pt.Z) / 2.0
    )

    size = XYZ(
        abs(max_pt.X - min_pt.X),
        abs(max_pt.Y - min_pt.Y),
        abs(max_pt.Z - min_pt.Z)
    )

    return (
        round_xyz(centre),
        round_xyz(size)
    )


def get_family_type_name(element):

    try:

        type_id = element.GetTypeId()

        if type_id == ElementId.InvalidElementId:
            return "No Type"

        element_type = doc.GetElement(type_id)

        if not element_type:
            return "Unknown Type"

        family_name = ""

        try:
            family_name = element_type.FamilyName
        except:
            pass

        type_name = element_type.Name

        return "{} : {}".format(family_name, type_name)

    except:
        return "Unknown"


# -------------------------------------------------------------------
# CATEGORY FILTER
# -------------------------------------------------------------------

category_filters = List[ElementFilter]()

for bic in TARGET_CATEGORIES:
    category_filters.Add(ElementCategoryFilter(bic))

multi_cat_filter = LogicalOrFilter(category_filters)

# -------------------------------------------------------------------
# COLLECT ELEMENTS
# -------------------------------------------------------------------

elements = list(
    FilteredElementCollector(doc)
    .WherePasses(multi_cat_filter)
    .WhereElementIsNotElementType()
    .ToElements()
)

total = len(elements)

print("\nScanning {} structural elements...\n".format(total))

grouped = defaultdict(list)

# -------------------------------------------------------------------
# PROCESS ELEMENTS WITH PROGRESS BAR
# -------------------------------------------------------------------

with forms.ProgressBar(
    title='Checking Structural Elements ({value} of {max_value})',
    cancellable=True
) as pb:

    for i, elem in enumerate(elements):

        # Cancel support
        if pb.cancelled:
            print("\nOperation cancelled by user.")
            script.exit()

        pb.update_progress(i + 1, total)

        try:

            if elem.Category is None:
                continue

            if elem.ViewSpecific:
                continue

            bbox_data = get_bbox_data(elem)

            if not bbox_data:
                continue

            category_name = elem.Category.Name
            family_type = get_family_type_name(elem)

            # UNIQUE MATCH KEY
            key = (
                category_name,
                family_type,
                bbox_data
            )

            grouped[key].append(elem)

        except:
            pass

# -------------------------------------------------------------------
# FIND DUPLICATES
# -------------------------------------------------------------------

duplicate_groups = []

for key, elems in grouped.items():

    if len(elems) > 1:
        duplicate_groups.append(elems)

# -------------------------------------------------------------------
# OUTPUT + SELECT
# -------------------------------------------------------------------

if duplicate_groups:

    print("===================================================")
    print("STRUCTURAL DUPLICATES FOUND")
    print("===================================================\n")

    selection_ids = List[ElementId]()
    total_duplicates = 0

    for i, group in enumerate(duplicate_groups):

        sample = group[0]

        print("GROUP {}".format(i + 1))
        print("-------------------------------------------")

        print("Category : {}".format(sample.Category.Name))
        print("Type     : {}".format(get_family_type_name(sample)))
        print("Instances : {}\n".format(len(group)))

        for elem in group:

            print("  Element ID: {}".format(elem.Id.IntegerValue))

            selection_ids.Add(elem.Id)
            total_duplicates += 1

        print("")

    # Select duplicates
    uidoc.Selection.SetElementIds(selection_ids)

    # Zoom to selection
    try:
        uidoc.ShowElements(selection_ids)
    except:
        pass

    TaskDialog.Show(
        "Structural Duplicates Found",
        "{} duplicate groups found.\n\n"
        "{} total duplicate elements selected.".format(
            len(duplicate_groups),
            total_duplicates
        )
    )

else:

    print("No structural duplicates found.")

    TaskDialog.Show(
        "Duplicate Elements",
        "No duplicate structural elements found."
    )