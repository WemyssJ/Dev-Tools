# -*- coding: utf-8 -*-
#============================================ IMPORTS

import sys
import clr
clr.AddReference('RevitAPI')

from Autodesk.Revit.DB import *
from pyrevit import forms

#============================================ VARIABLES
uidoc  = __revit__.ActiveUIDocument
doc    = uidoc.Document  # type: Document
active_view = doc.ActiveView  # source view

#============================================ FUNCTIONS

def clone_override(ogs):
    """Clone an OverrideGraphicSettings with all properties"""
    if not ogs:
        return OverrideGraphicSettings()
    new_ogs = OverrideGraphicSettings()
    new_ogs.SetCutLineColor(ogs.CutLineColor)
    new_ogs.SetProjectionLineColor(ogs.ProjectionLineColor)

    new_ogs.SetCutLinePatternId(ogs.CutLinePatternId)
    new_ogs.SetProjectionLinePatternId(ogs.ProjectionLinePatternId)

    new_ogs.SetCutForegroundPatternId(ogs.CutForegroundPatternId)
    new_ogs.SetCutForegroundPatternColor(ogs.CutForegroundPatternColor)
    new_ogs.SetCutBackgroundPatternId(ogs.CutBackgroundPatternId)
    new_ogs.SetCutBackgroundPatternColor(ogs.CutBackgroundPatternColor)

    new_ogs.SetSurfaceForegroundPatternId(ogs.SurfaceForegroundPatternId)
    new_ogs.SetSurfaceForegroundPatternColor(ogs.SurfaceForegroundPatternColor)
    new_ogs.SetSurfaceBackgroundPatternId(ogs.SurfaceBackgroundPatternId)
    new_ogs.SetSurfaceBackgroundPatternColor(ogs.SurfaceBackgroundPatternColor)

    new_ogs.SetHalftone(ogs.Halftone)
    new_ogs.SetSurfaceTransparency(ogs.Transparency)
    return new_ogs


#============================================ MAIN

# Collect filters applied to current view
applied_filter_ids = active_view.GetFilters()
if not applied_filter_ids:
    forms.alert("No filters are applied to the active view.", exitscript=True)

viewfilters = [doc.GetElement(fid) for fid in applied_filter_ids]
viewfilternames = [vf.Name for vf in viewfilters]

# Let user pick one or more from active view
selected_names = forms.SelectFromList.show(viewfilternames,
                                           button_name='Select Filters',
                                           title='Select One or More Filters from Active View',
                                           multiselect=True)
if not selected_names:
    sys.exit()

selected_filters = [viewfilters[viewfilternames.index(name)] for name in selected_names]

# Pick target templates
target_templates = forms.select_viewtemplates(title='Select View Templates to Apply Filters To',
                                              button_name='Select Templates',
                                              multiple=True)
if not target_templates:
    sys.exit()

# Apply overrides
t = Transaction(doc, 'Copy View Filters to Templates')
t.Start()
for vf in selected_filters:
    try:
        ogs = active_view.GetFilterOverrides(vf.Id)
        override = clone_override(ogs)

        for template in target_templates:
            try:
                if not template.IsFilterApplied(vf.Id):
                    template.AddFilter(vf.Id)
                template.SetFilterOverrides(vf.Id, override)
                print("Applied filter '{0}' to template '{1}'".format(vf.Name, template.Name))
            except Exception as e:
                print("Failed filter '{0}' on template '{1}': {2}".format(vf.Name, template.Name, str(e)))
    except Exception as e:
        print("Could not process filter '{0}': {1}".format(vf.Name, str(e)))
t.Commit()
