__title__ = "Split Framing\nat Ref Planes"
__author__ = "Craddys Tools"

from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Structure import StructuralType
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
from pyrevit import forms, script
import sys, time, traceback, os
from System.Windows import Visibility

uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document
output = script.get_output()

# ----------------------------------------------------------------------
# GLOBALS
# ----------------------------------------------------------------------
stored_beams = []
stored_planes = []

# ----------------------------------------------------------------------
# FILTERS
# ----------------------------------------------------------------------
class StructuralFramingFilter(ISelectionFilter):
    def AllowElement(self, elem):
        return elem.Category and elem.Category.Id.IntegerValue == int(BuiltInCategory.OST_StructuralFraming)
    def AllowReference(self, ref, point): 
        return False

class ReferencePlaneFilter(ISelectionFilter):
    def AllowElement(self, elem): 
        return isinstance(elem, ReferencePlane)
    def AllowReference(self, ref, point): 
        return False

# ----------------------------------------------------------------------
# UTILITY FUNCTIONS
# ----------------------------------------------------------------------
def get_intersection_points(beam_curve, plane_data_list):
    p0 = beam_curve.GetEndPoint(0)
    p1 = beam_curve.GetEndPoint(1)
    points = []
    for pdata in plane_data_list:
        d0 = pdata['normal'].DotProduct(p0 - pdata['origin'])
        d1 = pdata['normal'].DotProduct(p1 - pdata['origin'])
        if d0 * d1 <= 0.001 and abs(d1 - d0) >= 0.0001:
            t = -d0 / (d1 - d0)
            if 0.01 < t < 0.99:
                pt = beam_curve.Evaluate(t, True)
                if abs(pdata['normal'].DotProduct(pt - pdata['origin'])) < 0.01:
                    points.append(pt)
    return points

def copy_instance_parameters(source, target):
    for param in source.Parameters:
        if not param.IsReadOnly and param.HasValue:
            try:
                target_param = target.LookupParameter(param.Definition.Name)
                if target_param and not target_param.IsReadOnly:
                    if param.StorageType == StorageType.Double:
                        target_param.Set(param.AsDouble())
                    elif param.StorageType == StorageType.Integer:
                        target_param.Set(param.AsInteger())
                    elif param.StorageType == StorageType.String:
                        val = param.AsString()
                        if val: 
                            target_param.Set(val)
                    elif param.StorageType == StorageType.ElementId:
                        target_param.Set(param.AsElementId())
            except:
                pass

def split_beam_manual(beam, split_points, preserve_params=True):
    """
    Splits a beam into multiple new beams at the specified split_points.
    Preserves instance parameters if preserve_params is True.
    """
    if not split_points:
        return []

    new_beams = []

    try:
        loc = beam.Location
        if not isinstance(loc, LocationCurve):
            return []

        curve = loc.Curve
        p0 = curve.GetEndPoint(0)
        sorted_points = sorted(split_points, key=lambda pt: p0.DistanceTo(pt))
        all_pts = [p0] + sorted_points + [curve.GetEndPoint(1)]

        beam_type = doc.GetElement(beam.GetTypeId())
        level = doc.GetElement(beam.LevelId)

        # Create all new beams first
        for i in range(len(all_pts) - 1):
            start, end = all_pts[i], all_pts[i + 1]
            if start.DistanceTo(end) < 0.01:
                continue
            new_curve = Line.CreateBound(start, end)
            new_beam = doc.Create.NewFamilyInstance(new_curve, beam_type, level, StructuralType.Beam)
            if preserve_params:
                copy_instance_parameters(beam, new_beam)
            new_beams.append(new_beam)

        # Delete the original beam only after all new beams exist
        doc.Delete(beam.Id)

        return new_beams

    except Exception as e:
        print("Error splitting beam {}: {}".format(beam.Id, e))
        traceback.print_exc()
        return []

# ----------------------------------------------------------------------
# SELECTION STEPS
# ----------------------------------------------------------------------
def select_beams():
    global stored_beams
    try:
        refs = uidoc.Selection.PickObjects(ObjectType.Element, StructuralFramingFilter(), "Select structural framing elements")
        stored_beams = [doc.GetElement(r.ElementId) for r in refs]
        return True
    except:
        return False

def select_planes():
    global stored_planes
    try:
        refs = uidoc.Selection.PickObjects(ObjectType.Element, ReferencePlaneFilter(), "Select reference planes")
        stored_planes = [doc.GetElement(r.ElementId) for r in refs]
        return True
    except:
        return False

