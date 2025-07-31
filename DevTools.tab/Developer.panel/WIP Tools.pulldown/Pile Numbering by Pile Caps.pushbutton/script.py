import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitServices')
clr.AddReference('PresentationFramework')

from Autodesk.Revit.DB import *
from RevitServices.Persistence import DocumentManager
from System.Windows import Window, Thickness, HorizontalAlignment
from System.Windows.Controls import StackPanel, TextBlock, TextBox, Button, ComboBox
from pyrevit import revit, script, forms
from collections import defaultdict

doc = revit.doc
output = script.get_output()

# Collect all Structural Foundations
collector = FilteredElementCollector(doc) \
    .OfCategory(BuiltInCategory.OST_StructuralFoundation) \
    .WhereElementIsNotElementType()

piles = []
pile_categories = set()

for el in collector:
    try:
        element_name = el.Name
    except AttributeError:
        element_name = ""
    if element_name and element_name.lower() == "pile":
        loc = el.Location
        if isinstance(loc, LocationPoint):
            piles.append(el)
            param = el.LookupParameter("Pile Category")
            if param and param.HasValue:
                pile_categories.add(param.AsString())

sorted_categories = sorted([c for c in pile_categories if c])
sorted_categories.insert(0, "All")

if not piles:
    forms.alert("No Pile foundations found.")
    script.exit()

# --- UI window class ---
class InputWindow(Window):
    def __init__(self, categories):
        self.Title = "Number Piles"
        self.Height = 230
        self.Width = 300

        self.stack = StackPanel()
        self.stack.Margin = Thickness(10)

        self.prefix_label = TextBlock()
        self.prefix_label.Text = "Prefix (e.g. P):"
        self.stack.Children.Add(self.prefix_label)

        self.prefix_box = TextBox()
        self.prefix_box.Text = "P"
        self.stack.Children.Add(self.prefix_box)

        self.pad_label = TextBlock()
        self.pad_label.Text = "Padding (e.g. 3 for 001):"
        self.stack.Children.Add(self.pad_label)

        self.pad_box = TextBox()
        self.pad_box.Text = "3"
        self.stack.Children.Add(self.pad_box)

        self.cat_label = TextBlock()
        self.cat_label.Text = "Pile Category:"
        self.stack.Children.Add(self.cat_label)

        self.cat_combo = ComboBox()
        self.cat_combo.Width = 260
        for cat in categories:
            self.cat_combo.Items.Add(cat)
        self.cat_combo.SelectedIndex = 0
        self.stack.Children.Add(self.cat_combo)

        self.ok_button = Button()
        self.ok_button.Content = "OK"
        self.ok_button.Width = 60
        self.ok_button.HorizontalAlignment = HorizontalAlignment.Right
        self.ok_button.Click += self.on_ok
        self.stack.Children.Add(self.ok_button)

        self.Content = self.stack

        self.prefix = None
        self.padding = None
        self.category = None

    def on_ok(self, sender, args):
        try:
            self.prefix = self.prefix_box.Text.strip()
            self.padding = int(self.pad_box.Text.strip())
            self.category = self.cat_combo.SelectedItem
            self.Close()
        except:
            forms.alert("Padding must be an integer.")

form = InputWindow(sorted_categories)
form.ShowDialog()

if not form.prefix or not form.padding:
    script.exit("Cancelled or invalid input.")

prefix = form.prefix
padding = form.padding
selected_category = form.category

# Filter piles by category
filtered_piles = []
for el in piles:
    if selected_category == "All":
        filtered_piles.append(el)
    else:
        param = el.LookupParameter("Pile Category")
        val = param.AsString() if param and param.HasValue else None
        if val == selected_category:
            filtered_piles.append(el)

if not filtered_piles:
    forms.alert("No piles found for selected category '{0}'.".format(selected_category))
    script.exit()

# Collect pile caps by Description = "Pile Cap" (type parameter)
pile_caps = []
for el in collector:
    type_id = el.GetTypeId()
    elem_type = doc.GetElement(type_id) if type_id else None
    desc_param = elem_type.LookupParameter("Description") if elem_type else None
    if desc_param and desc_param.AsString() == "Pile Cap":
        pile_caps.append(el)

# Get XYZ location
def get_point(el):
    """Returns the X/Y point of an element, ignoring Z."""
    loc = el.Location
    if isinstance(loc, LocationPoint):
        pt = loc.Point
        return XYZ(pt.X, pt.Y, 0)  # Force Z = 0
    else:
        # Try to approximate from bounding box if no LocationPoint
        bb = el.get_BoundingBox(None)
        if bb:
            center_x = (bb.Min.X + bb.Max.X) / 2
            center_y = (bb.Min.Y + bb.Max.Y) / 2
            return XYZ(center_x, center_y, 0)  # Force Z = 0
    return XYZ(0, 0, 0)


# Bounding box intersection (Z ignored)
def bbox_intersects(pile, cap, tolerance=0.05):  # ~15mm tolerance
    pile_bb = pile.get_BoundingBox(None)
    cap_bb = cap.get_BoundingBox(None)
    if not pile_bb or not cap_bb:
        return False
    return (
        (pile_bb.Max.X + tolerance >= cap_bb.Min.X and pile_bb.Min.X - tolerance <= cap_bb.Max.X) and
        (pile_bb.Max.Y + tolerance >= cap_bb.Min.Y and pile_bb.Min.Y - tolerance <= cap_bb.Max.Y)
        # Z axis ignored
    )

