# -*- coding: utf-8 -*-
import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitServices')
clr.AddReference('PresentationFramework')

from Autodesk.Revit.DB import *
from RevitServices.Persistence import DocumentManager

from System.Windows import Window, Thickness, HorizontalAlignment
from System.Windows.Controls import StackPanel, TextBlock, TextBox, Button

from pyrevit import revit, script, forms

doc = revit.doc
output = script.get_output()

class InputWindow(Window):
    def __init__(self):
        self.Title = "Number Piles"
        self.Height = 180
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

        self.ok_button = Button()
        self.ok_button.Content = "OK"
        self.ok_button.Width = 60
        self.ok_button.HorizontalAlignment = HorizontalAlignment.Right
        self.ok_button.Click += self.on_ok
        self.stack.Children.Add(self.ok_button)

        self.Content = self.stack
        self.prefix = None
        self.padding = None

    def on_ok(self, sender, args):
        try:
            self.prefix = self.prefix_box.Text.strip()
            self.padding = int(self.pad_box.Text.strip())
            self.Close()
        except:
            forms.alert("Padding must be an integer.")

form = InputWindow()
form.ShowDialog()

if not form.prefix or not form.padding:
    script.exit("Cancelled or invalid input.")

prefix = form.prefix
padding = form.padding

collector = FilteredElementCollector(doc)\
    .OfCategory(BuiltInCategory.OST_StructuralFoundation)\
    .WhereElementIsNotElementType()

piles = []

output.print_md("### Found Structural Foundations:")
for el in collector:
    try:
        element_name = el.Name
    except AttributeError:
        element_name = ""

    output.print_md("- Element Id {}, Element Name: **{}**".format(el.Id, element_name))

    if element_name and element_name.lower() == "pile":
        loc = el.Location
        if isinstance(loc, LocationPoint):
            piles.append((el, loc.Point))

if not piles:
    forms.alert("No Pile foundations found.")
    script.exit()

piles.sort(key=lambda x: (-x[1].Y, x[1].X))

output.print_md("Starting transaction...")
t = Transaction(doc, "Number piles")
t.Start()
try:
    output.print_md("Inside transaction loop")
    for i, (el, pt) in enumerate(piles, 1):
        mark = "{}{}".format(prefix, str(i).zfill(padding))
        param = el.LookupParameter("Mark")
        if param:
            if not param.IsReadOnly:
                try:
                    param.Set(mark)
                except Exception, inner_e:
                    forms.alert("Failed to set Mark parameter on element {}: {}".format(el.Id, inner_e))
            else:
                output.print_md("- Parameter 'Mark' is read-only on element {}".format(el.Id))
        else:
            output.print_md("- Element {} has no 'Mark' parameter".format(el.Id))
except Exception, e:
    forms.alert("Error numbering piles: {}".format(e))
finally:
    if t.HasStarted() and not t.HasEnded():
        t.Commit()
    output.print_md("Transaction committed.")

forms.alert("Successfully numbered {} pile(s).".format(len(piles)), title="Success")
