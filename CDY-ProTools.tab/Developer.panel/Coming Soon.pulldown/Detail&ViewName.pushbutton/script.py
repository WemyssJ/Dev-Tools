# -*- coding: utf-8 -*-
import clr
import sys
import re
from pyrevit import revit, DB, script
from System.Windows import Window, Thickness
from System.Windows.Controls import StackPanel, Button, RadioButton, Orientation

doc = revit.doc
uidoc = revit.uidoc
output = script.get_output()
output.set_title("Viewport Name ↔ Detail Number Copy Tool")

# -----------------------------
# WPF form to select operation
# -----------------------------
class OptionWindow(Window):
    def __init__(self):
        self.Title = "Select Operation"
        self.Width = 350
        self.Height = 150
        self.ResizeMode = 0  # No resize
        self.WindowStartupLocation = 0  # Center screen

        panel = StackPanel()
        panel.Orientation = Orientation.Vertical
        panel.Margin = Thickness(10)

        self.rb_view_to_detail = RadioButton()
        self.rb_view_to_detail.Content = "Copy View Name → Detail Number"
        self.rb_view_to_detail.IsChecked = True
        self.rb_view_to_detail.Margin = Thickness(5)
        panel.Children.Add(self.rb_view_to_detail)

        self.rb_detail_to_view = RadioButton()
        self.rb_detail_to_view.Content = "Copy Detail Number → View Name"
        self.rb_detail_to_view.Margin = Thickness(5)
        panel.Children.Add(self.rb_detail_to_view)

        btn_panel = StackPanel()
        btn_panel.Orientation = Orientation.Horizontal
        btn_panel.Margin = Thickness(10)

        confirm = Button()
        confirm.Content = "Confirm"
        confirm.Width = 100
        confirm.Margin = Thickness(5)
        confirm.Click += self.on_confirm
        btn_panel.Children.Add(confirm)

        cancel = Button()
        cancel.Content = "Cancel"
        cancel.Width = 100
        cancel.Margin = Thickness(5)
        cancel.Click += self.on_cancel
        btn_panel.Children.Add(cancel)

        panel.Children.Add(btn_panel)
        self.Content = panel
        self.result = None

    def on_confirm(self, sender, args):
        if self.rb_view_to_detail.IsChecked:
            self.result = "view_to_detail"
        elif self.rb_detail_to_view.IsChecked:
            self.result = "detail_to_view"
        self.Close()

    def on_cancel(self, sender, args):
        self.result = None
        self.Close()

# Show the WPF window
win = OptionWindow()
win.ShowDialog()
if win.result is None:
    output.print_md("❌ Operation cancelled.")
    script.exit()

operation = win.result

# -----------------------------
# Selection of viewports
# -----------------------------
selection_ids = uidoc.Selection.GetElementIds()
if not selection_ids:
    output.print_md("❌ No elements selected. Please select one or more viewports.")
    script.exit()

selected_viewports = [doc.GetElement(eid) for eid in selection_ids if isinstance(doc.GetElement(eid), DB.Viewport)]
if not selected_viewports:
    output.print_md("❌ No viewport elements selected. Please select one or more viewports.")
    script.exit()

# -----------------------------
# Helper function
# -----------------------------
def sanitize_for_detail_number(view_name):
    return re.sub(r'[^A-Za-z0-9_\-/.]', '', view_name)

