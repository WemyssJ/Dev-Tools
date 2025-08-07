from pyrevit import script
from pyrevit.revit import doc
from Autodesk.Revit.DB import BasePoint, FilteredElementCollector, StorageType
import webbrowser
import math

output = script.get_output()

def feet_to_m(feet):
    return feet * 0.3048

def rad_to_deg(radians):
    return round(radians * (180.0 / math.pi), 3)

def get_param_value(elem, name):
    param = elem.LookupParameter(name)
    if not param:
        for p in elem.Parameters:
            if p.Definition.Name.strip() == name.strip():
                param = p
                break
    if param:
        if param.StorageType == StorageType.Double:
            return param.AsDouble()
        elif param.StorageType == StorageType.Integer:
            return param.AsInteger()
        elif param.StorageType == StorageType.String:
            return param.AsString()
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

# Get Project Base Point
pbp = None
for bp in FilteredElementCollector(doc).OfClass(BasePoint):
    if not bp.IsShared:
        pbp = bp
        break

if not pbp:
    output.print_md("Project Base Point not found.")
    script.exit()

ns_raw = get_param_value(pbp, "N/S")
ew_raw = get_param_value(pbp, "E/W")
elev_raw = get_param_value(pbp, "Elev")
angle = get_param_value(pbp, "Angle to True North")

if ns_raw is None or ew_raw is None:
    output.print_md("Error: Missing 'N/S' or 'E/W' parameter.")
    script.exit()

ns_m = feet_to_m(ns_raw)
ew_m = feet_to_m(ew_raw)
elev_m = feet_to_m(elev_raw) if elev_raw is not None else None
angle_deg = rad_to_deg(angle) if angle is not None else None

grid_ref = os_grid_ref(ew_m, ns_m, digits=10)

# Prepare output table
table_data = [[
    "{0:.5f}".format(ns_m),
    "{0:.5f}".format(ew_m),
    "{0:.3f}".format(elev_m) if elev_m is not None else "N/A",
    grid_ref,
    "{0} deg".format(angle_deg) if angle_deg is not None else "N/A"
]]

output.print_table(
    table_data=table_data,
    title="Project Base Point Coordinates",
    columns=[
        "N/S (m)",
        "E/W (m)",
        "Elevation (m)",
        "OS Grid Reference",
        "Angle to True North"
    ]
)

# Open in browser if valid grid reference
if grid_ref:
    url = "https://gridreferencefinder.com/#gr={0}|{1:.4f}_s__c__s_{2:.5f}|1".format(
        grid_ref, ew_m, ns_m)
    output.print_md("Opening OS Grid Reference in browser...")
    webbrowser.open(url)
else:
    output.print_md("Could not calculate valid OS Grid Reference.")
