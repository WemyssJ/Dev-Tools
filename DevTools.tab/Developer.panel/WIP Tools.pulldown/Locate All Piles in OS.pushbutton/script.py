from pyrevit import script
from pyrevit.revit import doc
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, BuiltInParameter
import webbrowser
import math

output = script.get_output()

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

def get_param_value(elem, name):
    param = elem.LookupParameter(name)
    if param:
        if param.StorageType == 1:  # double
            return param.AsDouble()
        elif param.StorageType == 0:  # integer
            return param.AsInteger()
        elif param.StorageType == 2:  # string
            return param.AsString()
    return None

# Conversion mm to meters
def mm_to_m(mm):
    return mm / 1000.0

# Collect all structural foundation instances
foundations = FilteredElementCollector(doc) \
    .OfCategory(BuiltInCategory.OST_StructuralFoundation) \
    .WhereElementIsNotElementType() \
    .ToElements()

points = []

for f in foundations:
    x_mm = get_param_value(f, "Co-ord X (E/W)")
    y_mm = get_param_value(f, "Co-ord Y (N/S)")

    if x_mm is None or y_mm is None:
        output.print_md(f"Skipping element ID {f.Id} because coordinate parameters not found")
        continue

    x_m = mm_to_m(x_mm)
    y_m = mm_to_m(y_mm)

    # Add to list for OS Grid conversion
    points.append((x_m, y_m))

if not points:
    output.print_md("No valid coordinates found on Structural Foundations.")
    script.exit()

# Convert points to OS Grid references
gridrefs = []
for e, n in points:
    gridref = os_grid_ref(e, n)
    if gridref:
        entry = "{}|{:.4f}_s__c__s_{:.4f}|1".format(gridref, e, n)
        gridrefs.append(entry)

if not gridrefs:
    output.print_md("No valid OS grid references generated.")
    script.exit()

url = "https://gridreferencefinder.com/#gr=" + ",".join(gridrefs)
output.print_md(f"Opening browser with {len(gridrefs)} points...")
webbrowser.open(url)
