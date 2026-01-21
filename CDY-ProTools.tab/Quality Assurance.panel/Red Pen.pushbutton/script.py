# -*- coding: utf-8 -*-
# pyRevit imports
from pyrevit import revit, DB, forms
from pyrevit import script

# Standard imports
import clr

#####
# Telemetry imports
import os, sys

# Add lib folder for telemetry_auto
lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'lib'))
if lib_path not in sys.path:
    sys.path.append(lib_path)

import telemetry_auto

TOOL_NAME = "Red Pen"
telemetry_auto.log_tool_usage(TOOL_NAME)
######


from System.Collections.Generic import List

# Revit API imports
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *

# Get current document
doc = revit.doc
uidoc = revit.uidoc


def get_text_elements_with_internal_comment_type():
    """Get all TextNote elements whose TextNoteType name contains 'Internal Comment' (case-insensitive)."""
    collector = FilteredElementCollector(doc).OfClass(TextNote)
    filtered = []

    for text_note in collector:
        type_id = text_note.GetTypeId()
        ttype = doc.GetElement(type_id)
        if ttype:
            pname = ttype.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)
            if pname:
                tname = pname.AsString()
                if tname and "internal comment" in tname.lower():
                    filtered.append(text_note)

    return filtered


def are_any_elements_hidden(text_elements, views):
    """Check if any element is currently hidden in its owner view."""
    for elem in text_elements:
        v_id = elem.OwnerViewId.IntegerValue
        if v_id in views:
            view = views[v_id]
            if elem.IsHidden(view):
                return True
    return False


def set_elements_visibility(text_elements, views, visible):
    """Hide or unhide elements in their owner views."""
    for elem in text_elements:
        v_id = elem.OwnerViewId.IntegerValue
        if v_id in views:
            view = views[v_id]

            try:
                if visible:
                    view.UnhideElements(List[ElementId]([elem.Id]))
                else:
                    view.HideElements(List[ElementId]([elem.Id]))
            except:
                # If a specific view cannot hide/unhide (e.g., legend on sheet), ignore
                pass


def main():
    text_elements = get_text_elements_with_internal_comment_type()

    if not text_elements:
        forms.alert("No 'Internal Comment' text elements found.", exitscript=True)

    view_collector = FilteredElementCollector(doc).OfClass(View)
    views = {
        v.Id.IntegerValue: v
        for v in view_collector
        if not v.IsTemplate  # include sheets!
    }

    # Determine the new state
    any_hidden = are_any_elements_hidden(text_elements, views)
    new_state = "Visible" if any_hidden else "Hidden"

    result = forms.alert(
        "{0} Internal Comment text elements found.\n"
        "They will be set to: {1}.\n\nContinue?"
        .format(len(text_elements), new_state),
        yes=True, no=True
    )

    if not result:
        script.exit()

    with revit.Transaction("Toggle Internal Comment Visibility"):
        set_elements_visibility(text_elements, views, visible=any_hidden)

    forms.alert("Done! Set {0} elements to {1}.".format(len(text_elements), new_state))


if __name__ == "__main__":
    main()