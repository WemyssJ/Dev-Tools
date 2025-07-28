import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitServices')
clr.AddReference('PresentationFramework')

from Autodesk.Revit.DB import *
from RevitServices.Persistence import DocumentManager

from System.Windows import Window, Thickness, HorizontalAlignment
from System.Windows.Controls import StackPanel, TextBlock, TextBox, Button, ComboBox

from pyrevit import revit, script, forms

doc = revit.doc
output = script.get_output()

# Collect all piles and their "Pile Category" values
collector = FilteredElementCollector(doc)\
    .OfCategory(BuiltInCategory.OST_StructuralFoundation)\
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
            # Get Pile Category param value
            param = el.LookupParameter("Pile Category")
            if param and param.HasValue:
                pile_categories.add(param.AsString())

# Sort categories and add "All" option at the front
sorted_categories = sorted(c for c in pile_categories if c)
sorted_categories.insert(0, "All")

if not piles:
    forms.alert("No Pile foundations found.")
    script.exit()

# --- UI window class with dropdown ---
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
        self.cat_combo.SelectedIndex = 0  # default to "All"
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

# Filter piles by category if not "All"
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
    forms.alert("No piles found for selected category '{}'.".format(selected_category))
    script.exit()

# Sort by location Y descending, then X ascending
def get_point(el):
    loc = el.Location
    return loc.Point if isinstance(loc, LocationPoint) else XYZ(0,0,0)

filtered_piles.sort(key=lambda el: (-get_point(el).Y, get_point(el).X))

output.print_md("Starting transaction...")
t = Transaction(doc, "Number piles")
t.Start()
try:
    output.print_md("Inside transaction loop")
    for i, el in enumerate(filtered_piles, 1):
        mark = "{}{}".format(prefix, str(i).zfill(padding))
        param = el.LookupParameter("Mark")
        if param:
            if not param.IsReadOnly:
                try:
                    param.Set(mark)
                except Exception as inner_e:
                    forms.alert("Failed to set Mark parameter on element {}: {}".format(el.Id, inner_e))
            else:
                output.print_md("- Parameter 'Mark' is read-only on element {}".format(el.Id))
        else:
            output.print_md("- Element {} has no 'Mark' parameter".format(el.Id))
except Exception as e:
    forms.alert("Error numbering piles: {}".format(e))
finally:
    if t.HasStarted() and not t.HasEnded():
        t.Commit()
    output.print_md("Transaction committed.")

forms.alert("Successfully numbered {} pile(s).".format(len(filtered_piles)), title="Success")
