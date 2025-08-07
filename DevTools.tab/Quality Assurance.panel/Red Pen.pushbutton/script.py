# -*- coding: utf-8 -*-
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
    # output = script.get_output()
    # output.print_md("# Toggle Internal Comment Visibility")
    # output.print_md("---")

    # Get all text elements with 'Internal Comment' in their TextNoteType
    text_elements = get_text_elements_with_internal_comment_type()
    # output.print_md("Found **{0}** text elements with 'Internal Comment' TextNoteType".format(len(text_elements)))

    if not text_elements:
        forms.alert("No matching text elements found in the document.", exitscript=False)

    # Get all views (excluding templates and sheets)
    view_collector = FilteredElementCollector(doc).OfClass(View)
    views = {v.Id.IntegerValue: v for v in view_collector if not v.IsTemplate and not isinstance(v, ViewSheet)}

    # output.print_md("Found **{0}** views".format(len(views)))

    # Determine current visibility state
    any_hidden = are_any_elements_hidden(text_elements, views)
    new_visibility_state = "Visible" if any_hidden else "Hidden"

    # Confirm with user, showing what will happen
    result = forms.alert(
        "{0} Internal Comment text elements found.\n"
        "These elements will be made:\n\n"
        "{1}.\n\n"
        "Do you want to continue?".format(len(text_elements), new_visibility_state),
        yes=True, no=True
    )
    if not result:
        script.exit()

    # Toggle visibility
    with revit.Transaction("Toggle Internal Comment Visibility"):
        set_elements_visibility(text_elements, views, visible=any_hidden)

    # output.print_md("---")
    # output.print_md("## Results")
    # output.print_md("- Total elements processed: **{0}**".format(len(text_elements)))
    # output.print_md("- Set all elements to: **{0}**".format(new_visibility_state))
    # output.print_md("---")
    # output.print_md("**Script completed successfully!**")

if __name__ == "__main__":
    main()
