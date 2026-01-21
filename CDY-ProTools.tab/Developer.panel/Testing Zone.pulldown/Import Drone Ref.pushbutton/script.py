# -*- coding: utf-8 -*-
import csv
import math
import urllib  # IronPython compatible

from pyrevit import forms, script, revit
from Autodesk.Revit import DB
from System.Windows import Window, Application, Thickness
from System.Windows.Controls import ComboBox, Button, StackPanel, TextBlock
from System.Collections.Generic import List

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

def os_grid_to_en(grid_ref):
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

    return (
        e100km * 100000 + e_remainder,
        n100km * 100000 + n_remainder
    )

# --------------------------------------------------
# Read CSV
# --------------------------------------------------
with open(csv_file_path) as csvfile:
    reader = csv.DictReader(csvfile)
    rows = list(reader)

required_headers = ["File", "OS Grid (10)", "Altitude (m)", "Public Sharepoint Link"]
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
struct_families = []
for f in DB.FilteredElementCollector(doc).OfClass(DB.Family):
    try:
        if f.FamilyCategory and f.FamilyCategory.Id.IntegerValue == int(DB.BuiltInCategory.OST_StructuralFoundation):
            struct_families.append(f)
    except:
        continue

if not struct_families:
    output.print_md("No Structural Foundation families found.")
    script.exit()

family_names = [f.Name for f in struct_families]

# --------------------------------------------------
# WPF Dropdown
# --------------------------------------------------
class DropdownWindow(Window):
    def __init__(self, options):
        self.SelectedFamily = None
        self.Title = "Select Structural Foundation Family"
        self.Width = 400
        self.Height = 150

        panel = StackPanel(Margin=Thickness(10))
        panel.Children.Add(TextBlock(Text="Select a Structural Foundation Family:"))

        self.combo = ComboBox()
        self.combo.ItemsSource = List[str](options)
        self.combo.SelectedIndex = 0
        panel.Children.Add(self.combo)

        btn = Button(Content="OK", Width=80, Margin=Thickness(0,10,0,0))
        btn.Click += self.on_ok
        panel.Children.Add(btn)

        self.Content = panel

    def on_ok(self, sender, e):
        self.SelectedFamily = struct_families[self.combo.SelectedIndex]
        self.Close()

win = DropdownWindow(family_names)
app = Application.Current or Application()
win.ShowDialog()

selected_family = win.SelectedFamily
if not selected_family:
    script.exit()

# --------------------------------------------------
# Family Symbol
# --------------------------------------------------
symbols = [
    s for s in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol)
    if s.Family.Id == selected_family.Id
]

if not symbols:
    output.print_md("Selected family has no types.")
    script.exit()

family_symbol = symbols[0]
if not family_symbol.IsActive:
    family_symbol.Activate()
    doc.Regenerate()

# --------------------------------------------------
# Project Base Point
# --------------------------------------------------
pbp = next((bp for bp in DB.FilteredElementCollector(doc).OfClass(DB.BasePoint) if not bp.IsShared), None)

pbp_e_ft = m_to_feet(feet_to_m(get_param_value(pbp, "E/W") or 0.0))
pbp_n_ft = m_to_feet(feet_to_m(get_param_value(pbp, "N/S") or 0.0))
pbp_z_ft = m_to_feet(feet_to_m(get_param_value(pbp, "Elev") or 0.0))

# --------------------------------------------------
# Place Family Instances
# --------------------------------------------------
t = DB.Transaction(doc, "Place Structural Foundations")
t.Start()

placed = []

for row in rows:
    file_name = row["File"]
    os_grid = row["OS Grid (10)"]
    altitude_m = float(row.get("Altitude (m)") or 0.0)

    e, n = os_grid_to_en(os_grid)
    if e is None:
        continue

    x = m_to_feet(e) - pbp_e_ft
    y = m_to_feet(n) - pbp_n_ft
    z = m_to_feet(altitude_m) - pbp_z_ft

    inst = doc.Create.NewFamilyInstance(
        DB.XYZ(x, y, z),
        family_symbol,
        DB.Structure.StructuralType.NonStructural
    )

    # Set DroneRef
    set_param_value(inst, "DroneRef", file_name)

    # Set DroneURL from Public Sharepoint Link
    public_url = row.get("Public Sharepoint Link", "")
    if public_url:
        set_param_value(inst, "DroneURL", public_url)

    placed.append(file_name)

t.Commit()

# --------------------------------------------------
# Output
# --------------------------------------------------
output.print_md("### Placed {} Structural Foundation Instances".format(len(placed)))
