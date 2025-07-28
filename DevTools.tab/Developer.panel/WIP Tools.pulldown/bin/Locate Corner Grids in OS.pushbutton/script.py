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

# Get both Project Base Point and Survey Point
base_points = list(FilteredElementCollector(doc).OfClass(BasePoint))
pbp = next((bp for bp in base_points if not bp.IsShared), None)  # Project Base Point
survey_point = next((bp for bp in base_points if bp.IsShared), None)  # Survey Point

if not pbp or not survey_point:
    print("Error: Could not find both Project Base Point and Survey Point.")
    script.exit()

# Get Project Base Point parameters (for real-world coordinates and rotation)
pbp_ns = get_param_value(pbp, "N/S")
pbp_ew = get_param_value(pbp, "E/W")
angle_to_true_north_rad = get_param_value(pbp, "Angle to True North")

if pbp_ns is None or pbp_ew is None or angle_to_true_north_rad is None:
    print("Error: Missing Project Base Point parameters (N/S, E/W, or Angle to True North).")
    script.exit()

# Get Survey Point position (this is its position in the internal coordinate system)
survey_position = survey_point.Position
survey_x_internal = survey_position.X  # feet
survey_y_internal = survey_position.Y  # feet

# Get Project Base Point position (this is its position in the internal coordinate system)
pbp_position = pbp.Position
pbp_x_internal = pbp_position.X  # feet
pbp_y_internal = pbp_position.Y  # feet

# Calculate the offset between Survey Point and Project Base Point in internal coordinates
offset_x_feet = survey_x_internal - pbp_x_internal
offset_y_feet = survey_y_internal - pbp_y_internal

print("Survey Point internal position: X={:.3f}ft, Y={:.3f}ft".format(survey_x_internal, survey_y_internal))
print("Project Base Point internal position: X={:.3f}ft, Y={:.3f}ft".format(pbp_x_internal, pbp_y_internal))
print("Offset (Survey - Project) in internal coords: X={:.3f}ft, Y={:.3f}ft".format(offset_x_feet, offset_y_feet))
print("Project Base Point real-world coords: E={:.3f}m, N={:.3f}m".format(feet_to_m(pbp_ew), feet_to_m(pbp_ns)))

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

# Find min and max X and Y among intersection points
xs = [pt[0] for pt in intersections]
ys = [pt[1] for pt in intersections]

min_x, max_x = min(xs), max(xs)
min_y, max_y = min(ys), max(ys)

# Select only the four corner points
corner_points = [
    (min_x, min_y),
    (min_x, max_y),
    (max_x, min_y),
    (max_x, max_y),
]

# Convert to OS Grid Reference format only for the corner points
gridrefs = []
for x, y in corner_points:
    # Convert from feet to meters
    x_m = feet_to_m(x)
    y_m = feet_to_m(y)
    
    # Rotate point from Project North to True North first
    x_rot, y_rot = rotate_point(x_m, y_m, -angle_to_true_north_rad)
    
    # Add the Survey Point offset to the rotated grid intersection position
    offset_x_rot, offset_y_rot = rotate_point(feet_to_m(offset_x_feet), feet_to_m(offset_y_feet), -angle_to_true_north_rad)
    
    # Add Project Base Point real-world coordinates and the rotated offset
    abs_e = feet_to_m(pbp_ew) + x_rot + offset_x_rot
    abs_n = feet_to_m(pbp_ns) + y_rot + offset_y_rot

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
