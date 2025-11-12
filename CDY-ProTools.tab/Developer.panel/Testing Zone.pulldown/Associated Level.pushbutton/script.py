# -*- coding: utf-8 -*-
__doc__ = "Select elements where the selected level is base or top level"

from pyrevit import revit, forms
from Autodesk.Revit.DB import FilteredElementCollector, Level, BuiltInParameter, ElementId
from System.Collections.Generic import List

doc = revit.doc
uidoc = revit.uidoc

# Ask user to select a level
levels = list(FilteredElementCollector(doc).OfClass(Level))
level_names = [lvl.Name for lvl in levels]

selected_level_name = forms.SelectFromList.show(
    level_names,
    title="Select a Level",
    multiselect=False
)

if selected_level_name:
    selected_level = [lvl for lvl in levels if lvl.Name == selected_level_name][0]
    selected_level_id = selected_level.Id

    all_elements = FilteredElementCollector(doc).WhereElementIsNotElementType()
    elements_on_level = []

    for e in all_elements:
        # 1) Base/reference level
        base_param = e.get_Parameter(BuiltInParameter.LEVEL_PARAM)
        ref_param = e.get_Parameter(BuiltInParameter.INSTANCE_REFERENCE_LEVEL_PARAM)

        if (base_param and base_param.HasValue and base_param.AsElementId() == selected_level_id) \
            or (ref_param and ref_param.HasValue and ref_param.AsElementId() == selected_level_id):
            elements_on_level.append(e)
            continue

        # 2) Wall top constraint
        wall_top = e.get_Parameter(BuiltInParameter.WALL_HEIGHT_TYPE)
        if wall_top and wall_top.HasValue and wall_top.AsElementId() == selected_level_id:
            elements_on_level.append(e)
            continue

        # 3) Look for any parameter named "Top Level" (columns, beams, structural)
        top_level_param = e.LookupParameter("Top Level")
        if top_level_param and top_level_param.HasValue and top_level_param.AsElementId() == selected_level_id:
            elements_on_level.append(e)
            continue

    # Convert list of ElementIds to ICollection[ElementId]
    element_ids = List[ElementId]([e.Id for e in elements_on_level])

    # Select elements in Revit
    uidoc.Selection.SetElementIds(element_ids)

    forms.alert("Selected {} elements on level: {}".format(len(elements_on_level), selected_level_name))
else:
    forms.alert("Operation cancelled")
