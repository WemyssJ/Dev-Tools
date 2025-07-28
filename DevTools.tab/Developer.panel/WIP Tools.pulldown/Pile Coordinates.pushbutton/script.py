from Autodesk.Revit.DB import *
from pyrevit import revit, script
import math

doc = revit.doc
output = script.get_output()

def rotate(x, y, angle_rad):
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    x_rot = x * cos_theta - y * sin_theta
    y_rot = x * sin_theta + y * cos_theta
    return x_rot, y_rot

def get_param_val(elem, param_name):
    param = elem.LookupParameter(param_name)
    if param and param.StorageType == StorageType.Double:
        return param.AsDouble()
    return 0.0

# --- Retrieve Base Points ---
bps = list(FilteredElementCollector(doc).OfClass(BasePoint))

# Find Project Base Point and Survey Point
pbp = None
svp = None

for bp in bps:
    if bp.IsShared:
        svp = bp
    else:
        pbp = bp

if not pbp or not svp:
    script.exit("Could not find both Project Base Point and Survey Point.")

# Get base point values (in feet and radians)
bp_ew = get_param_val(pbp, "E/W")  # Easting offset
bp_ns = get_param_val(pbp, "N/S")  # Northing offset
angle_rad = get_param_val(pbp, "Angle to True North")  # rotation angle in radians

# Get survey elevation and positions
svp_elev_ft = svp.get_Parameter(BuiltInParameter.BASEPOINT_ELEVATION_PARAM).AsDouble()
pbp_pos = pbp.Position
svp_pos = svp.Position

# --- Begin Transaction ---
t = Transaction(doc, "Set Pile Coordinates")
t.Start()

pile_count = 0

foundations = FilteredElementCollector(doc) \
    .OfCategory(BuiltInCategory.OST_StructuralFoundation) \
    .WhereElementIsNotElementType() \
    .ToElements()

for pile in foundations:
    type_elem = doc.GetElement(pile.GetTypeId())
    if not type_elem:
        continue

    family_name_param = type_elem.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)
    if not family_name_param:
        continue

    family_name = family_name_param.AsString()
    if "Pile" not in family_name:
        continue

    loc = pile.Location
    if not isinstance(loc, LocationPoint):
        continue

    pt = loc.Point

    # Translate to base point origin
    dx = pt.X - pbp_pos.X
    dy = pt.Y - pbp_pos.Y

    # Rotate into true north orientation
    dx_rot, dy_rot = rotate(dx, dy, -angle_rad)

    # Use raw feet values directly (no feet_to_mm conversion)
    easting_ft = bp_ew + dx_rot
    northing_ft = bp_ns + dy_rot

    # Elevation relative to Survey Point (in feet)
    elevation_rel_ft = pt.Z - svp_pos.Z
    elevation_total_ft = elevation_rel_ft + svp_elev_ft

    # Set custom parameters - assuming these parameters accept feet directly
    param_x = pile.LookupParameter("Co-ord X (E/W)")
    param_y = pile.LookupParameter("Co-ord Y (N/S)")
    param_z = pile.LookupParameter("Co-ord Z (Elev)")

    if param_x and param_x.StorageType == StorageType.Double:
        param_x.Set(easting_ft)
    if param_y and param_y.StorageType == StorageType.Double:
        param_y.Set(northing_ft)
    if param_z and param_z.StorageType == StorageType.Double:
        param_z.Set(elevation_total_ft)  # Elevation in feet

    pile_count += 1

t.Commit()

output.print_md("### Set coordinates for **{}** pile foundations.\n- Easting/Northing set (relative to Survey Point). \n- Elevation set (relative to Survey Point).".format(pile_count))
