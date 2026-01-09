import os
import subprocess
import csv
from urllib.parse import quote
from math import sin, cos, tan, sqrt, atan2, radians
import webbrowser

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
exiftool_path = r"C:\exiftool\exiftool.exe"
folder = r"C:\Users\wemyssj\OneDrive - Craddys\13914 - Plots 2 - 3, Silverthorne Lane\20260107 Drone photos"
output_csv = os.path.join(folder, "OSGridExtraction.csv")

# Keep your original SharePoint base URL from your other script
SHAREPOINT_BASE_URL = (
    "https://craddysuk-my.sharepoint.com/my"
    "?viewid=65e14d32%2Dda7d%2D477f%2Dba37%2D0b795e9f474b"
    "&source=waffle"
    "&id=%2Fpersonal%2Fjoe%5Fwemyss%5Fcraddys%5Fco%5Fuk%2FDocuments"
    "%2F13914%20%2D%20Plots%202%20%2D%203%2C%20Silverthorne%20Lane"
    "%2F20260107%20Drone%20photos%2F{filename}"
    "&parent=%2Fpersonal%2Fjoe%5Fwemyss%5Fcraddys%5Fco%5Fuk%2FDocuments"
    "%2F13914%20%2D%20Plots%202%20%2D%203%2C%20Silverthorne%20Lane"
    "%2F20260107%20Drone%20photos"
)

# --------------------------------------------------
# DECIMAL → DMS (ABSOLUTE)
# --------------------------------------------------
def dec_to_dms(dd):
    dd = abs(dd)
    d = int(dd)
    m = int((dd - d) * 60)
    s = (dd - d - m / 60) * 3600
    return f"{d}; {m}; {s:.6f}"

# --------------------------------------------------
# WGS84 → OSGB36 (FULL HELMERT)
# --------------------------------------------------
def wgs84_to_osgb36(lat, lon):
    a, b = 6378137.0, 6356752.3141
    e2 = 1 - (b*b)/(a*a)

    lat = radians(lat)
    lon = radians(lon)

    nu = a / sqrt(1 - e2*sin(lat)**2)
    x = nu*cos(lat)*cos(lon)
    y = nu*cos(lat)*sin(lon)
    z = (1 - e2)*nu*sin(lat)

    tx, ty, tz = -446.448, 125.157, -542.060
    s = 20.4894e-6
    rx = radians(-0.1502/3600)
    ry = radians(-0.2470/3600)
    rz = radians(-0.8421/3600)

    x2 = tx + (1+s)*x - rz*y + ry*z
    y2 = ty + rz*x + (1+s)*y - rx*z
    z2 = tz - ry*x + rx*y + (1+s)*z

    a, b = 6377563.396, 6356256.909
    e2 = 1 - (b*b)/(a*a)

    p = sqrt(x2*x2 + y2*y2)
    lat0 = 0
    lat = atan2(z2, p*(1-e2))

    while abs(lat - lat0) > 1e-10:
        lat0 = lat
        nu = a / sqrt(1 - e2*sin(lat)**2)
        lat = atan2(z2 + e2*nu*sin(lat), p)

    lon = atan2(y2, x2)

    F0 = 0.9996012717
    lat0 = radians(49)
    lon0 = radians(-2)
    N0, E0 = -100000, 400000
    n = (a-b)/(a+b)

    nu = a*F0 / sqrt(1 - e2*sin(lat)**2)
    rho = a*F0*(1-e2) / (1 - e2*sin(lat)**2)**1.5
    eta2 = nu/rho - 1

    M = b*F0 * (
        (1+n+5/4*n*n+5/4*n**3)*(lat-lat0)
        - (3*n+3*n*n+21/8*n**3)*sin(lat-lat0)*cos(lat+lat0)
        + (15/8*n*n+15/8*n**3)*sin(2*(lat-lat0))*cos(2*(lat+lat0))
        - (35/24*n**3)*sin(3*(lat-lat0))*cos(3*(lat+lat0))
    )

    dL = lon - lon0

    N = N0 + M \
        + nu*sin(lat)*cos(lat)*dL**2/2 \
        + nu*sin(lat)*cos(lat)**3*(5-tan(lat)**2+9*eta2)*dL**4/24

    E = E0 \
        + nu*cos(lat)*dL \
        + nu*cos(lat)**3*(nu/rho-tan(lat)**2)*dL**3/6

    return E, N

