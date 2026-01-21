from pyrevit import script
from pyrevit.revit import doc
from Autodesk.Revit.DB import BasePoint, FilteredElementCollector, StorageType
import webbrowser
import math

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

output = script.get_output()


# --------------------------------------------------------
# UNIT CONVERSIONS
# --------------------------------------------------------
def feet_to_m(feet):
    return feet * 0.3048

def rad_to_deg(radians):
    return round(radians * (180.0 / math.pi), 8)


# --------------------------------------------------------
# GENERIC PARAMETER GETTER
# --------------------------------------------------------
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


# --------------------------------------------------------
# OSGB36 easting/northing -> Grid Reference
# --------------------------------------------------------
def os_grid_ref(easting, northing, digits=12):
    if not (0 <= easting < 700000 and 0 <= northing < 1300000):
        return ""

    grid_letters = "ABCDEFGHJKLMNOPQRSTUVWXYZ"
    e100km = int(easting) // 100000
    n100km = int(northing) // 100000

    l1 = (19 - n100km) - (19 - n100km) % 5 + int((e100km + 10) / 5)
    l2 = (19 - n100km) * 5 % 25 + (e100km % 5)

    if l1 < 0 or l1 >= len(grid_letters) or l2 < 0 or l2 >= len(grid_letters):
        return ""

    letters = grid_letters[l1] + grid_letters[l2]

    e_remainder = easting % 100000
    n_remainder = northing % 100000
    digits_per_coord = digits // 2

    scale = 10 ** (5 - digits_per_coord)
    e_str = str(int(round(e_remainder / scale))).zfill(digits_per_coord)
    n_str = str(int(round(n_remainder / scale))).zfill(digits_per_coord)

    return "{}{}{}".format(letters, e_str, n_str)


# --------------------------------------------------------
# OSGB36 (E,N) -> WGS84 (lat, lon) using Helmert transform
# --------------------------------------------------------
def osgb36_to_wgs84(easting, northing):
    # Airy 1830 major/minor axes
    a = 6377563.396
    b = 6356256.909
    F0 = 0.9996012717
    lat0 = math.radians(49)
    lon0 = math.radians(-2)
    N0 = -100000
    E0 = 400000
    e2 = 1 - (b * b) / (a * a)
    n = (a - b) / (a + b)

    lat = lat0
    M = 0
    while True:
        lat_prev = lat
        M = (
            b * F0
            * (
                (1 + n + (5 / 4) * n ** 2 + (5 / 4) * n ** 3) * (lat - lat0)
                - (3 * n + 3 * n ** 2 + (21 / 8) * n ** 3) * math.sin(lat - lat0) * math.cos(lat + lat0)
                + ((15 / 8) * n ** 2 + (15 / 8) * n ** 3) * math.sin(2 * (lat - lat0)) * math.cos(2 * (lat + lat0))
                - (35 / 24) * n ** 3 * math.sin(3 * (lat - lat0)) * math.cos(3 * (lat + lat0))
            )
        )
        lat = (northing - N0 - M) / (a * F0) + lat
        if abs(lat - lat_prev) < 1e-10:
            break

    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    nu = a * F0 / math.sqrt(1 - e2 * sin_lat ** 2)
    rho = a * F0 * (1 - e2) / (1 - e2 * sin_lat ** 2) ** 1.5
    eta2 = nu / rho - 1

    tan_lat = math.tan(lat)
    sec_lat = 1 / cos_lat
    E_diff = easting - E0

    lat = (
        lat
        - (tan_lat / (2 * rho * nu)) * E_diff ** 2
        + (tan_lat / (24 * rho * nu ** 3)) * (5 + 3 * tan_lat ** 2 + eta2 - 9 * tan_lat ** 2 * eta2) * E_diff ** 4
    )

    lon = lon0 + (
        E_diff * sec_lat / nu
        - (sec_lat / (6 * nu ** 3)) * (1 + 2 * tan_lat ** 2 + eta2) * E_diff ** 3
        + (sec_lat / (120 * nu ** 5)) * (5 + 28 * tan_lat ** 2 + 24 * tan_lat ** 4) * E_diff ** 5
    )

    lat_deg = math.degrees(lat)
    lon_deg = math.degrees(lon)
    return lat_deg, lon_deg


# --------------------------------------------------------
# GET PROJECT BASE POINT
# --------------------------------------------------------
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
    output.print_md("Error: Missing N/S or E/W.")
    script.exit()

ns_m = feet_to_m(ns_raw)
ew_m = feet_to_m(ew_raw)

grid_ref = os_grid_ref(ew_m, ns_m, digits=12)

# Convert to WGS84 for Google Earth
lat, lon = osgb36_to_wgs84(ew_m, ns_m)

# Display output


# UK GRID REFERENCE FINDER
grf_url = "https://gridreferencefinder.com/#gr={}|{}_{}_{}".format(grid_ref, ew_m, ns_m, 1)

# GOOGLE EARTH (correct WGS84 coordinates)
earth_url = "https://earth.google.com/web/@{},{},1000a".format(lat, lon)

# Open both
if __shiftclick__:
    output.print_md("Opening both Approximate location on Google Earth...")
    webbrowser.open(earth_url)
else:
    output.print_md("Opening location on UK Grid Finder...")
    webbrowser.open(grf_url)


