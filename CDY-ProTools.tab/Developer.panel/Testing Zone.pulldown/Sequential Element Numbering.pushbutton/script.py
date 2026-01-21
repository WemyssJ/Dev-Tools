# -*- coding: utf-8 -*-
from pyrevit import revit, forms
from Autodesk.Revit.DB import FilteredElementCollector, Transaction
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
import clr, os

doc = revit.doc
uidoc = revit.uidoc

clr.AddReference('PresentationFramework')
clr.AddReference('PresentationCore')
clr.AddReference('WindowsBase')

from System.Windows import Window

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
# Load XAML UI
# ---------------------------
HERE = os.path.dirname(__file__)
XAMLFILE = os.path.join(HERE, "NumberElement.xaml")
dlg = forms.WPFWindow(XAMLFILE)

# Correct names from XAML
cat_combo = dlg.catCombo
prefix_box = dlg.prefixBox
padding_box = dlg.padBox
ok_btn = dlg.okBtn
cancel_btn = dlg.cancelBtn

# ---------------------------
# Populate ComboBox with model categories
# ---------------------------
def get_model_categories():
    cats = {}
    for e in FilteredElementCollector(doc).WhereElementIsNotElementType():
        if e.Category and e.Category.Name:
            cats[e.Category.Id] = e.Category.Name
    items = [CategoryItem(name, cid) for cid, name in cats.items()]
    return sorted(items, key=lambda x: x.Name)

for cat in get_model_categories():
    cat_combo.Items.Add(cat)
cat_combo.SelectedIndex = 0

# ---------------------------
# Start numbering logic
# ---------------------------
def start_numbering(sender, args):
    try:
        selected_cat_item = cat_combo.SelectedItem
        prefix = prefix_box.Text
        padding = int(padding_box.Text)
        dlg.Close()  # close dialog before selection
        number_elements(selected_cat_item, prefix, padding)
    except Exception as e:
        print("Error:", e)

ok_btn.Click += start_numbering
cancel_btn.Click += lambda s, a: dlg.Close()

# ---------------------------
# Function to number elements live
# ---------------------------
def number_elements(category_item, prefix, padding):
    filter_cat = CategorySelectionFilter(category_item.Id)
    counter = 1
    while True:
        try:
            ref = uidoc.Selection.PickObject(ObjectType.Element, filter_cat,
                                             "Select element or press ESC to finish")
            el = doc.GetElement(ref.ElementId)

            new_mark = "{}{}".format(prefix, str(counter).zfill(padding))
            t = Transaction(doc, "Set Mark")
            t.Start()
            param = el.LookupParameter("Mark")
            if param:
                param.Set(new_mark)
            t.Commit()

            print("Set {} to {}".format(el.Id, new_mark))
            counter += 1

        except:
            break  # ESC pressed

# ---------------------------
# Show UI
# ---------------------------
dlg.ShowDialog()
