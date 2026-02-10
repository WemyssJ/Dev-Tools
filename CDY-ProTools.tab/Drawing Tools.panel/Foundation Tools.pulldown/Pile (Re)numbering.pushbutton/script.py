# -*- coding: utf-8 -*-
import clr, os
clr.AddReference('RevitAPI')
clr.AddReference('RevitServices')
clr.AddReference('PresentationFramework')
clr.AddReference('PresentationCore')
clr.AddReference('WindowsBase')

from Autodesk.Revit.DB import *
from RevitServices.Persistence import DocumentManager
from System.Windows import Window
from System.Windows.Markup import XamlReader
from pyrevit import revit, script, forms
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption
from System import Uri
from collections import defaultdict

##############################################################################################
# TELEMETRY IMPORTS #
##############################################################################################
import os, sys

lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'lib'))
if lib_path not in sys.path:
    sys.path.append(lib_path)

import telemetry_auto

tool_name = os.path.basename(os.path.dirname(__file__)) 
TOOL_NAME = tool_name.replace(".pushbutton", "")
telemetry_auto.log_tool_usage(TOOL_NAME)
##############################################################################################

doc = revit.doc
uidoc = revit.uidoc
output = script.get_output()

# ---------------------------------------------------------------
# Load external XAML layout
# ---------------------------------------------------------------
xaml_path = script.get_bundle_file('NumberPiles.xaml')
with open(xaml_path, 'r') as f:
    xaml_str = f.read()
window = XamlReader.Parse(xaml_str)

icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
if not os.path.exists(icon_path):
    print("⚠️ icon.png not found in script folder.")

bmp = BitmapImage()
bmp.BeginInit()
bmp.UriSource = Uri(icon_path)
bmp.CacheOption = BitmapCacheOption.OnLoad
bmp.EndInit()
window.FindName("headerIcon").Source = bmp

# ---------------------------------------------------------------
# Get control references by name
# ---------------------------------------------------------------
prefix_box = window.FindName("prefixBox")
pad_box = window.FindName("padBox")
start_box = window.FindName("startBox")   # >>> START NUMBER ADDITION
cat_combo = window.FindName("catCombo")
method_combo = window.FindName("methodCombo")
ok_btn = window.FindName("okBtn")
cancel_btn = window.FindName("cancelBtn")

# ---------------------------------------------------------------
# Collect all Structural Foundations
# ---------------------------------------------------------------
collector = FilteredElementCollector(doc) \
    .OfCategory(BuiltInCategory.OST_StructuralFoundation) \
    .WhereElementIsNotElementType()

piles = []
pile_categories = set()

new_construction_phase = None
for ph in FilteredElementCollector(doc).OfClass(Phase):
    if ph.Name.lower() == "new construction":
        new_construction_phase = ph
        break

if not new_construction_phase:
    forms.alert("No 'New Construction' phase found in this model.")
    script.exit()

new_phase_id = new_construction_phase.Id

for el in collector:
    try:
        element_name = el.Name
    except AttributeError:
        element_name = ""
    if element_name and element_name.lower() == "pile":
        loc = el.Location
        if isinstance(loc, LocationPoint):
            phase_param = el.get_Parameter(BuiltInParameter.PHASE_CREATED)
            if phase_param and phase_param.AsElementId() == new_phase_id:
                piles.append(el)
                param = el.LookupParameter("Pile Category")
                if param and param.HasValue:
                    pile_categories.add(param.AsString())

sorted_categories = sorted([c for c in pile_categories if c])
sorted_categories.insert(0, "All")

if not piles:
    forms.alert("No New Construction pile foundations found.")
    script.exit()

# ---------------------------------------------------------------
# Populate combo boxes
# ---------------------------------------------------------------
for cat in sorted_categories:
    cat_combo.Items.Add(cat)
cat_combo.SelectedIndex = 0

# ---------------------------------------------------------------
# Capture form data
# ---------------------------------------------------------------
form_data = {
    "prefix": None,
    "padding": None,
    "start": None,        # >>> START NUMBER ADDITION
    "category": None,
    "method": None
}

