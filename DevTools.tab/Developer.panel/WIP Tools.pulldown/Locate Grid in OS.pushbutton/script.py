from pyrevit import script
from pyrevit.revit import doc
from Autodesk.Revit.DB import FilteredElementCollector, Grid, BasePoint, XYZ, Line, Curve
import webbrowser
import math

output = script.get_output()

def feet_to_m(feet):
    return feet * 0.3048

def rad_to_deg(radians):
    return round(radians * (180.0 / math.pi), 3)

def get_param_value(elem, name):
    param = elem.LookupParameter(name)
    if param:
        return param.AsDouble()
    return None

def os_grid_ref(easting, northing, digits=10):
    if not (0 <= easting < 700000 and 0 <= northing < 1300000):
        return ""

    grid_letters = "ABCDEFGHJKLMNOPQRSTUVWXYZ"
    e100km = int(easting) // 100000
    n100km = int(northing) // 100000

    l1 = (19 - n100km) - (19 - n100km) % 5 + int((e100km + 10) / 5)
    l2 = (19 - n100km) * 5 % 25 + e100km % 5

    if l1 < 0 or l1 >= len(grid_letters) or l2 < 0 or l2 >= len(grid_letters):
        return ""

    letters = grid_letters[l1] + grid_letters[l2]
    e_remainder = int(round(easting)) % 100000
    n_remainder = int(round(northing)) % 100000
    digits_per_coord = digits // 2
    e_str = str(e_remainder).zfill(5)[:digits_per_coord]
    n_str = str(n_remainder).zfill(5)[:digits_per_coord]

    return "{}{}{}".format(letters, e_str, n_str)

def intersect_lines(line1, line2):
    p1 = line1.GetEndPoint(0)
    p2 = line1.GetEndPoint(1)
    p3 = line2.GetEndPoint(0)
    p4 = line2.GetEndPoint(1)

    # 2D line intersection
    x1, y1 = p1.X, p1.Y
    x2, y2 = p2.X, p2.Y
    x3, y3 = p3.X, p3.Y
    x4, y4 = p4.X, p4.Y

    denom = (x1 - x2)*(y3 - y4) - (y1 - y2)*(x3 - x4)
    if denom == 0:
        return None  # Parallel lines

    px = ((x1*y2 - y1*x2)*(x3 - x4) - (x1 - x2)*(x3*y4 - y3*x4)) / denom
    py = ((x1*y2 - y1*x2)*(y3 - y4) - (y1 - y2)*(x3*y4 - y3*x4)) / denom

    # Check if within both segments
    def between(a, b, c): return min(a, b) <= c <= max(a, b)
    if (between(x1, x2, px) and between(y1, y2, py) and
        between(x3, x4, px) and between(y3, y4, py)):
        return XYZ(px, py, 0)
    else:
        return None

def rotate_point(x, y, angle_rad):
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    x_rot = x * cos_theta - y * sin_theta
    y_rot = x * sin_theta + y * cos_theta
    return x_rot, y_rot

# Get Project Base Point (for origin offset)
pbp = next((bp for bp in FilteredElementCollector(doc).OfClass(BasePoint) if not bp.IsShared), None)
if not pbp:
    print("Project Base Point not found.")
    script.exit()

ns_raw = get_param_value(pbp, "N/S")
ew_raw = get_param_value(pbp, "E/W")
angle_to_true_north_rad = get_param_value(pbp, "Angle to True North")

if ns_raw is None or ew_raw is None or angle_to_true_north_rad is None:
    print("Error: Missing Project Base Point parameters (N/S, E/W, or Angle to True North).")
    script.exit()

# Convert origin to meters
origin_x_m = feet_to_m(ew_raw)
origin_y_m = feet_to_m(ns_raw)

# Gather all grids and extract their curves
grids = list(FilteredElementCollector(doc).OfClass(Grid))
grid_curves = [g.Curve for g in grids if isinstance(g.Curve, Line)]

# Compute all unique intersection points
intersections = []
for i in range(len(grid_curves)):
    for j in range(i + 1, len(grid_curves)):
        pt = intersect_lines(grid_curves[i], grid_curves[j])
        if pt:
            # Remove duplicates by position (rounded to 3 decimal meters)
            rounded = (round(pt.X, 3), round(pt.Y, 3))
            if rounded not in intersections:
                intersections.append(rounded)

print("Found {} intersection points.".format(len(intersections)))

# Convert to OS Grid Reference format
gridrefs = []
for x, y in intersections:
    # Rotate point from Project North to True North
    x_rot, y_rot = rotate_point(x, y, -angle_to_true_north_rad)

    e_m = feet_to_m(x_rot)
    n_m = feet_to_m(y_rot)

    abs_e = origin_x_m + e_m
    abs_n = origin_y_m + n_m

    gridref = os_grid_ref(abs_e, abs_n)
    if gridref:
        entry = "{}|{:.4f}_s__c__s_{:.4f}|1".format(gridref, abs_e, abs_n)
        gridrefs.append(entry)

if not gridrefs:
    print("No valid OS grid references found.")
else:
    url = "https://gridreferencefinder.com/#gr=" + ",".join(gridrefs)
    print("\nOpening browser with {} points...".format(len(gridrefs)))
    webbrowser.open(url)
