from pyrevit import script
from pyrevit.revit import doc
from Autodesk.Revit.DB import BasePoint, FilteredElementCollector, Grid, IntersectionResultArray, SetComparisonResult
from System import Array
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
    print("DEBUG: Input Easting: {}, Northing: {}".format(easting, northing))

    if not (0 <= easting < 700000 and 0 <= northing < 1300000):
        print("DEBUG: Input out of OS grid bounds")
        return ""

    # The grid letters exclude 'I' - this is the correct 25-letter alphabet for OS grid
    grid_letters = "ABCDEFGHJKLMNOPQRSTUVWXYZ"

    # Get the 100km-grid indices
    e100km = int(easting) // 100000
    n100km = int(northing) // 100000
    print("DEBUG: 100km grid indices -> e100k: {}, n100k: {}".format(e100km, n100km))

    # Official OS Grid Reference letter calculation from Movable Type source
    # translate those into numeric equivalents of the grid letters
    l1 = (19 - n100km) - (19 - n100km) % 5 + int((e100km + 10) / 5)
    l2 = (19 - n100km) * 5 % 25 + e100km % 5
    
    print("DEBUG: Letter indices -> l1: {}, l2: {}".format(l1, l2))

    if l1 < 0 or l1 >= len(grid_letters) or l2 < 0 or l2 >= len(grid_letters):
        print("DEBUG: Letter indices out of range")
        return ""

    letters = grid_letters[l1] + grid_letters[l2]
    print("DEBUG: Grid letters: {}".format(letters))

    e_remainder = int(round(easting)) % 100000
    n_remainder = int(round(northing)) % 100000
    print("DEBUG: Easting remainder: {}, Northing remainder: {}".format(e_remainder, n_remainder))

    digits_per_coord = digits // 2
    e_str = str(e_remainder).zfill(5)[:digits_per_coord]
    n_str = str(n_remainder).zfill(5)[:digits_per_coord]
    print("DEBUG: Numeric parts -> e_str: {}, n_str: {}".format(e_str, n_str))

    result = "{}{}{}".format(letters, e_str, n_str)
    print("DEBUG: Final OS Grid Reference: {}".format(result))

    return result

def get_grid_intersections():
    """Find all grid intersections in the model"""
    from Autodesk.Revit.DB import Line, XYZ
    
    grids = FilteredElementCollector(doc).OfClass(Grid).ToElements()
    
    if len(grids) < 2:
        print("Not enough grids found (need at least 2)")
        return []
    
    intersections = []
    
    # Compare each grid with every other grid to find intersections
    for i, grid1 in enumerate(grids):
        for j, grid2 in enumerate(grids):
            if i >= j:  # Skip same grid and avoid duplicates
                continue
                
            try:
                # Get the curves of the grids
                curve1 = grid1.Curve
                curve2 = grid2.Curve
                
                # Try to find intersection using geometric calculation
                intersection_point = None
                
                # Check if both curves are lines (most common case)
                if isinstance(curve1, Line) and isinstance(curve2, Line):
                    line1 = curve1
                    line2 = curve2
                    
                    # Get line parameters
                    p1 = line1.GetEndPoint(0)
                    p2 = line1.GetEndPoint(1)
                    p3 = line2.GetEndPoint(0)
                    p4 = line2.GetEndPoint(1)
                    
                    # Calculate intersection using line-line intersection formula
                    # Line 1: p1 + t*(p2-p1)
                    # Line 2: p3 + s*(p4-p3)
                    
                    d1 = p2 - p1  # Direction vector of line 1
                    d2 = p4 - p3  # Direction vector of line 2
                    
                    # Cross product to check if lines are parallel
                    cross = d1.X * d2.Y - d1.Y * d2.X
                    
                    if abs(cross) > 1e-10:  # Lines are not parallel
                        # Calculate intersection parameters
                        dp = p1 - p3
                        t = (dp.X * d2.Y - dp.Y * d2.X) / cross
                        
                        # Calculate intersection point
                        intersection_point = p1 + t * d1
                        
                        # Verify the intersection is within reasonable bounds
                        # (optional: could check if intersection is on both line segments)
                        
                if intersection_point:
                    # Get grid names
                    grid1_name = grid1.Name
                    grid2_name = grid2.Name
                    
                    intersections.append({
                        'point': intersection_point,
                        'grid1': grid1_name,
                        'grid2': grid2_name,
                        'name': "{}_{}".format(grid1_name, grid2_name)
                    })
                    
            except Exception as e:
                print("Error finding intersection between {} and {}: {}".format(
                    grid1.Name, grid2.Name, str(e)))
    
    return intersections

