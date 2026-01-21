from Autodesk.Revit.DB import *
from pyrevit import revit, script
import math
import re

##############################################################################################
# TELEMETRY IMPORTS #
##############################################################################################
# Only works IF specified TELEMETRY_JSON path exists within %AppData%\pyRevit\Extensions\BIMTools.extension\lib\telemetry_auto.py"
# Records tool usage by date & revit version
import os, sys

# Add lib folder for telemetry_auto
lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'lib'))
if lib_path not in sys.path:
    sys.path.append(lib_path)

import telemetry_auto

tool_name = os.path.basename(os.path.dirname(__file__)) 
TOOL_NAME = tool_name.replace(".pushbutton", "")
telemetry_auto.log_tool_usage(TOOL_NAME)
##############################################################################################

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
log_data = []

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
    if not family_name or "pile" not in family_name.lower():
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

    # Use raw feet values directly
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

    # Get pile mark
    mark_param = pile.LookupParameter("Mark")
    pile_mark = mark_param.AsString() if mark_param and mark_param.HasValue else "N/A"

    # Append log row with both ft and mm
    log_data.append((
        pile_mark,
        round(easting_ft, 3),
        round(northing_ft, 3),
        round(elevation_total_ft, 3),
        "**" + str(round(easting_ft * 304.8)) + "**",
        "**" + str(round(northing_ft * 304.8)) + "**",
        "**" + str(round(elevation_total_ft * 304.8)) + "**"
    ))

    pile_count += 1

t.Commit()

# Natural sort: by prefix and then numeric portion of mark (e.g., P1, P2, P10)
def sort_key(item):
    mark = item[0]
    match = re.search(r'(\d+)', mark)
    return (re.sub(r'\d+', '', mark), int(match.group(1)) if match else 0)

# --- Output results ---
if not log_data:
    output.print_md("No piles found in the model.")
else:
    log_data.sort(key=sort_key)
    output.print_table(
        table_data=log_data,
        title="Pile Coordinates Log",
        columns=[
            "Pile Mark",
            "Internal X (ft)", "Internal Y (ft)", "Internal Z (ft)",
            "Co-ord X (E/W) (mm)", "Co-ord Y (N/S) (mm)", "Co-ord Z (Elev) (mm)"
        ]
    )
