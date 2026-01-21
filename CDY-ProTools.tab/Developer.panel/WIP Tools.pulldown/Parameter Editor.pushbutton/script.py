# -*- coding: utf-8 -*-
from Autodesk.Revit.DB import Transaction
from Autodesk.Revit.UI import TaskDialog
from pyrevit.forms import WPFWindow
import os

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

# Path to your XAML
xaml_path = os.path.join(os.path.dirname(__file__), 'ParamDialogWithDropdown.xaml')


class ParamDialog(WPFWindow):
    def __init__(self, xaml_file, param_names, writable_params, initial_value):
        WPFWindow.__init__(self, xaml_file)

        self.writable_params = writable_params
        self.param_names = param_names
        self.result = None

        # Populate dropdown
        self.cmbParameters.ItemsSource = param_names
        if param_names:
            self.cmbParameters.SelectedIndex = 0

        # Initialize textbox
        self.txtParameterValue.Text = initial_value or ""

        # Event bindings
        self.btnOk.Click += self.ok_clicked
        self.btnCancel.Click += self.cancel_clicked
        self.cmbParameters.SelectionChanged += self.param_changed

    def param_changed(self, sender, e):
        """Update textbox when dropdown selection changes."""
        selected_param = self.cmbParameters.SelectedItem
        if not selected_param:
            return

        # Get values from writable_params for this parameter
        values = []
        for p in self.writable_params:
            if p.Definition.Name == selected_param:
                values.append(p.AsString() or "")

        # Determine if values vary
        unique_values = list(dict.fromkeys(values))
        if len(unique_values) == 1:
            self.txtParameterValue.Text = unique_values[0]
        else:
            # Show all distinct values separated by newlines
            self.txtParameterValue.Text = "<Varies>\n" + "\n".join(unique_values)

    def ok_clicked(self, sender, e):
        self.result = True
        self.Close()

    def cancel_clicked(self, sender, e):
        self.result = False
        self.Close()


def main():
    uidoc = __revit__.ActiveUIDocument
    doc = uidoc.Document
    selection = uidoc.Selection.GetElementIds()

    if not selection:
        TaskDialog.Show("Error", "Please select one or more elements.")
        return

    elems = [doc.GetElement(eid) for eid in selection]

    # Ensure all elements are same category
    first_elem = elems[0]
    first_cat = first_elem.Category
    if any(e.Category.Id != first_cat.Id for e in elems):
        TaskDialog.Show("Error", "All selected elements must be of the same category/type.")
        return

    # Gather writable string parameters from the first element only
    writable_params = []
    for e in elems:
        for p in e.Parameters:
            if p.StorageType.ToString() == "String" and not p.IsReadOnly:
                writable_params.append(p)

    if not writable_params:
        TaskDialog.Show("Error", "No writable string parameters found.")
        return

    param_list = [
        p.Definition.Name for p in first_elem.Parameters
        if p.StorageType.ToString() == "String" and not p.IsReadOnly
    ]

    # Get initial value for first parameter
    initial_param_name = param_list[0]
    initial_values = []
    for e in elems:
        p = e.LookupParameter(initial_param_name)
        if p:
            initial_values.append(p.AsString() or "")

    # Determine initial textbox value
    unique_initial_values = list(dict.fromkeys(initial_values))
    if len(unique_initial_values) == 1:
        initial_text = unique_initial_values[0]
    else:
        initial_text = "<Varies>\n" + "\n".join(unique_initial_values)

    # Show dialog
    form = ParamDialog(xaml_path, param_list, writable_params, initial_text)
    form.ShowDialog()

    if not form.result:
        return

    # Get new text
    new_text = form.txtParameterValue.Text.strip()
    selected_param_name = form.cmbParameters.SelectedItem

    if not selected_param_name:
        TaskDialog.Show("Error", "No parameter selected.")
        return

    # Prevent saving if text contains <Varies>
    if "<Varies>" in new_text:
        TaskDialog.Show("Info", "No changes made (contains <Varies>).")
        return

    # Apply update in a single transaction for undo
    t = Transaction(doc, "Set '{}' Parameter on Multiple Elements".format(selected_param_name))
    t.Start()
    updated_count = 0
    for e in elems:
        p = e.LookupParameter(selected_param_name)
        if p and not p.IsReadOnly:
            p.Set(new_text)
            updated_count += 1
    t.Commit()

    TaskDialog.Show("Success", "'{}' updated on {} element(s).".format(selected_param_name, updated_count))


if __name__ == "__main__":
    main()
