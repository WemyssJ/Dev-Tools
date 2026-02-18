# -*- coding: utf-8 -*-
import os
import clr
from Autodesk.Revit.DB import *
from pyrevit import revit, forms, script

clr.AddReference("PresentationFramework")
clr.AddReference("PresentationCore")
clr.AddReference("WindowsBase")
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from System.Windows import Controls, Media

# ----------------------------------------------------------
# Revit & Application
# ----------------------------------------------------------
doc = revit.doc
app = __revit__.Application

# ----------------------------------------------------------
# Collect Open Family Documents
# ----------------------------------------------------------
open_family_docs = [d for d in app.Documents if d.IsFamilyDocument]
if len(open_family_docs) < 2:
    forms.alert("You must have at least TWO family documents open.")
    script.exit()

doc_dict = {d.Title: d for d in open_family_docs}

# ----------------------------------------------------------
# Load XAML
# ----------------------------------------------------------
script_dir = os.path.dirname(__file__)
xaml_path = os.path.join(script_dir, "TransferWindow.xaml")
if not os.path.exists(xaml_path):
    forms.alert("Could not find TransferWindow.xaml in script folder.", exitscript=True)

window = forms.WPFWindow(xaml_path)

# ----------------------------------------------------------
# Resolve named controls
# ----------------------------------------------------------
SourceListBox = window.FindName("SourceListBox")
TargetListBox = window.FindName("TargetListBox")
ParamStackPanel = window.FindName("ParamStackPanel")
TransferButton = window.FindName("TransferButton")
CancelButton = window.FindName("CancelButton")
CopyFormulasCheckbox = window.FindName("CopyFormulasCheckbox")

# ----------------------------------------------------------
# Populate Source and Target Lists
# ----------------------------------------------------------
for title in sorted(doc_dict.keys()):
    SourceListBox.Items.Add(title)
    TargetListBox.Items.Add(title)

# ----------------------------------------------------------
# Shared Parameter Lookup
# ----------------------------------------------------------
def get_external_definition_by_guid(guid):
    sp_file = app.OpenSharedParameterFile()
    if not sp_file:
        return None
    for group in sp_file.Groups:
        for definition in group.Definitions:
            try:
                if definition.GUID == guid:
                    return definition
            except:
                continue
    return None

# ----------------------------------------------------------
# Refresh Parameters
# ----------------------------------------------------------
def refresh_params(sender=None, args=None):
    ParamStackPanel.Children.Clear()
    src_title = SourceListBox.SelectedItem
    tgt_title = TargetListBox.SelectedItem
    if not src_title or not tgt_title:
        return

    src_doc = doc_dict[src_title]
    tgt_doc = doc_dict[tgt_title]
    src_fm = src_doc.FamilyManager
    tgt_fm = tgt_doc.FamilyManager

    tgt_params = {p.Definition.Name: p for p in tgt_fm.Parameters if p.Definition is not None}
    copy_formulas_checked = bool(CopyFormulasCheckbox.IsChecked)

    # Sort parameters alphabetically by name
    sorted_params = sorted([p for p in src_fm.Parameters if p.Definition is not None],
                           key=lambda p: p.Definition.Name)

    for param in sorted_params:
        cb = Controls.CheckBox()
        label = param.Definition.Name
        if param.IsShared:
            label += "  [Shared]"
        if param.IsInstance:
            label += "  (Instance)"
        else:
            label += "  (Type)"

        # Show formula only if checkbox is ticked
        if copy_formulas_checked and param.Formula:
            label += "  = " + param.Formula

        cb.Content = label
        cb.Tag = param

        name = param.Definition.Name
        tgt_param = tgt_params.get(name)
        src_formula = param.Formula or ""
        tgt_formula = tgt_param.Formula or "" if tgt_param else ""

        # Enable / highlight logic
        if tgt_param is None:
            # Parameter doesn't exist: allow copying
            cb.IsEnabled = True
            cb.Foreground = Media.Brushes.Black
        else:
            # Parameter exists
            if copy_formulas_checked and src_formula and src_formula != tgt_formula:
                # Formula-only update: allow
                cb.IsEnabled = True
                cb.Foreground = Media.Brushes.Blue
            else:
                # Parameter exists and formula same or not copying formulas
                cb.IsEnabled = False
                cb.Foreground = Media.Brushes.Gray

        ParamStackPanel.Children.Add(cb)

SourceListBox.SelectionChanged += refresh_params
TargetListBox.SelectionChanged += refresh_params
CopyFormulasCheckbox.Checked += refresh_params
CopyFormulasCheckbox.Unchecked += refresh_params

# ----------------------------------------------------------
# Transfer Logic
# ----------------------------------------------------------
def transfer_click(sender, args):
    src_title = SourceListBox.SelectedItem
    tgt_title = TargetListBox.SelectedItem
    if not src_title or not tgt_title:
        forms.alert("Select both source and target families.")
        return
    if src_title == tgt_title:
        forms.alert("Source and Target cannot be the same.")
        return

    src_doc = doc_dict[src_title]
    tgt_doc = doc_dict[tgt_title]
    src_fm = src_doc.FamilyManager
    tgt_fm = tgt_doc.FamilyManager

    added = []
    updated_formula = []
    skipped = []

    copy_formulas_checked = bool(CopyFormulasCheckbox.IsChecked)

    with revit.Transaction("Transfer Parameters", tgt_doc):

        # STEP 1: Add all parameters first
        for item in ParamStackPanel.Children:
            if not item.IsChecked:
                continue
            param = item.Tag
            name = param.Definition.Name
            tgt_param = next((p for p in tgt_fm.Parameters if p.Definition.Name == name), None)

            if tgt_param is None:
                try:
                    if param.IsShared:
                        ext_def = get_external_definition_by_guid(param.GUID)
                        if not ext_def:
                            skipped.append(name + " (Missing in SP file)")
                            continue
                        tgt_fm.AddParameter(ext_def, param.Definition.GetGroupTypeId(), param.IsInstance)
                    else:
                        tgt_fm.AddParameter(name, param.Definition.GetGroupTypeId(), param.Definition.GetDataType(), param.IsInstance)
                    added.append(name)
                except:
                    skipped.append(name + " (Error)")

        # STEP 2: Set formulas
        for item in ParamStackPanel.Children:
            if not item.IsChecked:
                continue
            if not copy_formulas_checked:
                continue
            param = item.Tag
            src_formula = param.Formula or ""
            if not src_formula.strip():
                continue
            tgt_param = next((p for p in tgt_fm.Parameters if p.Definition.Name == param.Definition.Name), None)
            if tgt_param is None:
                continue  # should never happen
            try:
                tgt_fm.SetFormula(tgt_param, src_formula)
                updated_formula.append(param.Definition.Name)
            except Exception:
                skipped.append(param.Definition.Name + " (Invalid formula)")



    # Show summary
    message = "Added:\n{}\n\nUpdated Formulas:\n{}\n\nSkipped:\n{}".format(
        "\n".join(added) if added else "None",
        "\n".join(updated_formula) if updated_formula else "None",
        "\n".join(skipped) if skipped else "None"
    )
    forms.alert("Transfer Complete\n\n" + message)

    # Refresh and then close window
    refresh_params()
    window.Close()


TransferButton.Click += transfer_click
CancelButton.Click += lambda s, e: window.Close()

# ----------------------------------------------------------
# Show Window
# ----------------------------------------------------------
window.ShowDialog()
