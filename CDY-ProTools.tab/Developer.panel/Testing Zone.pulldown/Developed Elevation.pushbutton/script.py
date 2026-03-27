# -*- coding: utf-8 -*-
import clr
clr.AddReference('PresentationFramework')
clr.AddReference('PresentationCore')
clr.AddReference('WindowsBase')

from Autodesk.Revit.DB import (
    BoundingBoxXYZ, Category, ElementId, FilteredElementCollector,
    Transform, ViewFamilyType, ViewSection, Viewport, ViewFamily,
    BuiltInCategory, BuiltInParameter, XYZ, ViewSheet, Wall, View
)
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
from pyrevit import forms, script, revit
from rpw.ui.forms import (FlexForm, Label, ComboBox, TextBox,
                           Separator, Button)

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
logger = script.get_logger()

# -------------------- HELPERS --------------------
def to_int(v, k, d):
    try:
        return max(1, int(v.get(k, d)))
    except:
        return int(d)

def mm_to_ft(v, k, d):
    try:
        return float(v.get(k, d)) / 304.8
    except:
        return float(d) / 304.8

# -------------------- SELECTION FILTER --------------------
class WallCurveFilter(ISelectionFilter):
    def AllowElement(self, elem):
        return elem.Category and elem.Category.Id.IntegerValue == int(BuiltInCategory.OST_Walls) and hasattr(elem.Location, "Curve")
    def AllowReference(self, ref, pt):
        return False

# -------------------- UI --------------------
def get_sheet_list():
    return sorted(
        FilteredElementCollector(doc).OfClass(ViewSheet).ToElements(),
        key=lambda s: s.SheetNumber
    )

def sheet_caption(s):
    return "{} - {}".format(s.SheetNumber, s.Name)

def pick_walls():
    forms.alert(
        "Select walls in the exact order you want them placed on sheet (first wall = first section group).",
        title="Dev Elevation: pick walls", warn_icon=False
    )
    try:
        refs = uidoc.Selection.PickObjects(ObjectType.Element,
                                           WallCurveFilter(),
                                           "Pick walls in order, then Finish")
    except:
        return []
    return [doc.GetElement(r.ElementId) for r in refs or []]

def prompt_options(sheets):
    if not sheets:
        forms.alert("Create at least one sheet first.", exitscript=True)
    labels = [sheet_caption(s) for s in sheets]
    components = [
        Label('View style'),
        ComboBox('view_type', ['Section', 'Elevation'], default='Section'),
        Label('Segments per wall'),
        TextBox('segments', default='1'),
        Label('Crop height mm'),
        TextBox('height_mm', default='5000'),
        Label('Cut depth mm'),
        TextBox('depth_mm', default='500'),
        Label('Viewport overlap mm'),
        TextBox('overlap_mm', default='6.1'),
        Separator(),
        Label('Target sheet'),
        ComboBox('target_sheet', labels),
        Label('View name prefix'),
        TextBox('prefix', default='DevElev'),
        Separator(),
        Button('Create Developed Elevation')
    ]
    form = FlexForm('Developed Elevation', components)
    form.show()
    if not form.values:
        return None
    v = form.values

    return {
        'use_sections': v['view_type'] == 'Section',
        'segments': to_int(v, 'segments', 24),
        'height_ft': mm_to_ft(v, 'height_mm', 3000),
        'depth_ft': mm_to_ft(v, 'depth_mm', 400),
        'overlap_mm': float(v.get('overlap_mm', 6.1)),
        'sheet_label': v['target_sheet'],
        'prefix': str(v['prefix']).strip() or 'DevElev',
    }

# -------------------- VIEWBOX --------------------
def make_section_box(origin, tangent, half_width, height, depth, outer_dir=None):
    tangent = tangent.Normalize()
    if tangent.GetLength() < 1e-6:
        tangent = XYZ.BasisX
    right = tangent.Normalize()

    if outer_dir is None:
        outer_dir = right.CrossProduct(XYZ.BasisZ)
        if outer_dir.GetLength() < 1e-6:
            outer_dir = right.CrossProduct(XYZ.BasisY)
        outer_dir = outer_dir.Normalize()
    else:
        try:
            outer_dir = outer_dir.Normalize()
        except:
            outer_dir = right.CrossProduct(XYZ.BasisZ).Normalize()

    view_dir = outer_dir.Negate()
    offset = outer_dir * depth * 0.75
    origin = origin + offset

    up = view_dir.CrossProduct(right)
    if up.GetLength() < 1e-6:
        up = XYZ.BasisZ
    up = up.Normalize()

    right = up.CrossProduct(view_dir).Normalize()

    t = Transform.Identity
    t.Origin = origin
    t.BasisX = right
    t.BasisY = up
    t.BasisZ = view_dir
    bb = BoundingBoxXYZ()
    bb.Transform = t

    half_height = height * 0.5
    bb.Min = XYZ(-half_width, -half_height, 0)
    bb.Max = XYZ(half_width, half_height, depth)
    return bb