def on_ok(sender, args):
    try:
        form_data["prefix"] = prefix_box.Text.strip()
        form_data["padding"] = int(pad_box.Text.strip())
        form_data["start"] = int(start_box.Text.strip())  # >>> START NUMBER ADDITION
        form_data["category"] = cat_combo.SelectedItem
        selected_item = method_combo.SelectedItem
        form_data["method"] = selected_item.Content if hasattr(selected_item, "Content") else selected_item
        window.Close()
    except:
        forms.alert("Padding and Start Number must be integers.")

def on_cancel(sender, args):
    window.Close()
    script.exit("User cancelled.")

ok_btn.Click += on_ok
cancel_btn.Click += on_cancel

window.ShowDialog()

if not form_data["prefix"] or not form_data["padding"] or form_data["start"] < 1:
    script.exit("Cancelled or invalid input.")

prefix = form_data["prefix"]
padding = form_data["padding"]
start_number = form_data["start"]      # >>> START NUMBER ADDITION
selected_category = form_data["category"]
method = form_data["method"]

# ---------------------------------------------------------------
# Filter piles by category (case-insensitive)
# ---------------------------------------------------------------
filtered_piles = []
for el in piles:
    param = el.LookupParameter("Pile Category")
    val = param.AsString() if param and param.HasValue else ""
    if selected_category.lower() == "all" or val.strip().lower() == selected_category.strip().lower():
        filtered_piles.append(el)

if not filtered_piles:
    forms.alert("No piles found for selected category '{0}'.".format(selected_category))
    script.exit()

# ---------------------------------------------------------------
# Collect pile caps
# ---------------------------------------------------------------
pile_caps = []
for el in collector:
    type_id = el.GetTypeId()
    elem_type = doc.GetElement(type_id) if type_id else None
    desc_param = elem_type.LookupParameter("Description") if elem_type else None
    if desc_param and desc_param.AsString() == "Pile Cap":
        pile_caps.append(el)

# ---------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------
def get_point(el):
    loc = el.Location
    if isinstance(loc, LocationPoint):
        pt = loc.Point
        return XYZ(pt.X, pt.Y, 0)
    bb = el.get_BoundingBox(None)
    if bb:
        return XYZ((bb.Min.X + bb.Max.X) / 2, (bb.Min.Y + bb.Max.Y) / 2, 0)
    return XYZ(0, 0, 0)

def get_view_point(el):
    pt = get_point(el)
    view = uidoc.ActiveView
    try:
        inv = view.CropBox.Transform.Inverse
        relpt = inv.OfPoint(pt)
        return XYZ(relpt.X, relpt.Y, 0)
    except:
        return pt

def pile_sort_key(el):
    pt = get_point(el) if method == "By World Co-ordinates" else get_view_point(el)
    return (-round(pt.Y, 3), round(pt.X, 3), el.Id.IntegerValue)

def bbox_intersects(pile, cap, tolerance=0.1):
    pile_bb = pile.get_BoundingBox(None)
    cap_bb = cap.get_BoundingBox(None)
    if not pile_bb or not cap_bb:
        return False
    return (
        pile_bb.Max.X + tolerance >= cap_bb.Min.X and
        pile_bb.Min.X - tolerance <= cap_bb.Max.X and
        pile_bb.Max.Y + tolerance >= cap_bb.Min.Y and
        pile_bb.Min.Y - tolerance <= cap_bb.Max.Y
    )

# ---------------------------------------------------------------
# Map piles to caps
# ---------------------------------------------------------------
pile_to_cap = {}
for pile in filtered_piles:
    mark_param = pile.LookupParameter("Mark")
    pile_name = mark_param.AsString() if mark_param else str(pile.Id)
    matched = False
    for cap in pile_caps:
        if bbox_intersects(pile, cap):
            output.print_md("Pile '{0}' intersects with Cap ID '{1}'".format(pile_name, cap.Id))
            pile_to_cap[pile.Id] = cap.Id
            matched = True
            break
    if not matched:
        output.print_md("Pile '{0}' did **not** match any cap.".format(pile_name))