# Map pile to cap using bounding box overlap
pile_to_cap = {}
for pile in filtered_piles:
    mark_param = pile.LookupParameter("Mark")
    if mark_param:
        pile_name = mark_param.AsString()
    else:
        pile_name = str(pile.Id)
    matched = False
    for cap in pile_caps:
        if bbox_intersects(pile, cap):
            output.print_md("Pile '{0}' intersects with Cap ID '{1}'".format(pile_name, cap.Id))
            pile_to_cap[pile.Id] = cap.Id
            matched = True
            break
    if not matched:
        output.print_md("Pile '{0}' did **not** match any cap.".format(pile_name))

# Sort pile caps by Y descending, X ascending
pile_caps_sorted = sorted(pile_caps, key=lambda cap: (-get_point(cap).Y, get_point(cap).X))

# Group piles by their cap ID
cap_to_piles = defaultdict(list)
unassociated_piles = []

for pile in filtered_piles:
    cap_id = pile_to_cap.get(pile.Id, None)
    if cap_id is not None:
        cap_to_piles[cap_id].append(pile)
    else:
        unassociated_piles.append(pile)

# Sort piles within each cap top-left to top-right (Y desc, X asc)
for cap_id, piles_list in cap_to_piles.items():
    piles_list.sort(key=lambda p: (-get_point(p).Y, get_point(p).X))

# Sort unassociated piles similarly
unassociated_piles.sort(key=lambda p: (-get_point(p).Y, get_point(p).X))

# Group unassociated piles between caps by Y position
between_groups = defaultdict(list)  # key = cap index, value = list of piles

cap_ys = [get_point(cap).Y for cap in pile_caps_sorted]

for pile in unassociated_piles:
    p_y = get_point(pile).Y
    assigned = False
    for i in range(len(cap_ys) - 1):
        upper_y = cap_ys[i]      # higher Y
        lower_y = cap_ys[i + 1]  # lower Y
        if lower_y <= p_y <= upper_y:
            between_groups[i].append(pile)
            assigned = True
            break
    if not assigned:
        pass  # handled below

# Separate unassociated piles outside cap Y ranges into top and bottom groups
top_unassociated = []
bottom_unassociated = []

highest_cap_y = cap_ys[0] if cap_ys else None
lowest_cap_y = cap_ys[-1] if cap_ys else None

for pile in unassociated_piles:
    p_y = get_point(pile).Y
    # Skip piles already assigned to between_groups
    in_between = False
    for piles_list in between_groups.values():
        if pile in piles_list:
            in_between = True
            break
    if in_between:
        continue
    if highest_cap_y is not None and p_y > highest_cap_y:
        top_unassociated.append(pile)
    elif lowest_cap_y is not None and p_y < lowest_cap_y:
        bottom_unassociated.append(pile)
    else:
        output.print_md("Pile ID {0} outside expected Y ranges, skipping numbering.".format(pile.Id))

# Sort piles in each between group by Y desc, X asc
for key in between_groups:
    between_groups[key].sort(key=lambda p: (-get_point(p).Y, get_point(p).X))

# Sort top and bottom unassociated piles by Y desc, X asc
top_unassociated.sort(key=lambda p: (-get_point(p).Y, get_point(p).X))
bottom_unassociated.sort(key=lambda p: (-get_point(p).Y, get_point(p).X))

# Start transaction and number piles
output.print_md("Starting transaction...")
t = Transaction(doc, "Number piles with cap awareness")
t.Start()

try:
    i = 1

    # Number unassociated piles above highest cap first (top_unassociated)
    for pile in top_unassociated:
        mark = prefix + str(i).zfill(padding)
        param = pile.LookupParameter("Mark")
        if param and not param.IsReadOnly:
            param.Set(mark)
        else:
            output.print_md("Could not set Mark on Pile ID {0}".format(pile.Id))
        i += 1

    num_caps = len(pile_caps_sorted)
    for idx, cap in enumerate(pile_caps_sorted):
        cap_id = cap.Id
        # Number piles under this cap
        piles_list = cap_to_piles.get(cap_id, [])
        for pile in piles_list:
            mark = prefix + str(i).zfill(padding)
            param = pile.LookupParameter("Mark")
            if param and not param.IsReadOnly:
                param.Set(mark)
            else:
                output.print_md("Could not set Mark on Pile ID {0}".format(pile.Id))
            i += 1

        # Number piles between this cap and the next cap, if not last cap
        if idx < num_caps - 1:
            between_piles = between_groups.get(idx, [])
            for pile in between_piles:
                mark = prefix + str(i).zfill(padding)
                param = pile.LookupParameter("Mark")
                if param and not param.IsReadOnly:
                    param.Set(mark)
                else:
                    output.print_md("Could not set Mark on Pile ID {0}".format(pile.Id))
                i += 1

    # Number unassociated piles below lowest cap last (bottom_unassociated)
    for pile in bottom_unassociated:
        mark = prefix + str(i).zfill(padding)
        param = pile.LookupParameter("Mark")
        if param and not param.IsReadOnly:
            param.Set(mark)
        else:
            output.print_md("Could not set Mark on Pile ID {0}".format(pile.Id))
        i += 1

except Exception as e:
    forms.alert("Error numbering piles: {0}".format(e))
finally:
    if t.HasStarted() and not t.HasEnded():
        t.Commit()
    output.print_md("Transaction committed.")

total_numbered = i - 1
forms.alert("Successfully numbered {0} pile(s).".format(total_numbered), title="Success")