def sample_curve(curve, n):
    t0 = curve.GetEndParameter(0)
    t1 = curve.GetEndParameter(1)
    samples = []
    for i in range(n):
        t = t0 + (t1 - t0) * (i + 0.5) / max(1, n)
        pt = curve.Evaluate(t, False)
        tangent = curve.ComputeDerivatives(t, False).BasisX
        samples.append((pt, tangent))
    return samples

def get_view_family_type(family):
    for vft in FilteredElementCollector(doc).OfClass(ViewFamilyType):
        if vft.ViewFamily == family:
            return vft.Id
    return None

def is_point_on_right_side(curve, point):
    try:
        sample = XYZ(point.X, point.Y, 0)
        proj = curve.Project(sample)
        if proj is None or proj.XYZPoint is None:
            return False
        curve_pt = proj.XYZPoint
        tangent = curve.ComputeDerivatives(proj.Parameter, False).BasisX
        if tangent.GetLength() < 1e-6:
            return False
        right_dir = tangent.Normalize().CrossProduct(XYZ.BasisZ).Normalize()
        delta = XYZ(point.X - curve_pt.X, point.Y - curve_pt.Y, 0)
        return delta.Dot(right_dir) > 0
    except:
        return False

def make_unique_view_name(base_name):
    existing = set(v.Name for v in FilteredElementCollector(doc).OfClass(View).ToElements())
    if base_name not in existing:
        return base_name
    if '-' in base_name:
        prefix, num_str = base_name.rsplit('-', 1)
        try:
            num = int(num_str)
            idx = num + 1
            while True:
                candidate = "{}-{:03d}".format(prefix, idx)
                if candidate not in existing:
                    return candidate
                idx += 1
        except:
            pass
    idx = 1
    while True:
        candidate = "{}_{}".format(base_name, idx)
        if candidate not in existing:
            return candidate
        idx += 1

def safe_set_parameter(element, param_id, value):
    try:
        p = element.get_Parameter(param_id)
        if p is not None and not p.IsReadOnly:
            p.Set(str(value))
            return True
    except:
        pass
    return False

def set_section_mark_number(view, number):
    num_text = "{:03d}".format(number) if isinstance(number, int) else str(number)
    safe_set_parameter(view, BuiltInParameter.VIEW_NUMBER, num_text)
    safe_set_parameter(view, BuiltInParameter.VIEWER_NUMBER, num_text)
    safe_set_parameter(view, BuiltInParameter.SECTION_NUMBER, num_text)
    safe_set_parameter(view, BuiltInParameter.SECTION_MARK, num_text)

def hide_annotation_in_view(view):
    for cat in doc.Settings.Categories:
        try:
            if cat.CategoryType.ToString() == 'Annotation' and cat.get_AllowsVisibilityControl(view):
                view.SetCategoryHidden(cat.Id, True)
            if cat.CategoryType.ToString() == 'Model' and cat.Id.IntegerValue in (
                    int(BuiltInCategory.OST_Levels),
                    int(BuiltInCategory.OST_Grids),
                    int(BuiltInCategory.OST_Sections)):
                if cat.get_AllowsVisibilityControl(view):
                    view.SetCategoryHidden(cat.Id, True)
        except:
            pass
    try:
        view.CropBoxVisible = False
        view.CropBoxActive = True
    except:
        pass

def sort_walls_from_start(walls, start_wall):
    walls_remaining = set(walls)
    sequence = [start_wall]
    walls_remaining.remove(start_wall)
    current = start_wall
    while walls_remaining:
        found = False
        c0 = current.Location.Curve
        end_pts = [c0.GetEndPoint(0), c0.GetEndPoint(1)]
        for w in list(walls_remaining):
            c1 = w.Location.Curve
            c1_end_pts = [c1.GetEndPoint(0), c1.GetEndPoint(1)]
            if any(ep0.IsAlmostEqualTo(ep1) for ep0 in end_pts for ep1 in c1_end_pts):
                sequence.append(w)
                walls_remaining.remove(w)
                current = w
                found = True
                break
        if not found:
            next_wall = walls_remaining.pop()
            sequence.append(next_wall)
            current = next_wall
    return sequence

