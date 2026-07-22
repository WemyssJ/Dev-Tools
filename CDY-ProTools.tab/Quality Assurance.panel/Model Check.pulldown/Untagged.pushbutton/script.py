# -*- coding: utf-8 -*-
# pylint: skip-file

__title__ = "Select Untagged in View"
__author__ = "Your Name"

from pyrevit import forms, revit
from Autodesk.Revit.DB import (
    FilteredElementCollector,
    IndependentTag,
    ElementCategoryFilter,
    ElementId
)
from System.Collections.Generic import List

doc = revit.doc
uidoc = revit.uidoc
view = doc.ActiveView

##############################################################################################
# TELEMETRY IMPORTS #
##############################################################################################
# Only works IF specified TELEMETRY_JSON path exists within %AppData%\pyRevit\Extensions\BIMTools.extension\lib\telemetry_auto.py"
# Records tool usage by date & revit version
import os, sys

# Add lib folder for telemetry_auto
lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'lib'))
if lib_path not in sys.path:
    sys.path.append(lib_path)

import telemetry_auto

tool_name = os.path.basename(os.path.dirname(__file__)) 
TOOL_NAME = tool_name.replace(".pushbutton", "")
telemetry_auto.log_tool_usage(TOOL_NAME)
##############################################################################################

# ------------------------------------------------------------
# STEP 1: Get all model categories in the view
# ------------------------------------------------------------

collector = FilteredElementCollector(doc, view.Id).WhereElementIsNotElementType()
elements_in_view = list(collector)

categories = {}
for el in elements_in_view:
    if el.Category and el.Category.HasMaterialQuantities:
        categories[el.Category.Name] = el.Category

if not categories:
    forms.alert("No valid model categories found in this view.")
    script.exit()

# ------------------------------------------------------------
# STEP 2: Prompt user to select category
# ------------------------------------------------------------

selected_cat_name = forms.SelectFromList.show(
    sorted(categories.keys()),
    title="Select Category to Check for Untagged Elements",
    multiselect=False
)

if not selected_cat_name:
    script.exit()

selected_category = categories[selected_cat_name]

# ------------------------------------------------------------
# STEP 3: Collect all elements of that category in active view
# ------------------------------------------------------------

category_filter = ElementCategoryFilter(selected_category.Id)
elements = list(
    FilteredElementCollector(doc, view.Id)
    .WherePasses(category_filter)
    .WhereElementIsNotElementType()
)

if not elements:
    forms.alert("No elements of that category found in this view.")
    script.exit()

# ------------------------------------------------------------
# STEP 4: Collect all tags in active view that reference elements
# ------------------------------------------------------------

tags = FilteredElementCollector(doc, view.Id).OfClass(IndependentTag).ToElements()
tagged_element_ids = set()

for tag in tags:
    try:
        refs = tag.GetTaggedElementIds()
        for ref in refs:
            if ref.HostElementId != ElementId.InvalidElementId:
                tagged_element_ids.add(ref.HostElementId)
    except:
        continue

# ------------------------------------------------------------
# STEP 5: Find untagged elements
# ------------------------------------------------------------

untagged_ids = [el.Id for el in elements if el.Id not in tagged_element_ids]

if not untagged_ids:
    forms.alert("All elements of this category are tagged in this view.")
    script.exit()

# ------------------------------------------------------------
# STEP 6: Select untagged elements (IronPython ICollection fix)
# ------------------------------------------------------------

untagged_element_ids = List[ElementId](untagged_ids)
uidoc.Selection.SetElementIds(untagged_element_ids)

forms.alert(
    "{} untagged elements selected.".format(len(untagged_ids)),
    title="Done"
)