# -*- coding: utf-8 -*-
# Duplicate a line style with defaults from source line, using WPF form

import os
from Autodesk.Revit.DB import (
    Transaction,
    BuiltInCategory,
    Color,
    FilteredElementCollector,
    LinePatternElement,
    GraphicsStyle
)
from Autodesk.Revit.UI import TaskDialog
from pyrevit import forms

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument

# -------- WPF Form ----------
class InputForm(forms.WPFWindow):
    def __init__(self, xaml_file, defaults, patterns):
        forms.WPFWindow.__init__(self, xaml_file)

        # Fill defaults from source line
        self.NameBox.Text = defaults["name"] + " Copy"
        self.WeightBox.Text = str(defaults["weight"])
        self.ColourBox.Text = "{},{},{}".format(defaults["colour"].Red,
                                                defaults["colour"].Green,
                                                defaults["colour"].Blue)

        for p in patterns:
            self.PatternBox.Items.Add(p.Name)
        self.PatternBox.SelectedItem = defaults["pattern_name"]

        self.OkBtn.Click += self.ok_click
        self.CancelBtn.Click += self.cancel_click
        self.result = None

    def ok_click(self, sender, args):
        try:
            weight = int(self.WeightBox.Text)
        except:
            weight = 1
        try:
            r, g, b = [int(x.strip()) for x in self.ColourBox.Text.split(",")]
        except:
            r, g, b = (0, 0, 0)

        self.result = {
            "name": self.NameBox.Text,
            "weight": weight,
            "colour": Color(r, g, b),
            "pattern_name": self.PatternBox.SelectedItem
        }
        self.Close()

    def cancel_click(self, sender, args):
        self.result = None
        self.Close()

# -------- Helpers ----------
def pick_source_line():
    selection = uidoc.Selection.GetElementIds()
    if selection.Count > 0:
        return doc.GetElement(list(selection)[0])
    else:
        ref = uidoc.Selection.PickObject(
            Autodesk.Revit.UI.Selection.ObjectType.Element,
            "Select a line to duplicate its style")
        return doc.GetElement(ref.ElementId)


def get_line_style(element):
    gs = getattr(element, "LineStyle", None)
    if isinstance(gs, GraphicsStyle):
        return gs
    return None


def duplicate_line_style(inputs, patterns_dict, elements_to_update):
    # Lines category
    lines_cat = doc.Settings.Categories.get_Item(BuiltInCategory.OST_Lines)
    pattern = patterns_dict[inputs["pattern_name"]]

    t = Transaction(doc, "Duplicate Line Style")
    t.Start()

    # Create new subcategory safely in IronPython
    new_subcat = lines_cat.SubCategories.Create(inputs["name"])
    new_subcat.LineColor = inputs["colour"]
    new_subcat.SetLineWeight(inputs["weight"], 0)  # projection
    new_subcat.SetLinePatternId(pattern.Id, 0)      # projection

    # Apply new style to selected lines
    for el in elements_to_update:
        try:
            el.LineStyle = new_subcat
        except:
            pass  # ignore if element cannot set LineStyle

    t.Commit()
    TaskDialog.Show("Success", "Created and applied new line style: {}".format(inputs['name']))
    return new_subcat

# ---------------- MAIN -----------------
try:
    element = pick_source_line()
    gs = get_line_style(element)

    if not gs:
        forms.alert("Selected element does not have a line style. Use a model or detail line.")
    else:
        cat = gs.GraphicsStyleCategory
        lines_cat = doc.Settings.Categories.get_Item(BuiltInCategory.OST_Lines)

        if not cat.Parent or cat.Parent.Id != lines_cat.Id:
            forms.alert("The selected line uses a style that cannot be duplicated (not a Lines subcategory).")
        else:
            # Defaults from source line
            try:
                weight = cat.GetLineWeight(0)
            except:
                weight = 1
            try:
                pattern_name = doc.GetElement(cat.GetLinePatternId(0)).Name
            except:
                pattern_name = ""

            defaults = {
                "name": cat.Name,
                "weight": weight,
                "colour": cat.LineColor,
                "pattern_name": pattern_name
            }

            # Collect line patterns
            patterns = list(FilteredElementCollector(doc).OfClass(LinePatternElement))
            patterns_dict = {p.Name: p for p in patterns}

            # XAML path
            xaml_file = os.path.join(os.path.dirname(__file__), "DuplicateLineStyle.xaml")

            # Show form
            form = InputForm(xaml_file, defaults, patterns)
            form.ShowDialog()

            if form.result:
                # Apply to all selected lines
                selected_elements = [doc.GetElement(i) for i in uidoc.Selection.GetElementIds()]
                duplicate_line_style(form.result, patterns_dict, selected_elements)

except Exception as e:
    import traceback
    forms.alert("Failed: {}".format(e))
    print(traceback.format_exc())
