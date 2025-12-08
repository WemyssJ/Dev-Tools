# -*- coding: utf-8 -*-
import os
import clr
clr.AddReference("PresentationFramework")
from pyrevit import revit, forms, script
from Autodesk.Revit.DB import (
    FilteredElementCollector,
    BuiltInCategory,
    Level,
    BuiltInParameter,
    ElementId
)
from System.Collections.Generic import List
from System import Uri
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption

doc = revit.doc
uidoc = revit.uidoc

# --- Paths ---
script_dir = os.path.dirname(__file__) 
xaml_path = os.path.join(script_dir, "AssociatedUI.xaml")

# --- WPF Window Class ---
class MasterSelectWindow(forms.WPFWindow):
    def __init__(self):
        super(MasterSelectWindow, self).__init__(xaml_path)

        # Set header icon
        icon_path = os.path.join(script_dir, "icon.png")
        if os.path.exists(icon_path):
            bmp = BitmapImage()
            bmp.BeginInit()
            bmp.UriSource = Uri(icon_path)
            bmp.CacheOption = BitmapCacheOption.OnLoad
            bmp.EndInit()
            header_icon = self.FindName("headerIcon")
            if header_icon:
                header_icon.Source = bmp

        # Get buttons
        self.btnWorkPlane = self.FindName("btnWorkPlane")
        self.btnLevel = self.FindName("btnLevel")
        self.cancelBtn = self.FindName("cancelBtn")

        # Attach events
        if self.btnWorkPlane:
            self.btnWorkPlane.Click += self.select_by_workplane
        if self.btnLevel:
            self.btnLevel.Click += self.select_by_level
        if self.cancelBtn:
            self.cancelBtn.Click += self.cancel


    # ------------------ Work Plane Selection ------------------
    def select_by_workplane(self, sender, args):
        ref_planes = list(FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_CLines))
        ref_plane_names = [(rp.Name if rp.Name else "<unnamed>") for rp in ref_planes]

        selected_plane_name = forms.SelectFromList.show(
            ref_plane_names,
            title="Select a Reference Plane / Work Plane",
            multiselect=False
        )
        if not selected_plane_name:
            forms.alert("Operation cancelled")
            return

        expected_string = "Reference Plane : {}".format(selected_plane_name)
        framing_elements = FilteredElementCollector(doc) \
            .OfCategory(BuiltInCategory.OST_StructuralFraming) \
            .WhereElementIsNotElementType() \
            .ToElements()

        matches = [e for e in framing_elements if e.LookupParameter("Work Plane") and
                   e.LookupParameter("Work Plane").AsString() == expected_string]

        element_ids = List[ElementId]([x.Id for x in matches])
        uidoc.Selection.SetElementIds(element_ids)

        forms.alert("Selected {} structural framing elements on: {}".format(
            len(matches),
            selected_plane_name
        ))

        # Close window after operation
        self.Close()

    # ------------------ Level Selection (MULTI-SELECT) ------------------
    def select_by_level(self, sender, args):
        levels = list(FilteredElementCollector(doc).OfClass(Level))
        level_names = [lvl.Name for lvl in levels]

        selected_level_names = forms.SelectFromList.show(
            level_names,
            title="Select Level(s)",
            multiselect=True
        )
        if not selected_level_names:
            forms.alert("Operation cancelled")
            return

        # Convert names -> Level objects
        selected_levels = [lvl for lvl in levels if lvl.Name in selected_level_names]
        selected_level_ids = {lvl.Id for lvl in selected_levels}   # use a set for fast lookup

        all_elements = FilteredElementCollector(doc).WhereElementIsNotElementType()
        elements_on_levels = []

        for e in all_elements:
            # Base level
            base_param = e.get_Parameter(BuiltInParameter.LEVEL_PARAM)
            if base_param and base_param.HasValue and base_param.AsElementId() in selected_level_ids:
                elements_on_levels.append(e)
                continue

            # Ref level
            ref_param = e.get_Parameter(BuiltInParameter.INSTANCE_REFERENCE_LEVEL_PARAM)
            if ref_param and ref_param.HasValue and ref_param.AsElementId() in selected_level_ids:
                elements_on_levels.append(e)
                continue

            # Wall top constraint
            wall_top = e.get_Parameter(BuiltInParameter.WALL_HEIGHT_TYPE)
            if wall_top and wall_top.HasValue and wall_top.AsElementId() in selected_level_ids:
                elements_on_levels.append(e)
                continue

            # Generic "Top Level"
            top_level_param = e.LookupParameter("Top Level")
            if top_level_param and top_level_param.HasValue and top_level_param.AsElementId() in selected_level_ids:
                elements_on_levels.append(e)
                continue

        # Select results in Revit
        element_ids = List[ElementId]([e.Id for e in elements_on_levels])
        uidoc.Selection.SetElementIds(element_ids)

        forms.alert(
            "Selected {} elements on {} levels:\n{}".format(
                len(elements_on_levels),
                len(selected_level_names),
                ", ".join(selected_level_names)
            )
        )

        self.Close()


    # ------------------ Cancel ------------------
    def cancel(self, sender, args):
        self.Close()


# ------------------ Main Execution ------------------
try:
    window = MasterSelectWindow()
    window.show_dialog()
except Exception as e:
    forms.alert("Error initializing window: {}".format(str(e)))
