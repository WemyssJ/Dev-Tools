from pyrevit import script
from pyrevit.revit import doc
from Autodesk.Revit.DB import BasePoint, FilteredElementCollector
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



# Get shared Project Base Point
pbp = None
for bp in FilteredElementCollector(doc).OfClass(BasePoint):
    if bp.IsShared:
        pbp = bp
        break

if not pbp:
    print("Project Base Point not found.")
else:
    ns_raw = get_param_value(pbp, "N/S")
    ew_raw = get_param_value(pbp, "E/W")
    elev_raw = get_param_value(pbp, "Elev")
    angle = get_param_value(pbp, "Angle to True North")

    print("\nRaw Revit parameters (internal units, feet):")
    print("N/S raw: {}".format(ns_raw))
    print("E/W raw: {}".format(ew_raw))
    print("Elev raw: {}".format(elev_raw))

    if ns_raw is None or ew_raw is None:
        print("\nError: N/S or E/W parameter missing.")
    else:
        if ns_raw > 3000000:
            print("\nN/S raw seems too large, scaling down by factor 10.")
            ns_raw = ns_raw / 10

        ns_m = feet_to_m(ns_raw)
        ew_m = feet_to_m(ew_raw)
        elev_m = feet_to_m(elev_raw) if elev_raw is not None else None

        print("\nConverted coordinates (meters):")
        print("N/S: {:.5f} m".format(ns_m))
        print("E/W: {:.5f} m".format(ew_m))

        grid_ref = os_grid_ref(ew_m, ns_m, digits=10)

        if grid_ref:
            url = "https://gridreferencefinder.com/#gr={}|{:.4f}_s__c__s_{:.5f}|1".format(grid_ref, ew_m, ns_m)
            print("\nOS Grid Reference: {}".format(grid_ref))
            print("\nOpening in browser:\n" + url)
            webbrowser.open(url)
        else:
            print("\nCould not calculate OS Grid Reference from coordinates.")

    if elev_m is not None:
        print("\nElevation: {:.3f} m".format(elev_m))
    else:
        print("\nElevation parameter missing.")

    if angle is not None:
        print("Angle to True North: {} deg".format(rad_to_deg(angle)))
    else:
        print("Angle to True North: N/A")