def transform_to_survey_point(point, pbp):
    """Transform a point from project coordinates to survey coordinates"""
    if not pbp:
        print("Warning: No Project Base Point found - using project coordinates")
        return type('Point', (), {'X': feet_to_m(point.X), 'Y': feet_to_m(point.Y)})()
        
    # Get the survey point offset from project base point
    ns_raw = get_param_value(pbp, "N/S")
    ew_raw = get_param_value(pbp, "E/W")
    elev_raw = get_param_value(pbp, "Elev")
    angle = get_param_value(pbp, "Angle to True North")
    
    if ns_raw is None or ew_raw is None:
        print("Warning: Cannot get survey coordinates - using project coordinates")
        return type('Point', (), {'X': feet_to_m(point.X), 'Y': feet_to_m(point.Y)})()
    
    # Apply scaling if needed
    if ns_raw > 3000000:
        print("DEBUG: Scaling N/S coordinate by factor of 10")
        ns_raw = ns_raw / 10
    
    # Convert project coordinates from feet to meters
    project_x_m = feet_to_m(point.X)
    project_y_m = feet_to_m(point.Y)
    
    print("DEBUG: Project coordinates (m): X={:.3f}, Y={:.3f}".format(project_x_m, project_y_m))
    
    # Apply rotation first if there's an angle to true north
    if angle is not None and angle != 0:
        print("DEBUG: Applying rotation of {:.3f} degrees".format(rad_to_deg(angle)))
        cos_angle = math.cos(angle)
        sin_angle = math.sin(angle)
        
        # Rotate the project coordinates
        rotated_x = project_x_m * cos_angle - project_y_m * sin_angle
        rotated_y = project_x_m * sin_angle + project_y_m * cos_angle
        
        project_x_m = rotated_x
        project_y_m = rotated_y
        
        print("DEBUG: After rotation (m): X={:.3f}, Y={:.3f}".format(project_x_m, project_y_m))
    
    # Convert survey offset from feet to meters
    survey_offset_x = feet_to_m(ew_raw)  # Easting
    survey_offset_y = feet_to_m(ns_raw)  # Northing
    
    print("DEBUG: Survey offset (m): Easting={:.3f}, Northing={:.3f}".format(survey_offset_x, survey_offset_y))
    
    # Add the survey offset to get final coordinates
    final_x = project_x_m + survey_offset_x  # Easting
    final_y = project_y_m + survey_offset_y  # Northing
    
    print("DEBUG: Final coordinates (m): Easting={:.3f}, Northing={:.3f}".format(final_x, final_y))
    
    return type('Point', (), {'X': final_x, 'Y': final_y})()

# Get shared Project Base Point
pbp = None
for bp in FilteredElementCollector(doc).OfClass(BasePoint):
    if bp.IsShared:
        pbp = bp
        break

if not pbp:
    print("Project Base Point not found - coordinates may not be accurate.")

# Find all grid intersections
intersections = get_grid_intersections()

if not intersections:
    print("No grid intersections found.")
else:
    print("Found {} grid intersections:".format(len(intersections)))
    
    url_parts = []
    
    for i, intersection in enumerate(intersections):
        # Transform to survey coordinates
        survey_point = transform_to_survey_point(intersection['point'], pbp)
        
        # Convert to OS grid coordinates (easting, northing)
        easting = survey_point.X
        northing = survey_point.Y
        
        # Get OS grid reference
        grid_ref = os_grid_ref(easting, northing, digits=10)
        
        if grid_ref:
            point_name = intersection['name']
            print("\nIntersection {}: {} (Grids: {} & {})".format(
                i+1, point_name, intersection['grid1'], intersection['grid2']))
            print("  Easting: {:.5f} m, Northing: {:.5f} m".format(easting, northing))
            print("  OS Grid Reference: {}".format(grid_ref))
            
            # Format for URL: GridRef|Easting_s__c__s_Northing|1
            url_part = "{}|{:.5f}_s__c__s_{:.5f}|1".format(grid_ref, easting, northing)
            url_parts.append(url_part)
        else:
            print("\nIntersection {}: {} - Could not calculate OS Grid Reference".format(
                i+1, intersection['name']))
    
    if url_parts:
        # Create the full URL
        url = "https://gridreferencefinder.com/#gr=" + ",".join(url_parts)
        print("\n" + "="*50)
        print("Opening all intersections in browser:")
        print(url)
        print("="*50)
        webbrowser.open(url)
    else:
        print("\nNo valid OS Grid References calculated.")

# Also show base point info if available
if pbp:
    ns_raw = get_param_value(pbp, "N/S")
    ew_raw = get_param_value(pbp, "E/W")
    elev_raw = get_param_value(pbp, "Elev")
    angle = get_param_value(pbp, "Angle to True North")

    print("\n" + "="*50)
    print("PROJECT BASE POINT INFO:")
    print("="*50)
    
    if ns_raw is not None and ew_raw is not None:
        if ns_raw > 3000000:
            ns_raw = ns_raw / 10
        
        ns_m = feet_to_m(ns_raw)
        ew_m = feet_to_m(ew_raw)
        elev_m = feet_to_m(elev_raw) if elev_raw is not None else None
        
        print("Survey Coordinates:")
        print("  Easting: {:.5f} m".format(ew_m))
        print("  Northing: {:.5f} m".format(ns_m))
        
        if elev_m is not None:
            print("  Elevation: {:.3f} m".format(elev_m))
        
        if angle is not None:
            print("  Angle to True North: {} deg".format(rad_to_deg(angle)))
    else:
        print("Base point coordinates not available.")