# ---------------------------------------------------------------
# Sort and group piles
# ---------------------------------------------------------------
pile_caps_sorted = sorted(pile_caps, key=pile_sort_key)
cap_to_piles = defaultdict(list)
unassociated_piles = []

for pile in filtered_piles:
    cap_id = pile_to_cap.get(pile.Id)
    if cap_id:
        cap_to_piles[cap_id].append(pile)
    else:
        unassociated_piles.append(pile)

for piles_list in cap_to_piles.values():
    piles_list.sort(key=pile_sort_key)

unassociated_piles.sort(key=pile_sort_key)

between_groups = defaultdict(list)
cap_ys = [get_point(cap).Y for cap in pile_caps_sorted]

for pile in unassociated_piles:
    p_y = get_point(pile).Y
    for i in range(len(cap_ys) - 1):
        if cap_ys[i + 1] <= p_y <= cap_ys[i]:
            between_groups[i].append(pile)
            break

top_unassociated = []
bottom_unassociated = []

highest_cap_y = cap_ys[0] if cap_ys else None
lowest_cap_y = cap_ys[-1] if cap_ys else None

for pile in unassociated_piles:
    p_y = get_point(pile).Y
    if any(pile in lst for lst in between_groups.values()):
        continue
    if highest_cap_y is not None and p_y > highest_cap_y:
        top_unassociated.append(pile)
    elif lowest_cap_y is not None and p_y < lowest_cap_y:
        bottom_unassociated.append(pile)

leftover_unassociated = []
for pile in unassociated_piles:
    if pile not in top_unassociated and pile not in bottom_unassociated and not any(pile in lst for lst in between_groups.values()):
        leftover_unassociated.append(pile)
        output.print_md("Leftover pile ID {0}, numbering anyway.".format(pile.Id))

for grp in between_groups.values():
    grp.sort(key=pile_sort_key)

top_unassociated.sort(key=pile_sort_key)
bottom_unassociated.sort(key=pile_sort_key)
leftover_unassociated.sort(key=pile_sort_key)

# ---------------------------------------------------------------
# Number piles transaction
# ---------------------------------------------------------------
output.print_md("Starting transaction...")
t = Transaction(doc, "Number piles with cap awareness")
t.Start()

try:
    i = start_number    # >>> START NUMBER ADDITION

    for pile in top_unassociated:
        mark = prefix + str(i).zfill(padding)
        param = pile.LookupParameter("Mark")
        if param and not param.IsReadOnly:
            param.Set(mark)
        output.print_md("Numbered pile ID {0} as '{1}'".format(pile.Id, mark))
        i += 1

    for idx, cap in enumerate(pile_caps_sorted):
        for pile in cap_to_piles.get(cap.Id, []):
            mark = prefix + str(i).zfill(padding)
            param = pile.LookupParameter("Mark")
            if param and not param.IsReadOnly:
                param.Set(mark)
            output.print_md("Numbered pile ID {0} as '{1}'".format(pile.Id, mark))
            i += 1
        for pile in between_groups.get(idx, []):
            mark = prefix + str(i).zfill(padding)
            param = pile.LookupParameter("Mark")
            if param and not param.IsReadOnly:
                param.Set(mark)
            output.print_md("Numbered pile ID {0} as '{1}'".format(pile.Id, mark))
            i += 1

    for pile in bottom_unassociated + leftover_unassociated:
        mark = prefix + str(i).zfill(padding)
        param = pile.LookupParameter("Mark")
        if param and not param.IsReadOnly:
            param.Set(mark)
        output.print_md("Numbered pile ID {0} as '{1}'".format(pile.Id, mark))
        i += 1

except Exception as e:
    forms.alert("Error numbering piles: {0}".format(e))
finally:
    if t.HasStarted() and not t.HasEnded():
        t.Commit()
    output.print_md("Transaction committed.")

total_numbered = i - start_number   # >>> START NUMBER ADDITION
forms.alert("Successfully numbered {0} pile(s).".format(total_numbered), title="Success")