# --------------------------------------------------
# OS GRID REF (10-FIGURE)
# --------------------------------------------------
def en_to_osref(E, N):
    if not (0 <= E < 700000 and 0 <= N < 1300000):
        return None

    letters = "ABCDEFGHJKLMNOPQRSTUVWXYZ"

    e100k = int(E) // 100000
    n100k = int(N) // 100000

    l1 = (19 - n100k) - ((19 - n100k) % 5) + (e100k + 10) // 5
    l2 = ((19 - n100k) * 5 % 25) + (e100k % 5)

    prefix = letters[l1] + letters[l2]

    e = str(int(E % 100000)).zfill(5)
    n = str(int(N % 100000)).zfill(5)

    return f"{prefix}{e}{n}"

# --------------------------------------------------
# MAIN CSV WRITE
# --------------------------------------------------
gridfinder_entries = []

with open(output_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "File",
        "Lat DMS", "Lat Ref",
        "Lon DMS", "Lon Ref",
        "Altitude (m)",
        "OS Grid (10)",
        "Private Sharepoint Link",
        "Public Sharepoint Link"
    ])

    for r, _, files in os.walk(folder):
        for file in files:
            if not file.lower().endswith((".jpg", ".jpeg", ".heic")):
                continue

            path = os.path.join(r, file)

            # Extract EXIF GPS
            res = subprocess.run(
                [exiftool_path,
                 "-GPSLatitude", "-GPSLatitudeRef",
                 "-GPSLongitude", "-GPSLongitudeRef",
                 "-GPSAltitude", "-GPSAltitudeRef",
                 "-n", path],
                capture_output=True, text=True
            )

            if not res.stdout.strip():
                continue

            d = {}
            for line in res.stdout.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    d[k.strip()] = v.strip()

            lat = float(d["GPS Latitude"])
            lon = float(d["GPS Longitude"])

            # Altitude handling
            alt = d.get("GPS Altitude")
            alt_ref = d.get("GPS Altitude Ref", "0")
            if alt is not None:
                alt = float(alt)
                if alt_ref == "1":
                    alt = -alt
            else:
                alt = ""

            # OS Grid
            E, N = wgs84_to_osgb36(lat, lon)
            os10 = en_to_osref(E, N)

            if os10:
                prefix = os10[:2]
                e5 = os10[2:7]
                n5 = os10[7:12]
                pattern = f"{prefix}_s_{e5}_s_{n5}"
                gridfinder_entries.append(f"{os10}|{pattern}|1")

            # Encode filename for SharePoint
            encoded_file = quote(file)

            # Private SharePoint URL using your original base
            private_url = SHAREPOINT_BASE_URL.format(filename=encoded_file)

            # Placeholder Public SharePoint URL (replace later with Power Automate CSV)
            public_url = f"PUBLIC_LINK_FOR_{encoded_file}"

            # Write CSV row
            writer.writerow([
                file,
                dec_to_dms(lat), d["GPS Latitude Ref"],
                dec_to_dms(lon), d["GPS Longitude Ref"],
                alt,
                os10 or "Out of range",
                private_url,
                public_url
            ])

# --------------------------------------------------
# OPEN GRIDREFERENCEFINDER
# --------------------------------------------------
if gridfinder_entries:
    joined = ",".join(gridfinder_entries)
    url = f"https://gridreferencefinder.com/#gr={joined}"
    webbrowser.open(url)
