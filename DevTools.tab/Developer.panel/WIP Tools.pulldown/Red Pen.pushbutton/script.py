# -*- coding: utf-8 -*-
"""Toggle Text Visibility in Their Own Views (Synced)
This script finds all TextNote elements with TextNoteType containing "Internal Comment"
and toggles their visibility together in their host views.
If any are hidden, all will be unhidden; if all are visible, all will be hidden.
"""

__title__ = "Toggle Text\nVisibility (Synced)"
__author__ = "Your Name"

# pyRevit imports
from pyrevit import revit, DB, forms
from pyrevit import script

# Standard imports
import clr
from System.Collections.Generic import List

# Revit API imports
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *

# Get current document
doc = revit.doc
uidoc = revit.uidoc

def get_text_elements_with_internal_comment_type():
    """Get all TextNote elements whose TextNoteType name contains 'Internal Comment' (case-insensitive)"""
    collector = FilteredElementCollector(doc).OfClass(TextNote)
    filtered_text_notes = []
    for text_note in collector:
        type_id = text_note.GetTypeId()
        text_note_type = doc.GetElement(type_id)
        if text_note_type:
            type_name_param = text_note_type.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)
            if type_name_param:
                type_name = type_name_param.AsString()
                if type_name and "internal comment" in type_name.lower():
                    filtered_text_notes.append(text_note)
    return filtered_text_notes

def are_any_elements_hidden(text_elements, views):
    """Return True if any of the text elements is hidden in its host view"""
    for elem in text_elements:
        view_id = elem.OwnerViewId.IntegerValue
        if view_id in views:
            view = views[view_id]
            if elem.IsHidden(view):
                return True
    return False

def set_elements_visibility(text_elements, views, visible):
    """Set all elements visible/unhidden or hidden in their host views"""
    for elem in text_elements:
        view_id = elem.OwnerViewId.IntegerValue
        if view_id in views:
            view = views[view_id]
            if visible:
                view.UnhideElements(List[ElementId]([elem.Id]))
            else:
                view.HideElements(List[ElementId]([elem.Id]))

def main():
    output = script.get_output()
    output.print_md("# Toggle Text Visibility Script (Synced)")
    output.print_md("---")

    # Get all text elements with 'Internal Comment' in their TextNoteType
    text_elements = get_text_elements_with_internal_comment_type()
    output.print_md("Found **{0}** text elements with 'Internal Comment' TextNoteType".format(len(text_elements)))

    if not text_elements:
        forms.alert("No matching text elements found in the document.", exitscript=True)

    # Get all views (excluding templates and sheets)
    view_collector = FilteredElementCollector(doc).OfClass(View)
    views = {v.Id.IntegerValue: v for v in view_collector if not v.IsTemplate and not isinstance(v, ViewSheet)}

    output.print_md("Found **{0}** views".format(len(views)))

    # Confirm with user
    result = forms.alert(
        "This will toggle visibility of {0} text elements in their respective views *together*.\n"
        "If any are hidden, all will be shown; otherwise, all will be hidden.\n\n"
        "Do you want to continue?".format(len(text_elements)),
        yes=True, no=True
    )
    if not result:
        script.exit()

    with revit.Transaction("Toggle Text Visibility Synced"):
        any_hidden = are_any_elements_hidden(text_elements, views)
        set_elements_visibility(text_elements, views, visible=any_hidden)

    output.print_md("---")
    output.print_md("## Results")
    output.print_md("- Total elements processed: **{0}**".format(len(text_elements)))
    output.print_md("- Set all elements to: **{0}**".format("Visible" if any_hidden else "Hidden"))
    output.print_md("---")
    output.print_md("**Script completed successfully!**")

if __name__ == "__main__":
    main()
