from pyrevit import script
from pyrevit.revit import doc
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, StorageType
import webbrowser
import math
import re

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
    return feet / 3.28084

def os_grid_ref(easting, northing, digits=12):
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

    e_remainder = easting % 100000
    n_remainder = northing % 100000
    digits_per_coord = digits // 2

    # Scale remainders to the required precision
    scale = 10 ** (5 - digits_per_coord)
    e_str = str(int(round(e_remainder / scale))).zfill(digits_per_coord)
    n_str = str(int(round(n_remainder / scale))).zfill(digits_per_coord)

    return "{}{}{}".format(letters, e_str, n_str)


# --- Collect Piles ---
all_foundations = (FilteredElementCollector(doc)
                   .OfCategory(BuiltInCategory.OST_StructuralFoundation)
                   .WhereElementIsNotElementType()
                   .ToElements())

foundations = [f for f in all_foundations if f.Name.strip().lower() == "pile"]

if not foundations:
    output.print_md("No structural foundations named 'Pile' found.")
    script.exit()

log_data = []

for f in foundations:
    x_val = get_param_value(f, "Co-ord X (E/W)")
    y_val = get_param_value(f, "Co-ord Y (N/S)")
    z_val = get_param_value(f, "Co-ord Z (Elev)")

    if x_val is None or y_val is None:
        continue

    x_m = feet_to_m(x_val)
    y_m = feet_to_m(y_val)
    z_m = feet_to_m(z_val) if z_val else 0.0

    gridref = os_grid_ref(x_m, y_m)

    mark_param = f.LookupParameter("Mark")
    mark = mark_param.AsString() if mark_param and mark_param.HasValue else "N/A"

    log_data.append((
        mark,
        "{0:.3f}".format(x_m),
        "{0:.3f}".format(y_m),
        "{0:.3f}".format(z_m) if z_val else "N/A",
        gridref
    ))

if not log_data:
    output.print_md("No valid coordinate data to display.")
    script.exit()

# --- Sort by Mark ---
def sort_key(item):
    mark = item[0]
    match = re.search(r'(\d+)', mark)
    return (re.sub(r'\d+', '', mark), int(match.group(1)) if match else 0)

log_data.sort(key=sort_key)

# --- Print Table ---
output.print_table(
    table_data=log_data,
    title="Pile Coordinates and OS Grid References",
    columns=[
        "Pile Mark",
        "Co-ord X (E/W) (m)",
        "Co-ord Y (N/S) (m)",
        "Co-ord Z (Elev) (m)",
        "OS Grid Reference"
    ]
)

# --- Open in Grid Reference Finder ---
gridrefs = []
for f in foundations:
    x = get_param_value(f, "Co-ord X (E/W)")
    y = get_param_value(f, "Co-ord Y (N/S)")
    if x is not None and y is not None:
        x_m = feet_to_m(x)
        y_m = feet_to_m(y)
        gridref = os_grid_ref(x_m, y_m)
        if gridref:
            gridrefs.append("{}|{:.4f}_s__c__s_{:.4f}|1".format(gridref, x_m, y_m))

if gridrefs:
    url = "https://gridreferencefinder.com/#gr=" + ",".join(gridrefs)
    output.print_md("Opening browser with {} valid OS grid points...".format(len(gridrefs)))
    webbrowser.open(url)
else:
    output.print_md("No valid OS grid references generated.")
