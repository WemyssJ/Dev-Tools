__title__ = "Split Framing\nat Ref Planes or Grids"
__author__ = "Craddys Tools"

from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Structure import StructuralType
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
from pyrevit import forms, script
import sys, time, traceback, os
from System.Windows import Visibility
from System import Uri
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption

uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document
output = script.get_output()

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

class PlaneOrGridFilter(ISelectionFilter):
    def AllowElement(self, elem):
        return isinstance(elem, ReferencePlane) or isinstance(elem, Grid)
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
        for i in range(len(all_pts) - 1):
            start, end = all_pts[i], all_pts[i + 1]
            if start.DistanceTo(end) < 0.01:
                continue
            new_curve = Line.CreateBound(start, end)
            new_beam = doc.Create.NewFamilyInstance(new_curve, beam_type, level, StructuralType.Beam)
            if preserve_params:
                copy_instance_parameters(beam, new_beam)
            new_beams.append(new_beam)
        doc.Delete(beam.Id)
        return new_beams
    except Exception as e:
        print("Error splitting beam {}: {}".format(beam.Id, e))
        traceback.print_exc()
        return []

# ----------------------------------------------------------------------
# SELECTION
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
        refs = uidoc.Selection.PickObjects(ObjectType.Element, PlaneOrGridFilter(), "Select reference planes or grids")
        stored_planes = [doc.GetElement(r.ElementId) for r in refs]
        return True
    except:
        return False

# ----------------------------------------------------------------------
# RUN SPLIT
# ----------------------------------------------------------------------
def run_split(show_logs=True, preserve_params=True):
    if not stored_beams or not stored_planes:
        forms.alert("You must select beams and reference planes or grids first.")
        return

    plane_data = []
    for el in stored_planes:
        if isinstance(el, ReferencePlane):
            plane = el.GetPlane()
            plane_data.append({'normal': plane.Normal, 'origin': plane.Origin})
        elif isinstance(el, Grid):
            curve = el.Curve
            if isinstance(curve, Line):
                direction = curve.Direction
                normal = XYZ(-direction.Y, direction.X, 0).Normalize()
                origin = curve.Origin
                plane_data.append({'normal': normal, 'origin': origin})

    total_splits = 0
    start = time.time()

    t = Transaction(doc, "Split Structural Framing at Ref Planes or Grids")
    t.Start()
    try:
        with forms.ProgressBar(title='Splitting Beams ({value} of {max_value})', cancellable=True, step=1) as pb:
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
                beam_id = beam.Id
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
# WPF Launcher (unchanged)
# ----------------------------------------------------------------------
class SplitLauncher(forms.WPFWindow):
    def __init__(self):
        xaml_path = os.path.join(os.path.dirname(__file__), "SplitFraming.xaml")
        forms.WPFWindow.__init__(self, xaml_path)
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        if os.path.exists(icon_path):
            bmp = BitmapImage()
            bmp.BeginInit()
            bmp.UriSource = Uri(icon_path)
            bmp.CacheOption = BitmapCacheOption.OnLoad
            bmp.EndInit()
            self.FindName("headerIcon").Source = bmp
        self.selectBeamsBtn.IsEnabled = True
        self.selectSplittersBtn.IsEnabled = False
        self.optionsBtn.IsEnabled = False
        self.showConsoleBox.IsChecked = True
        self.preserveParamsBox.IsChecked = True
        self.beamCountText = self.FindName("beamCountText")
        self.planeCountText = self.FindName("planeCountText")
        self.optionsPanel.Visibility = Visibility.Collapsed
        self.selectBeamsBtn.Click += self.on_select_beams
        self.selectSplittersBtn.Click += self.on_select_planes
        self.optionsBtn.Click += self.on_show_options
        self.runSplitBtn.Click += self.on_run_split
        self.closeBtn.Click += lambda s, e: self.Close()
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
            window.selectSplittersBtn.IsEnabled = True
            window.ShowDialog()

    def on_select_planes(self, sender, e):
        self.Close()
        if select_planes():
            window = SplitLauncher()
            window.selectBeamsBtn.IsEnabled = False
            window.selectSplittersBtn.IsEnabled = False
            window.optionsBtn.IsEnabled = True
            window.ShowDialog()

    def on_show_options(self, sender, e):
        self.optionsPanel.Visibility = Visibility.Visible

    def on_run_split(self, sender=None, e=None):
        self.Close()
        run_split(show_logs=self.showConsoleBox.IsChecked, preserve_params=self.preserveParamsBox.IsChecked)

SplitLauncher().ShowDialog()