def create_segment_views(walls, vft_id, segments, height, depth, prefix,
                         section_side_point=None):
    views = []
    if not walls:
        return views
    walls = sort_walls_from_start(walls, walls[0])
    for w_idx, wall in enumerate(walls):
        curve = wall.Location.Curve
        mid_t = (curve.GetEndParameter(0) + curve.GetEndParameter(1)) * 0.5
        pt = curve.Evaluate(mid_t, False)
        tan = curve.ComputeDerivatives(mid_t, False).BasisX
        half_width = curve.Length * 0.5
        outer_dir = None
        if section_side_point is not None:
            is_right = is_point_on_right_side(curve, section_side_point)
            try:
                right_dir = tan.Normalize().CrossProduct(XYZ.BasisZ).Normalize()
                outer_dir = right_dir if is_right else right_dir.Negate()
            except:
                outer_dir = None
        bb = make_section_box(pt, tan, half_width, height, depth, outer_dir)
        try:
            v = ViewSection.CreateSection(doc, vft_id, bb)
            temp_name = "TempSection_{}".format(w_idx)
            v.Name = make_unique_view_name(temp_name)
            hide_annotation_in_view(v)
            views.append(v)
        except Exception as ex:
            logger.warning("skip {} : {}".format(w_idx, ex))
    for i, v in enumerate(views, 1):
        desired_name = "{}-{:03d}".format(prefix, i)
        v.Name = make_unique_view_name(desired_name)
    return views

def find_sheet(label, sheets):
    for s in sheets:
        if sheet_caption(s) == label:
            return s
    return None

def find_no_title_viewport_type():
    for vt in FilteredElementCollector(doc).OfClass(Viewport).WhereElementIsElementType().ToElements():
        p = vt.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME)
        if p and 'no' in (p.AsString() or '').lower() and 'title' in (p.AsString() or '').lower():
            return vt.Id
    return ElementId.InvalidElementId

# -------------------- PLACEMENT --------------------
def place_continuous(sheet, views, vp_type, overlap_mm=6.1, start_x_mm=100, start_y_mm=250):
    """
    Place views continuously on a sheet.
    Correct first viewport horizontal offset by small Revit margin (~25.6mm).
    """
    overlap_ft = overlap_mm / 304.8
    y_level = start_y_mm / 304.8
    placed = []

    cursor_x = start_x_mm / 304.8  # initial left margin

    for i, v in enumerate(views):
        # Create temporary viewport at origin
        try:
            vp = Viewport.Create(doc, sheet.Id, v.Id, XYZ(0, 0, 0))
        except Exception as ex:
            logger.warning("Failed to place viewport {}: {}".format(v.Name, ex))
            continue

        if vp_type != ElementId.InvalidElementId:
            try:
                vp.ChangeTypeId(vp_type)
                doc.Regenerate()
            except:
                pass

        # Get viewport box outline width
        try:
            bb = vp.GetBoxOutline()
            vp_width = bb.MaximumPoint.X - bb.MinimumPoint.X
            vp_height = bb.MaximumPoint.Y - bb.MinimumPoint.Y
        except:
            bb = v.CropBox
            vp_width = bb.Max.X - bb.Min.X
            vp_height = bb.Max.Y - bb.Min.Y

        # Compute small left margin adjustment for the first viewport
        if i == 0:
            # Desired top-left = start_x_mm, actual top-left = cursor_x
            # offset = half of box outline internal margin (approx 25.6 mm)
            adjust_ft = 25.6 / 304.8  # convert mm to ft
        else:
            adjust_ft = 0.0

        vp_center = XYZ(cursor_x + vp_width / 2 + adjust_ft, y_level + vp_height / 2, 0)
        vp.SetBoxCenter(vp_center)

        placed.append(vp)

        # Move cursor for next viewport
        cursor_x += vp_width - overlap_ft
        doc.Regenerate()

    return placed

# -------------------- RUN --------------------
def run():
    walls = pick_walls()
    if not walls:
        forms.alert("No walls selected.", exitscript=True)
        return
    sheets = get_sheet_list()
    opts = prompt_options(sheets)
    if not opts:
        return
    try:
        side_point = uidoc.Selection.PickPoint("Pick a point to choose section side")
    except:
        side_point = None
    target = find_sheet(opts['sheet_label'], sheets)
    if not target:
        forms.alert("Target sheet not found.", exitscript=True)
        return
    vft = get_view_family_type(ViewFamily.Section if opts['use_sections'] else ViewFamily.Elevation)
    if not vft:
        forms.alert("No suitable view family type in project.", exitscript=True)
        return
    no_title = find_no_title_viewport_type()
    with revit.Transaction("Developed Elevation"):
        views = create_segment_views(
            walls, vft, opts['segments'],
            opts['height_ft'], opts['depth_ft'], opts['prefix'],
            section_side_point=side_point
        )
        if not views:
            forms.alert("No segment views created (maybe a geometry issue).")
            return
        place_continuous(target, views, no_title, overlap_mm=opts['overlap_mm'])
    uidoc.ActiveView = target
    forms.alert("Done: {} segment views on sheet.".format(len(views)), warn_icon=False)

run()
