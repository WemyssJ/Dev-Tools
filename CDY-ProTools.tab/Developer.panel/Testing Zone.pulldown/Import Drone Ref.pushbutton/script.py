# -*- coding: utf-8 -*-
import csv
from pyrevit import forms, script, revit
from Autodesk.Revit import DB
from System.Windows import Window, Application
from System.Windows.Controls import ComboBox, Button, StackPanel, TextBlock
from System.Windows import Thickness
from System.Collections.Generic import List
import math

output = script.get_output()
doc = revit.doc

# --------------------------------------------------
# CSV File
# --------------------------------------------------
csv_file_path = forms.pick_file(file_ext='csv', title='Select CSV File')
if not csv_file_path:
    output.print_md("No CSV file selected. Exiting.")
    script.exit()

# --------------------------------------------------
# Utility functions
# --------------------------------------------------
def feet_to_m(feet):
    return feet / 3.28084

def m_to_feet(meters):
    return meters * 3.28084

def set_param_value(elem, name, value):
    param = elem.LookupParameter(name)
    if param and not param.IsReadOnly:
        if param.StorageType == DB.StorageType.Double:
            param.Set(value)
        elif param.StorageType == DB.StorageType.String:
            param.Set(str(value))
        elif param.StorageType == DB.StorageType.Integer:
            param.Set(int(value))

