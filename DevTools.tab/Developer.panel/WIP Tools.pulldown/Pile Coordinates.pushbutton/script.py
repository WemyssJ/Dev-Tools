from Autodesk.Revit.DB import *
from pyrevit import revit, script
import math

doc = revit.doc
output = script.get_output()

def feet_to_mm(feet):
    return round(feet * 304.8, 1)  # mm, 0.1 mm precision

def rotate(x, y, angle_rad):
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    x_rot = x * cos_theta - y * sin_theta
    y_rot = x * sin_theta + y * cos_theta
    return x_rot, y_rot

def get_param_val(elem, name):
    p = elem.LookupParameter(name)
    return p.AsDouble() if p and p.StorageType == StorageType.Double else 0

bps = list(FilteredElementCollector(doc).OfClass(BasePoint))
pbp = next(bp for bp in bps if not bp.IsShared)
svp = next(bp for bp in bps if bp.IsShared)

bp_ew = get_param_val(pbp, "E/W")  # feet
bp_ns = get_param_val(pbp, "N/S")  # feet
angle_rad = get_param_val(pbp, "Angle to True North")  # radians

svp_elev = svp.get_Parameter(BuiltInParameter.BASEPOINT_ELEVATION_PARAM).AsDouble()  # feet

pbp_internal = pbp.Position
svp_internal = svp.Position

t = Transaction(doc, "Set Pile Coordinates")
t.Start()

pile_count = 0

foundations = FilteredElementCollector(doc) \
    .OfCategory(BuiltInCategory.OST_StructuralFoundation) \
    .WhereElementIsNotElementType() \
    .ToElements()

for pile in foundations:
    type_elem = doc.GetElement(pile.GetTypeId())
    name = type_elem.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString()

    if "Pile" not in name:
        continue

    loc = pile.Location
    if not isinstance(loc, LocationPoint):
        continue

    pt = loc.Point

    dx = pt.X - pbp_internal.X
    dy = pt.Y - pbp_internal.Y

    dx_rot, dy_rot = rotate(dx, dy, -angle_rad)

    # Easting and Northing in mm
    easting_mm = feet_to_mm(bp_ew + dx_rot)
    northing_mm = feet_to_mm(bp_ns + dy_rot)

    # Elevation relative to Survey Point elevation, in feet
    elevation_rel_ft = pt.Z - svp_internal.Z  # difference in feet

    # Add Survey Point's elevation (feet)
    elevation_ft = elevation_rel_ft + svp_elev

    param_x = pile.LookupParameter("Co-ord X (E/W)")
    param_y = pile.LookupParameter("Co-ord Y (N/S)")
    param_z = pile.LookupParameter("Co-ord Z (Elev)")

    if param_x and param_x.StorageType == StorageType.Double:
        param_x.Set(easting_mm)   # mm assumed
    if param_y and param_y.StorageType == StorageType.Double:
        param_y.Set(northing_mm)  # mm assumed
    if param_z and param_z.StorageType == StorageType.Double:
        param_z.Set(elevation_ft)  # feet (internal units)

    pile_count += 1

t.Commit()

output.print_md("### Set coordinates for {} pile foundations. Easting/Northing in mm, Elevation relative to Survey Point in feet.".format(pile_count))
