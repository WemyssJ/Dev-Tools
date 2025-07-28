from pyrevit import script
from pyrevit.revit import doc
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, StorageType
import webbrowser
import math

output = script.get_output()

def get_param_value(elem, name):
    param = elem.LookupParameter(name)
    if param is None:
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

def feet_to_m(feet):
    return feet / 3.28084  # Convert feet to meters

def os_grid_ref(easting, northing, digits=10):
    # Only allow coordinates in valid OS range
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


# Get all foundations
all_foundations = (FilteredElementCollector(doc)
                   .OfCategory(BuiltInCategory.OST_StructuralFoundation)
                   .WhereElementIsNotElementType()
                   .ToElements())

# Filter only foundations with name "Pile"
foundations = [f for f in all_foundations if f.Name.strip().lower() == "pile"]

if not foundations:
    output.print_md("No structural foundations named 'Pile' found.")
    script.exit()

# Print all parameters on the first element
sample = foundations[0]
output.print_md("### Parameters for element ID {}".format(sample.Id))

for p in sample.Parameters:
    try:
        name = p.Definition.Name
        stype = p.StorageType
        if stype == StorageType.Double:
            val = p.AsDouble()
        elif stype == StorageType.Integer:
            val = p.AsInteger()
        elif stype == StorageType.String:
            val = p.AsString()
        else:
            val = "Unsupported storage type"
        output.print_md("- {} (StorageType {}): {}".format(name, stype, val))
    except Exception as ex:
        output.print_md("- {}: Error reading param ({})".format(p.Definition.Name, ex))


# Now attempt to collect coordinates
points = []

for f in foundations:
    x_val = get_param_value(f, "Co-ord X (E/W)")
    y_val = get_param_value(f, "Co-ord Y (N/S)")

    output.print_md("Element ID {} param X='{}' param Y='{}'".format(f.Id, x_val, y_val))

    if x_val is None or y_val is None:
        output.print_md("Skipping element ID {} because coordinate parameters not found or empty".format(f.Id))
        continue

    # Convert feet to meters here
    x_m = feet_to_m(x_val)
    y_m = feet_to_m(y_val)

    points.append((x_m, y_m))

if not points:
    output.print_md("No valid coordinates found on 'Pile' foundations.")
    script.exit()

gridrefs = []
for e, n in points:
    gridref = os_grid_ref(e, n)
    if gridref:
        entry = "{}|{:.4f}_s__c__s_{:.4f}|1".format(gridref, e, n)
        gridrefs.append(entry)
    else:
        output.print_md("Coordinate ({}, {}) out of OS Grid bounds.".format(e, n))

if not gridrefs:
    output.print_md("No valid OS grid references generated.")
    script.exit()

url = "https://gridreferencefinder.com/#gr=" + ",".join(gridrefs)
output.print_md("Opening browser with {} points...".format(len(gridrefs)))
webbrowser.open(url)
