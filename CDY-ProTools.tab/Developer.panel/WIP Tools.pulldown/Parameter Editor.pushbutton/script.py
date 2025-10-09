# -*- coding: utf-8 -*-

from Autodesk.Revit.DB import Transaction, BuiltInParameter
from Autodesk.Revit.UI import TaskDialog
from pyrevit.forms import WPFWindow
import os

# Adjust path if needed to point to the XAML file location
xaml_path = os.path.join(os.path.dirname(__file__), 'ParamDialogWithDropdown.xaml')


class ParamDialog(WPFWindow):
    def __init__(self, xaml_file, param_names, writable_params, initial_value):
        WPFWindow.__init__(self, xaml_file)

        self.writable_params = writable_params

        # Populate dropdown with parameter names
        self.cmbParameters.ItemsSource = param_names
        if param_names:
            self.cmbParameters.SelectedIndex = 0  # default select first

        self.txtParameterValue.Text = initial_value or ""
        self.result = None

        self.btnOk.Click += self.ok_clicked
        self.btnCancel.Click += self.cancel_clicked

        # Update text box when dropdown selection changes
        self.cmbParameters.SelectionChanged += self.param_changed

    def param_changed(self, sender, e):
        selected_param_name = self.cmbParameters.SelectedItem
        if not selected_param_name:
            return

        # Find the corresponding parameter
        selected_param = next(
            (p for p in self.writable_params if p.Definition.Name == selected_param_name), None
        )

        if selected_param:
            current_value = selected_param.AsString() or ""
            self.txtParameterValue.Text = current_value
        else:
            self.txtParameterValue.Text = ""

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
    if len(selection) != 1:
        TaskDialog.Show("Error", "Please select exactly one element.")
        return

    elem = doc.GetElement(selection[0])

    # Gather all writable string parameters of the selected element
    param_list = []
    writable_params = []
    for param in elem.Parameters:
        if param.StorageType.ToString() == "String" and not param.IsReadOnly:
            param_list.append(param.Definition.Name)
            writable_params.append(param)

    if not param_list:
        TaskDialog.Show("Error", "No writable string parameters found on the selected element.")
        return

    # Default to first param value
    initial_value = writable_params[0].AsString() or ""

    form = ParamDialog(xaml_path, param_list, writable_params, initial_value)
    form.ShowDialog()

    if form.result:
        new_value = form.txtParameterValue.Text
        selected_param_name = form.cmbParameters.SelectedItem

        selected_param = next(
            (p for p in writable_params if p.Definition.Name == selected_param_name), None
        )

        if selected_param is None:
            TaskDialog.Show("Error", "Selected parameter not found.")
            return

        t = Transaction(doc, "Set '{}' Parameter".format(selected_param_name))
        t.Start()
        selected_param.Set(new_value)
        t.Commit()

        TaskDialog.Show("Success", "'{}' parameter updated.".format(selected_param_name))


if __name__ == "__main__":
    main()