def os_grid_to_en(grid_ref):
    """
    Convert OS Grid ref (e.g., ST6018172418) to easting/northing in meters
    """
    if not grid_ref or len(grid_ref) < 2:
        return None, None
    grid_letters = "ABCDEFGHJKLMNOPQRSTUVWXYZ"
    try:
        l1 = grid_letters.index(grid_ref[0].upper())
        l2 = grid_letters.index(grid_ref[1].upper())
    except ValueError:
        return None, None
    e100km = ((l1 - 2) % 5) * 5 + (l2 % 5)
    n100km = (19 - (l1 // 5) * 5) - (l2 // 5)
    digits = str(grid_ref[2:]).strip()
    if len(digits) % 2 != 0:
        return None, None
    half = len(digits) // 2
    e_remainder = int(digits[:half].ljust(5, '0'))
    n_remainder = int(digits[half:].ljust(5, '0'))
    easting = e100km * 100000 + e_remainder
    northing = n100km * 100000 + n_remainder
    return easting, northing

# --------------------------------------------------
# Read CSV
# --------------------------------------------------
with open(csv_file_path) as csvfile:
    reader = csv.DictReader(csvfile)
    rows = list(reader)

required_headers = ["File", "OS Grid (10)", "Altitude (m)"]
for h in required_headers:
    if h not in rows[0]:
        output.print_md("Missing header: {}".format(h))
        script.exit()

if not rows:
    output.print_md("No data found in CSV. Exiting.")
    script.exit()

# --------------------------------------------------
# Collect Structural Foundation Families
# --------------------------------------------------
collector = DB.FilteredElementCollector(doc).OfClass(DB.Family)
struct_families = []

for f in collector:
    try:
        if f.FamilyCategory and f.FamilyCategory.Id.IntegerValue == int(DB.BuiltInCategory.OST_StructuralFoundation):
            struct_families.append(f)
    except:
        continue

if not struct_families:
    output.print_md("No Structural Foundation families found in the project.")
    script.exit()

family_names = [f.Name for f in struct_families]

# --------------------------------------------------
# WPF Dropdown Window
# --------------------------------------------------
class DropdownWindow(Window):
    def __init__(self, options):
        self.SelectedFamily = None
        self.Title = "Select Structural Foundation Family"
        self.Width = 400
        self.Height = 150

        panel = StackPanel()
        panel.Margin = Thickness(10)

        panel.Children.Add(TextBlock(Text="Select a Structural Foundation Family:", Margin=Thickness(0,0,0,5)))

        self.combo = ComboBox()
        self.combo.ItemsSource = List[str](options)
        self.combo.SelectedIndex = 0
        panel.Children.Add(self.combo)

        btn = Button(Content="OK", Width=80, Margin=Thickness(0,10,0,0))
        btn.Click += self.btn_click
        panel.Children.Add(btn)

        self.Content = panel

    def btn_click(self, sender, e):
        idx = self.combo.SelectedIndex
        if idx >= 0:
            self.SelectedFamily = struct_families[idx]
        self.Close()

# Show the dropdown
win = DropdownWindow(family_names)
app = Application.Current
if not app:
    app = Application()
win.ShowDialog()

selected_family = win.SelectedFamily

if not selected_family:
    output.print_md("No family selected. Exiting.")
    script.exit()

# --------------------------------------------------
# Get first FamilySymbol (type) from selected family
# --------------------------------------------------
symbols = DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol)
symbols = [s for s in symbols if s.Family.Id == selected_family.Id]

if not symbols:
    output.print_md("Selected family has no types. Exiting.")
    script.exit()

family_symbol = symbols[0]  # pick first type

if not family_symbol.IsActive:
    family_symbol.Activate()
    doc.Regenerate()

# --------------------------------------------------
# Get Project Base Point offsets (non-shared)
# --------------------------------------------------
pbp = None
for bp in DB.FilteredElementCollector(doc).OfClass(DB.BasePoint):
    if not bp.IsShared:
        pbp = bp
        break

pbp_e_ft = 0.0
pbp_n_ft = 0.0
pbp_z_ft = 0.0

def get_param_value(elem, name):
    param = elem.LookupParameter(name)
    if not param:
        for p in elem.Parameters:
            if p.Definition.Name.strip() == name.strip():
                param = p
                break
    if param:
        if param.StorageType == DB.StorageType.Double:
            return param.AsDouble()
        elif param.StorageType == DB.StorageType.Integer:
            return param.AsInteger()
        elif param.StorageType == DB.StorageType.String:
            return param.AsString()
    return None

if pbp:
    ew_raw = get_param_value(pbp, "E/W") or 0.0
    ns_raw = get_param_value(pbp, "N/S") or 0.0
    elev_raw = get_param_value(pbp, "Elev") or 0.0
    pbp_e_ft = m_to_feet(feet_to_m(ew_raw))
    pbp_n_ft = m_to_feet(feet_to_m(ns_raw))
    pbp_z_ft = m_to_feet(feet_to_m(elev_raw))
else:
    output.print_md("Warning: Project Base Point not found. Using 0,0,0 offsets.")

# --------------------------------------------------
# Place Family Instances
# --------------------------------------------------
t = DB.Transaction(doc, "Place Structural Foundations")
t.Start()

placed_elements = []

for row in rows:
    file_name = row["File"]
    os_grid = row["OS Grid (10)"]
    try:
        altitude_m = float(row.get("Altitude (m)") or 0.0)
    except:
        altitude_m = 0.0

    easting, northing = os_grid_to_en(os_grid)
    if easting is None or northing is None:
        output.print_md("Skipping {}: Invalid OS Grid {}".format(file_name, os_grid))
        continue

    # Convert CSV coordinates (meters) to Revit feet, subtract PBP offsets
    x_ft = m_to_feet(easting) - pbp_e_ft
    y_ft = m_to_feet(northing) - pbp_n_ft
    z_ft = m_to_feet(altitude_m) - pbp_z_ft

    point = DB.XYZ(x_ft, y_ft, z_ft)

    # Place the family instance
    instance = doc.Create.NewFamilyInstance(
        point,
        family_symbol,
        DB.Structure.StructuralType.NonStructural
    )

    # Set mark/filename
    set_param_value(instance, "Mark", file_name)

    placed_elements.append((file_name, os_grid, altitude_m))

t.Commit()

# --------------------------------------------------
# Output summary
# --------------------------------------------------
if placed_elements:
    output.print_md("### Placed Structural Foundation Instances")
    for f, osr, alt in placed_elements:
        output.print_md("- **{}** at OS Grid {} with elevation {:.2f} m".format(f, osr, alt))
else:
    output.print_md("No family instances were placed.")
