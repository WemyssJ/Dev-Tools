# -*- coding: utf-8 -*-
__title__ = 'Trim/Extend Beams to Line/Grid (Safe)'
__doc__ = 'Trim or extend multiple beams so their ends align with a selected line or grid, preserving slope or Z as specified, with optional disallow join.'

from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Structure import StructuralFramingUtils
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
from Autodesk.Revit.Exceptions import InvalidOperationException
from pyrevit import forms, script
from System.Windows import Visibility
from System import Uri
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption
import os, traceback, math

uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document
output = script.get_output()

# ----------------------------------------------------------------------
# GLOBALS
# ----------------------------------------------------------------------
stored_beams = []
stored_ref_elem = None

# ----------------------------------------------------------------------
# FILTERS
# ----------------------------------------------------------------------
class StructuralFramingFilter(ISelectionFilter):
    def AllowElement(self, elem):
        return elem.Category and elem.Category.Id.IntegerValue == int(BuiltInCategory.OST_StructuralFraming)
    def AllowReference(self, ref, point):
        return False

class ReferenceElementFilter(ISelectionFilter):
    def AllowElement(self, elem):
        return (hasattr(elem, 'Location') and isinstance(elem.Location, LocationCurve)) or isinstance(elem, Grid)
    def AllowReference(self, ref, point):
        return False

# ----------------------------------------------------------------------
# UTILITY FUNCTIONS
# ----------------------------------------------------------------------
def get_line_from_element(elem):
    if hasattr(elem, 'Location') and isinstance(elem.Location, LocationCurve):
        return elem.Location.Curve
    if isinstance(elem, (ModelCurve, DetailCurve)):
        return elem.GeometryCurve
    if isinstance(elem, Grid):
        return elem.Curve
    return None

def move_point_to_ref_along_beam(orig_pt, beam_vec, ref_line, preserve_z):
    """
    Calculate new endpoint for a beam along its original vector so that XY aligns with reference line.
    If preserve_z is False, Z is adjusted to maintain slope.
    """
    # Project original point to reference line in XY only
    p0 = ref_line.GetEndPoint(0)
    p1 = ref_line.GetEndPoint(1)
    # Flatten Z for projection
    p0f = XYZ(p0.X, p0.Y, 0)
    p1f = XYZ(p1.X, p1.Y, 0)
    pf = XYZ(orig_pt.X, orig_pt.Y, 0)
    line_vec = (p1f - p0f).Normalize()
    t = line_vec.DotProduct(pf - p0f)
    proj_xy = p0f + t * line_vec

    # Compute delta in XY
    delta_xy = XYZ(proj_xy.X - orig_pt.X, proj_xy.Y - orig_pt.Y, 0)

    # Project delta along beam vector
    beam_xy_len = math.hypot(beam_vec.X, beam_vec.Y)
    if beam_xy_len < 1e-9:
        scale = 0
    else:
        scale = math.hypot(delta_xy.X, delta_xy.Y) / beam_xy_len

    if preserve_z:
        new_pt = XYZ(orig_pt.X + delta_xy.X, orig_pt.Y + delta_xy.Y, orig_pt.Z)
    else:
        new_pt = XYZ(orig_pt.X + delta_xy.X,
                     orig_pt.Y + delta_xy.Y,
                     orig_pt.Z + beam_vec.Z * scale)

    return new_pt

# ----------------------------------------------------------------------
# SELECTION FUNCTIONS
# ----------------------------------------------------------------------
def select_beams():
    global stored_beams
    try:
        refs = uidoc.Selection.PickObjects(ObjectType.Element, StructuralFramingFilter(), "Select structural framing elements")
        stored_beams = [doc.GetElement(r.ElementId) for r in refs]
        return True
    except:
        return False

def select_reference():
    global stored_ref_elem
    try:
        ref = uidoc.Selection.PickObject(ObjectType.Element, ReferenceElementFilter(), "Select reference line/grid/beam")
        stored_ref_elem = doc.GetElement(ref.ElementId)
        if not get_line_from_element(stored_ref_elem):
            forms.alert("Selected element has no valid line/curve.")
            stored_ref_elem = None
            return False
        return True
    except:
        return False

