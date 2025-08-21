# -*- coding: utf-8 -*-
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
from pyrevit import revit
import clr

clr.AddReference('PresentationFramework')
clr.AddReference('PresentationCore')
clr.AddReference('WindowsBase')
clr.AddReference('System.Xaml')

from System.Windows import Window
from System.Windows.Controls import ComboBox, TextBox, Button, StackPanel, Label
from System import Windows

doc = revit.doc
uidoc = revit.uidoc


# ---------------------------
# Wrapper for category list items
# ---------------------------
class CategoryItem:
    def __init__(self, name, catid):
        self.Name = name
        self.Id = catid
    def __str__(self):
        return self.Name


# ---------------------------
# Selection filter for category
# ---------------------------
class CategorySelectionFilter(ISelectionFilter):
    def __init__(self, category_id):
        self.category_id = category_id
    def AllowElement(self, element):
        return element.Category and element.Category.Id == self.category_id
    def AllowReference(self, reference, position):
        return True


# ---------------------------
# Main UI Window
# ---------------------------
class NumberingWindow(Window):
    def __init__(self):
        self.Title = "Element Renumbering"
        self.Width = 300
        self.Height = 200
        self.WindowStartupLocation = Windows.WindowStartupLocation.CenterScreen

        panel = StackPanel()

        # Dropdown
        panel.Children.Add(Label(Content="Type of Element:"))
        self.categoryBox = ComboBox()
        for cat in self.get_model_categories():
            self.categoryBox.Items.Add(cat)
        self.categoryBox.SelectedIndex = 0
        panel.Children.Add(self.categoryBox)

        # Prefix
        panel.Children.Add(Label(Content="Naming Prefix:"))
        self.prefixBox = TextBox(Text="Pad")
        panel.Children.Add(self.prefixBox)

        # Padding
        panel.Children.Add(Label(Content="Number Padding:"))
        self.paddingBox = TextBox(Text="3")
        panel.Children.Add(self.paddingBox)

        # Start button
        self.startButton = Button(Content="Start Numbering")
        self.startButton.Click += self.start_numbering
        panel.Children.Add(self.startButton)

        self.Content = panel

    def get_model_categories(self):
        """Return sorted list of CategoryItem objects for categories in model."""
        cats = {}
        for e in FilteredElementCollector(doc).WhereElementIsNotElementType():
            if e.Category and e.Category.Name:
                cats[e.Category.Id] = e.Category.Name
        items = [CategoryItem(name, cid) for cid, name in cats.items()]
        return sorted(items, key=lambda x: x.Name)

    def start_numbering(self, sender, args):
        try:
            self.selected_cat_item = self.categoryBox.SelectedItem
            self.prefix = self.prefixBox.Text
            self.padding = int(self.paddingBox.Text)
            self.Close()
            self.number_elements_live()
        except Exception as e:
            print("Error:", e)

    def number_elements_live(self):
        filter_cat = CategorySelectionFilter(self.selected_cat_item.Id)

        counter = 1
        while True:
            try:
                ref = uidoc.Selection.PickObject(ObjectType.Element, filter_cat,
                                                 "Select element or press ESC to finish")
                el = doc.GetElement(ref.ElementId)

                new_mark = "{}{}".format(self.prefix, str(counter).zfill(self.padding))
                t = Transaction(doc, "Set Mark")
                t.Start()
                el.LookupParameter("Mark").Set(new_mark)
                t.Commit()

                print("Set {} to {}".format(el.Id, new_mark))
                counter += 1

            except:
                break  # ESC pressed


# ---------------------------
# Run UI
# ---------------------------
win = NumberingWindow()
win.ShowDialog()