# -----------------------------
# View Name → Detail Number
# -----------------------------
if operation == "view_to_detail":
    temp_suffix = "_temp"
    temp_map = {}

    # STEP 1: Apply temporary unique names
    with revit.Transaction("Temporarily Rename Detail Numbers"):
        for vp in selected_viewports:
            detail_param = vp.LookupParameter("Detail Number")
            if detail_param:
                original = detail_param.AsString()
                temp_name = "{}{}".format(original if original else "TEMP", temp_suffix)
                detail_param.Set(temp_name)
                temp_map[vp.Id.IntegerValue] = (original, temp_name)

    # STEP 2: Apply final sanitized names with rollback logic
    try:
        with revit.Transaction("Set Detail Number from View Name"):
            for vp in selected_viewports:
                view = doc.GetElement(vp.ViewId)
                sheet = doc.GetElement(vp.SheetId)
                detail_param = vp.LookupParameter("Detail Number")

                if view and sheet and detail_param:
                    base_detail = sanitize_for_detail_number(view.Name)

                    other_vps = [
                        doc.GetElement(vid)
                        for vid in sheet.GetAllViewports()
                        if vid != vp.Id
                    ]
                    used_detail_nums = [
                        other.LookupParameter("Detail Number").AsString()
                        for other in other_vps if other.LookupParameter("Detail Number")
                    ]

                    new_detail_num = base_detail
                    i = 1
                    while new_detail_num in used_detail_nums:
                        new_detail_num = "{}{}".format(base_detail, i)
                        i += 1

                    original, temp_name = temp_map.get(vp.Id.IntegerValue, ("?", "?"))
                    detail_param.Set(new_detail_num)
                    output.print_md("✅ `{}` → `{}` → `{}` for view `{}` on sheet `{}`".format(
                        original, temp_name, new_detail_num, view.Name, sheet.SheetNumber
                    ))

    except Exception as e:
        output.print_md("❌ Error occurred: {}. Rolling back...".format(str(e)))
        with revit.Transaction("Rollback to Original Detail Numbers"):
            for vp in selected_viewports:
                detail_param = vp.LookupParameter("Detail Number")
                if detail_param:
                    original, temp_name = temp_map.get(vp.Id.IntegerValue, (None, None))
                    if original is not None:
                        detail_param.Set(original)
                        output.print_md("↩️ Rolled back view ID `{}` to original `{}`".format(vp.Id.IntegerValue, original))

# -----------------------------
# Detail Number → View Name
# -----------------------------
elif operation == "detail_to_view":
    temp_suffix = "_temp"
    temp_names = {}

    # STEP 1: Temporarily rename views
    with revit.Transaction("Temporarily Rename Views"):
        for vp in selected_viewports:
            view = doc.GetElement(vp.ViewId)
            if view:
                try:
                    original_name = view.Name
                    temp_name = "{}{}".format(original_name, temp_suffix)
                    view.Name = temp_name
                    temp_names[view.Id.IntegerValue] = (original_name, temp_name)
                except Exception as e:
                    output.print_md("⚠️ Could not temporarily rename view ID `{}`: {}".format(view.Id, str(e)))

    # STEP 2: Set final names from detail numbers with rollback on failure
    try:
        with revit.Transaction("Set View Name from Detail Number"):
            existing_names = set(v.Name for v in DB.FilteredElementCollector(doc).OfClass(DB.View))

            for vp in selected_viewports:
                view = doc.GetElement(vp.ViewId)
                if not view:
                    output.print_md("⚠️ Could not find view for viewport ID: {}".format(vp.Id))
                    continue

                detail_param = vp.LookupParameter("Detail Number")
                if not detail_param:
                    output.print_md("⚠️ No 'Detail Number' found for viewport ID `{}`".format(vp.Id))
                    continue

                detail_number = detail_param.AsString()
                if not detail_number:
                    output.print_md("⚠️ Empty detail number for viewport ID `{}`".format(vp.Id))
                    continue

                base_name = detail_number
                new_name = base_name
                i = 1
                while new_name in existing_names:
                    new_name = "{}_{}".format(base_name, i)
                    i += 1

                old_name, temp_name = temp_names.get(view.Id.IntegerValue, ("?", view.Name))
                try:
                    view.Name = new_name
                    existing_names.add(new_name)
                    output.print_md("✅ `'{}' → '{}' → '{}'` for view ID `{}`".format(
                        old_name, temp_name, new_name, view.Id.IntegerValue
                    ))
                except Exception as e:
                    raise Exception("❌ Failed to set view name for view ID `{}`: {}".format(view.Id, str(e)))

    except Exception as e:
        output.print_md("\n❌ Error during renaming process: {}\n🔄 Rolling back to original names...".format(e))
        with revit.Transaction("Rollback View Names"):
            for vp in selected_viewports:
                view = doc.GetElement(vp.ViewId)
                if view and view.Id.IntegerValue in temp_names:
                    original, temp = temp_names[view.Id.IntegerValue]
                    try:
                        view.Name = original
                        output.print_md("↩️ Rolled back view ID `{}` to `'{}'`".format(view.Id.IntegerValue, original))
                    except Exception as rollback_err:
                        output.print_md("⚠️ Failed to roll back view ID `{}`: {}".format(view.Id.IntegerValue, rollback_err))