# ----------------------------------------------------------------------
# RUN SPLIT
# ----------------------------------------------------------------------
def run_split(show_logs=True, preserve_params=True):
    if not stored_beams or not stored_planes:
        forms.alert("You must select beams and reference planes first.")
        return

    plane_data = [{'normal': rp.GetPlane().Normal, 'origin': rp.GetPlane().Origin} for rp in stored_planes]
    total_splits = 0
    start = time.time()

    t = Transaction(doc, "Split Structural Framing at Reference Planes")
    t.Start()
    try:
        with forms.ProgressBar(title='Splitting Beams ({value} of {max_value})',
                               cancellable=True,
                               step=1) as pb:

            for idx, beam in enumerate(stored_beams):
                if pb.cancelled:
                    t.RollBack()
                    forms.alert("Operation cancelled by user.")
                    return

                pb.update_progress(idx + 1, len(stored_beams))

                loc = beam.Location
                if not isinstance(loc, LocationCurve):
                    continue

                pts = get_intersection_points(loc.Curve, plane_data)
                beam_id = beam.Id  # Store ID before deleting
                st = SubTransaction(doc)
                st.Start()
                try:
                    new_beams = split_beam_manual(beam, pts, preserve_params)
                    total_splits += len(new_beams)
                    st.Commit()
                except Exception as e:
                    st.RollBack()
                    print("Error splitting beam {}: {}".format(beam_id, e))
                    traceback.print_exc()

                if show_logs:
                    output.print_md("Beam **{}** split into **{}** segments.".format(beam_id, len(pts)))


        t.Commit()
        duration = time.time() - start
        forms.alert("Split complete.\nBeams processed: {}\nNew segments: {}\nTime: {:.1f}s".format(
            len(stored_beams), total_splits, duration))

    except Exception as e:
        t.RollBack()
        forms.alert("Error during split: " + str(e))
        print(traceback.format_exc())

# ----------------------------------------------------------------------
# WPF LAUNCHER
# ----------------------------------------------------------------------
class SplitLauncher(forms.WPFWindow):
    def __init__(self):
        xaml_path = os.path.join(os.path.dirname(__file__), "SplitFramingAtRefPlanes.xaml")
        forms.WPFWindow.__init__(self, xaml_path)

        # Initial state
        self.selectBeamsBtn.IsEnabled = True
        self.selectPlanesBtn.IsEnabled = False
        self.optionsBtn.IsEnabled = False

        # Default options
        self.showConsoleBox.IsChecked = True
        self.preserveParamsBox.IsChecked = True

        # Count TextBlocks (make sure these exist in XAML)
        self.beamCountText = self.FindName("beamCountText")
        self.planeCountText = self.FindName("planeCountText")

        # Hide options panel initially
        self.optionsPanel.Visibility = Visibility.Collapsed

        # Bind buttons
        self.selectBeamsBtn.Click += self.on_select_beams
        self.selectPlanesBtn.Click += self.on_select_planes
        self.optionsBtn.Click += self.on_show_options
        self.runSplitBtn.Click += self.on_run_split
        self.closeBtn.Click += lambda s,e: self.Close()

        # Update counts
        self.update_counts()

    def update_counts(self):
        if self.beamCountText is not None:
            self.beamCountText.Text = "Selected: {}".format(len(stored_beams))
        if self.planeCountText is not None:
            self.planeCountText.Text = "Selected: {}".format(len(stored_planes))

    def on_select_beams(self, sender, e):
        self.Close()
        if select_beams():
            window = SplitLauncher()
            window.selectBeamsBtn.IsEnabled = False
            window.selectPlanesBtn.IsEnabled = True
            window.optionsBtn.IsEnabled = False
            window.ShowDialog()

    def on_select_planes(self, sender, e):
        self.Close()
        if select_planes():
            window = SplitLauncher()
            window.selectBeamsBtn.IsEnabled = False
            window.selectPlanesBtn.IsEnabled = False
            window.optionsBtn.IsEnabled = True
            window.ShowDialog()

    def on_show_options(self, sender, e):
        # Reveal options panel and run button
        self.optionsPanel.Visibility = Visibility.Visible

    def on_run_split(self, sender=None, e=None):
        self.Close()
        show_logs = self.showConsoleBox.IsChecked
        preserve_params = self.preserveParamsBox.IsChecked
        run_split(show_logs=show_logs, preserve_params=preserve_params)

# Launch
SplitLauncher().ShowDialog()
