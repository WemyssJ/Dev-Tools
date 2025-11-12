# -*- coding: utf-8 -*-
import clr
import sys
import os

clr.AddReference("PresentationFramework")
clr.AddReference("PresentationCore")
clr.AddReference("WindowsBase")
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')

from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType
from System.Windows.Markup import XamlReader
from System.IO import StringReader
from pyrevit import script
from System import Uri
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption

# -----------------------------
# Selection filter
# -----------------------------
class GridSelectionFilter(ISelectionFilter):
    def AllowElement(self, element):
        return isinstance(element, Grid)
    def AllowReference(self, reference, position):
        return False

# ---------------------------------------------------------------------
# Load XAML UI
# ---------------------------------------------------------------------
xaml_path = script.get_bundle_file('GridManip.xaml')
with open(xaml_path, 'r') as f:
    xaml_str = f.read()
window = XamlReader.Parse(xaml_str)

btn2D = window.FindName("btn2D")
btn3D = window.FindName("btn3D")
btnBubbles = window.FindName("btnBubbles")
cancelBtn = window.FindName("cancelBtn")
headerIcon = window.FindName("headerIcon")

# -----------------------------
# Load icon.png automatically
# -----------------------------
icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
if os.path.exists(icon_path):
    bmp = BitmapImage()
    bmp.BeginInit()
    bmp.UriSource = Uri(icon_path)
    bmp.CacheOption = BitmapCacheOption.OnLoad
    bmp.EndInit()
    headerIcon.Source = bmp
else:
    print("⚠️ icon.png not found in script folder.")

# -----------------------------
# Result storage variable
# -----------------------------
result = None

def on_2D(sender, args):
    global result
    result = "2D"
    window.Close()

def on_3D(sender, args):
    global result
    result = "3D"
    window.Close()

def on_Bubbles(sender, args):
    global result
    result = "Bubbles"
    window.Close()

def on_cancel(sender, args):
    global result
    result = None
    window.Close()

btn2D.Click += on_2D
btn3D.Click += on_3D
btnBubbles.Click += on_Bubbles
cancelBtn.Click += on_cancel

# -----------------------------
# Grid selection
# -----------------------------
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document
view = doc.ActiveView

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
# Show dialog
# -----------------------------
window.ShowDialog()

if result is None:
    TaskDialog.Show("Grid Extents", "Operation cancelled.")
    sys.exit()

force_to_2d = (result == "2D")
force_to_3d = (result == "3D")
force_bubbles = (result == "Bubbles")

# -----------------------------
# Apply changes
# -----------------------------
changed = 0
t = Transaction(doc, "Set Grid Extents/Bubbles")
t.Start()

for g in grids:
    try:
        if force_to_2d:
            g.SetDatumExtentType(DatumEnds.End0, view, DatumExtentType.ViewSpecific)
            g.SetDatumExtentType(DatumEnds.End1, view, DatumExtentType.ViewSpecific)
        elif force_to_3d:
            g.SetDatumExtentType(DatumEnds.End0, view, DatumExtentType.Model)
            g.SetDatumExtentType(DatumEnds.End1, view, DatumExtentType.Model)
        elif force_bubbles:
            g.SetDatumExtentType(DatumEnds.End0, view, DatumExtentType.ViewSpecific)
            g.SetDatumExtentType(DatumEnds.End1, view, DatumExtentType.ViewSpecific)
            g.ShowBubbleInView(DatumEnds.End0, view)
            g.ShowBubbleInView(DatumEnds.End1, view)
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
elif force_bubbles:
    msg = "Processed {0} grids.\nBubbles turned ON at both ends.".format(changed)
else:
    msg = "No changes applied."

TaskDialog.Show("Grid Extents", msg)