# ----------------------------------------------------------------------
# RUN TRIM/EXTEND
# ----------------------------------------------------------------------
def run_trim_extend(preserve_z=True, disallow_join=True):
    if not stored_beams or not stored_ref_elem:
        forms.alert("You must select beams and a reference element first.")
        return

    ref_line = get_line_from_element(stored_ref_elem)
    if not ref_line:
        forms.alert("Reference element is invalid.")
        return

    t = Transaction(doc, "Trim/Extend Beams to Reference (Safe)")
    t.Start()
    try:
        with forms.ProgressBar(title='Trimming/Extending Beams ({value} of {max_value})', cancellable=True, step=1) as pb:
            for idx, beam in enumerate(stored_beams):
                if pb.cancelled:
                    t.RollBack()
                    forms.alert("Operation cancelled by user.")
                    return
                pb.update_progress(idx + 1, len(stored_beams))

                loc = beam.Location
                if not isinstance(loc, LocationCurve):
                    continue

                start = loc.Curve.GetEndPoint(0)
                end = loc.Curve.GetEndPoint(1)
                beam_vec = end - start

                # Decide which end is closer in XY to reference
                proj_start = move_point_to_ref_along_beam(start, beam_vec, ref_line, preserve_z=True)
                proj_end = move_point_to_ref_along_beam(end, beam_vec, ref_line, preserve_z=True)
                dist_start = math.hypot(start.X - proj_start.X, start.Y - proj_start.Y)
                dist_end = math.hypot(end.X - proj_end.X, end.Y - proj_end.Y)

                if dist_start < dist_end:
                    new_start = move_point_to_ref_along_beam(start, beam_vec, ref_line, preserve_z)
                    new_line = Line.CreateBound(new_start, end)
                else:
                    new_end = move_point_to_ref_along_beam(end, beam_vec, ref_line, preserve_z)
                    new_line = Line.CreateBound(start, new_end)

                # Disallow joins if requested
                if disallow_join:
                    try:
                        StructuralFramingUtils.DisallowJoinAtEnd(beam, 0)
                        StructuralFramingUtils.DisallowJoinAtEnd(beam, 1)
                    except:
                        pass

                loc.Curve = new_line

        t.Commit()
        forms.alert("Trim/Extend complete. {} beams processed.".format(len(stored_beams)))

    except Exception as e:
        t.RollBack()
        forms.alert("Error during Trim/Extend: " + str(e))
        print(traceback.format_exc())

# ----------------------------------------------------------------------
# WPF LAUNCHER
# ----------------------------------------------------------------------
class TrimExtendLauncher(forms.WPFWindow):
    def __init__(self):
        xaml_path = os.path.join(os.path.dirname(__file__), "TrimExtendBeams.xaml")
        forms.WPFWindow.__init__(self, xaml_path)

        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        if os.path.exists(icon_path):
            bmp = BitmapImage()
            bmp.BeginInit()
            bmp.UriSource = Uri(icon_path)
            bmp.CacheOption = BitmapCacheOption.OnLoad
            bmp.EndInit()
            self.FindName("headerIcon").Source = bmp   # <-- use self, not window

        # Initial state
        self.selectBeamsBtn.IsEnabled = True
        self.selectRefBtn.IsEnabled = False
        self.optionsBtn.IsEnabled = False

        # Default options
        self.preserveZBox.IsChecked = True
        self.disallowJoinBox.IsChecked = True

        # Count TextBlocks
        self.beamCountText = self.FindName("beamCountText")
        self.refCountText = self.FindName("refCountText")

        # Hide options panel initially
        self.optionsPanel.Visibility = Visibility.Collapsed

        # Bind buttons
        self.selectBeamsBtn.Click += self.on_select_beams
        self.selectRefBtn.Click += self.on_select_ref
        self.optionsBtn.Click += self.on_show_options
        self.runBtn.Click += self.on_run_trim
        self.closeBtn.Click += lambda s,e: self.Close()

        # Update counts
        self.update_counts()

    def update_counts(self):
        if self.beamCountText is not None:
            self.beamCountText.Text = "Selected: {}".format(len(stored_beams))
        if self.refCountText is not None:
            self.refCountText.Text = "Selected: {}".format(1 if stored_ref_elem else 0)

    def on_select_beams(self, sender, e):
        self.Close()
        if select_beams():
            window = TrimExtendLauncher()
            window.selectBeamsBtn.IsEnabled = False
            window.selectRefBtn.IsEnabled = True
            window.optionsBtn.IsEnabled = False
            window.ShowDialog()

    def on_select_ref(self, sender, e):
        self.Close()
        if select_reference():
            window = TrimExtendLauncher()
            window.selectBeamsBtn.IsEnabled = False
            window.selectRefBtn.IsEnabled = False
            window.optionsBtn.IsEnabled = True
            window.ShowDialog()

    def on_show_options(self, sender, e):
        self.optionsPanel.Visibility = Visibility.Visible

    def on_run_trim(self, sender=None, e=None):
        self.Close()
        preserve_z = self.preserveZBox.IsChecked
        disallow_join = self.disallowJoinBox.IsChecked
        run_trim_extend(preserve_z=preserve_z, disallow_join=disallow_join)

# Launch
TrimExtendLauncher().ShowDialog()