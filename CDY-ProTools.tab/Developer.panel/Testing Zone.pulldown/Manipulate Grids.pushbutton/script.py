# -*- coding: utf-8 -*-
import clr
import sys
import os
import math

clr.AddReference("PresentationFramework")
clr.AddReference("PresentationCore")
clr.AddReference("WindowsBase")
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')

from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType
from System.Windows.Markup import XamlReader
from System import Uri
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption
from pyrevit import script
from coordinate_selector import show_coordinate_system_selector

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

# -----------------------------
# Fix IronPython import for custom_grids
# -----------------------------
bundle_dir = os.path.dirname(__file__)
lib_dir = os.path.join(bundle_dir, "lib")
if lib_dir not in sys.path:
    sys.path.append(lib_dir)

from custom_grids import CustomGrids, ToggleGridWindow, GridsCollector

# -----------------------------
# Selection filter
# -----------------------------
class GridSelectionFilter(ISelectionFilter):
    def AllowElement(self, element):
        return isinstance(element, Grid)
    def AllowReference(self, reference, position):
        return False

# -----------------------------
# Load XAML UI
# -----------------------------
xaml_path = script.get_bundle_file('GridManip.xaml')
with open(xaml_path, 'r') as f:
    xaml_str = f.read()
window = XamlReader.Parse(xaml_str)

btn2D = window.FindName("btn2D")
btn3D = window.FindName("btn3D")
btnCoordinate = window.FindName("btnCoordinate")  # Advanced button
cancelBtn = window.FindName("cancelBtn")
headerIcon = window.FindName("headerIcon")

# -----------------------------
# Load icon.png
# -----------------------------
icon_path = os.path.join(bundle_dir, "icon.png")
if os.path.exists(icon_path):
    bmp = BitmapImage()
    bmp.BeginInit()
    bmp.UriSource = Uri(icon_path)
    bmp.CacheOption = BitmapCacheOption.OnLoad
    bmp.EndInit()
    headerIcon.Source = bmp

# -----------------------------
# Result storage
# -----------------------------
result = None
grids = []

uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document
view = uidoc.ActiveView

# -----------------------------
# Prompt user to pick grids if needed
# -----------------------------
def select_grids():
    global grids
    sel_ids = uidoc.Selection.GetElementIds()
    grids = [doc.GetElement(eid) for eid in sel_ids if isinstance(doc.GetElement(eid), Grid)]

    if not grids:
        try:
            picked_refs = uidoc.Selection.PickObjects(ObjectType.Element, GridSelectionFilter(), "Select grid lines")
            grids = [doc.GetElement(r.ElementId) for r in picked_refs]
        except:
            TaskDialog.Show("Grid Extents", "Selection cancelled.")
            sys.exit()
    if not grids:
        TaskDialog.Show("Grid Extents", "No Grid elements selected.")
        sys.exit()

# -----------------------------
# Button click handlers
# -----------------------------
def on_2D(sender, args):
    global result
    result = "2D"
    window.Close()   # <-- close immediately

def on_3D(sender, args):
    global result
    result = "3D"
    window.Close()   # <-- close immediately
    
def on_coordinate(sender, args):
    """Advanced coordinate selector logic"""
    global result
    # Show coordinate system selector window
    selection_result = show_coordinate_system_selector(None, None, None, None)
    if selection_result is None:
        result = None
        window.Close()
        return

    # Collect all grids in view for advanced workflow
    grid_collector = GridsCollector(doc, view)
    if not grid_collector.check_validity():
        result = None
        window.Close()
        return

    # Show the toggle grid bubbles window
    toggle_window = ToggleGridWindow.create(
        script.get_bundle_file("toggle_grid_bubbles.xaml"),
        view,
        selection_result["coordinate_system"],
        selection_result["angle_tolerance"],
        grid_collector
    )
    if toggle_window is None:
        result = None
    else:
        toggle_window.ShowDialog()
        if toggle_window.result in [None, "cancel"]:
            result = None
        else:
            result = selection_result  # keep coordinate system info
    window.Close()

def on_cancel(sender, args):
    global result
    result = None
    window.Close()

# -----------------------------
# Wire up buttons
# -----------------------------
btn2D.Click += on_2D
btn3D.Click += on_3D
if btnCoordinate:
    btnCoordinate.Click += on_coordinate
cancelBtn.Click += on_cancel

# -----------------------------
# Show main dialog
# -----------------------------
window.ShowDialog()
if result is None:
    TaskDialog.Show("Grid Extents", "Operation cancelled.")
    sys.exit()

# -----------------------------
# Determine operation type
# -----------------------------
force_to_2d = (result == "2D")
force_to_3d = (result == "3D")
advanced_coord = isinstance(result, dict)  # Advanced button returns dict

# -----------------------------
# Apply changes
# -----------------------------
changed = 0
t = Transaction(doc, "Set Grid Extents/Bubbles")
t.Start()

if force_to_2d or force_to_3d:
    select_grids()  # Make sure grids are selected

for g in grids:
    try:
        if force_to_2d:
            g.SetDatumExtentType(DatumEnds.End0, view, DatumExtentType.ViewSpecific)
            g.SetDatumExtentType(DatumEnds.End1, view, DatumExtentType.ViewSpecific)
        elif force_to_3d:
            g.SetDatumExtentType(DatumEnds.End0, view, DatumExtentType.Model)
            g.SetDatumExtentType(DatumEnds.End1, view, DatumExtentType.Model)
        elif advanced_coord:
            # Advanced logic
            cg = CustomGrids(doc, view, result["coordinate_system"], result["angle_tolerance"])
            active_grids = cg.get_active_grids()
            for ag in active_grids:
                ag.ShowBubbleInView(DatumEnds.End0, view)
                ag.ShowBubbleInView(DatumEnds.End1, view)
        changed += 1
    except Exception as ex:
        print("Failed for grid {0} : {1}".format(g.Id, ex))

t.Commit()

# -----------------------------
# Report
# -----------------------------
if force_to_2d:
    msg = "Processed {0} grids.\nAll set to 2D (ViewSpecific).".format(changed)
elif force_to_3d:
    msg = "Processed {0} grids.\nAll set to 3D (Model).".format(changed)
elif advanced_coord:
    msg = "Processed grids.\nBubbles updated according to coordinate system and tolerance.".format(changed)
else:
    # fallback message if somehow none of the above applies
    msg = "No changes applied."

TaskDialog.Show("Grid Extents", msg)
