# grid_extents_wpf_enum_fixed.py (IronPython for pyRevit)
import clr
import sys

clr.AddReference("PresentationFramework")
clr.AddReference("PresentationCore")
clr.AddReference("WindowsBase")
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')

from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType
from System.Windows import Window, Thickness, WindowStartupLocation
from System.Windows.Controls import StackPanel, Button, CheckBox, Orientation

# Selection filter to allow only grids
class GridSelectionFilter(ISelectionFilter):
    def AllowElement(self, element):
        return isinstance(element, Grid)
    def AllowReference(self, reference, position):
        return False

# WPF window
class GridExtentsWindow(Window):
    def __init__(self):
        self.Title = "Grid Extents Options"
        self.Width = 250
        self.Height = 150
        self.ResizeMode = 0  # No resize
        self.WindowStartupLocation = WindowStartupLocation.CenterScreen

        panel = StackPanel()
        panel.Orientation = Orientation.Vertical
        panel.Margin = Thickness(10)

        # Checkboxes
        self.cb2d = CheckBox()
        self.cb2d.Content = "Set to 2D (ViewSpecific)"
        self.cb2d.Margin = Thickness(5)
        panel.Children.Add(self.cb2d)

        self.cb3d = CheckBox()
        self.cb3d.Content = "Set to 3D (Model)"
        self.cb3d.Margin = Thickness(5)
        panel.Children.Add(self.cb3d)

        # Mutually exclusive
        def on_cb2d(sender, args):
            if self.cb2d.IsChecked:
                self.cb3d.IsChecked = False
        def on_cb3d(sender, args):
            if self.cb3d.IsChecked:
                self.cb2d.IsChecked = False
        self.cb2d.Checked += on_cb2d
        self.cb3d.Checked += on_cb3d

        # Buttons
        btn_panel = StackPanel()
        btn_panel.Orientation = Orientation.Horizontal
        btn_panel.Margin = Thickness(5)

        confirm = Button()
        confirm.Content = "Confirm"
        confirm.Width = 80
        confirm.Margin = Thickness(5)
        confirm.Click += self.on_confirm
        btn_panel.Children.Add(confirm)

        cancel = Button()
        cancel.Content = "Cancel"
        cancel.Width = 80
        cancel.Margin = Thickness(5)
        cancel.Click += self.on_cancel
        btn_panel.Children.Add(cancel)

        panel.Children.Add(btn_panel)
        self.Content = panel
        self.result = None

    def on_confirm(self, sender, args):
        if self.cb2d.IsChecked:
            self.result = "2D"
        elif self.cb3d.IsChecked:
            self.result = "3D"
        else:
            self.result = None
        self.Close()

    def on_cancel(self, sender, args):
        self.result = None
        self.Close()


# Main script
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document
view = doc.ActiveView

# Preselected grids
sel_ids = uidoc.Selection.GetElementIds()
grids = [doc.GetElement(eid) for eid in sel_ids if isinstance(doc.GetElement(eid), Grid)]

# Post-selection if none
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

# Show WPF form
win = GridExtentsWindow()
win.ShowDialog()

if win.result is None:
    TaskDialog.Show("Grid Extents", "Operation cancelled.")
    sys.exit()

force_to_2d = (win.result == "2D")

# Process grids
changed = 0
t = Transaction(doc, "Set Grid Extents")
t.Start()

for g in grids:
    try:
        if not g.CanBeVisibleInView(view):
            continue

        if force_to_2d:
            # Force to 2D
            g.SetDatumExtentType(DatumEnds.End0, view, DatumExtentType.ViewSpecific)
            g.SetDatumExtentType(DatumEnds.End1, view, DatumExtentType.ViewSpecific)

            # Copy geometry from model curve
            try:
                model_curves = g.GetCurvesInView(DatumExtentType.Model, view)
                if model_curves:
                    for c in model_curves:
                        try:
                            if g.IsCurveValidInView(DatumExtentType.ViewSpecific, view, c):
                                g.SetCurveInView(DatumExtentType.ViewSpecific, view, c)
                                break
                        except:
                            pass
            except:
                pass
        else:
            # Force to 3D
            g.SetDatumExtentType(DatumEnds.End0, view, DatumExtentType.Model)
            g.SetDatumExtentType(DatumEnds.End1, view, DatumExtentType.Model)

        changed += 1

    except Exception as ex:
        print("Failed for grid {0} : {1}".format(g.Id, ex))

t.Commit()

# Report
if force_to_2d:
    msg = "Processed {0} grids.\nAll set to 2D (ViewSpecific).".format(changed)
else:
    msg = "Processed {0} grids.\nAll set to 3D (Model).".format(changed)

TaskDialog.Show("Grid Extents", msg)
