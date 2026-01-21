
# coding: utf-8
"""
Structural Framing: Allow/Disallow joins with contextual UI.
- If elements are selected, processes ONLY the selection (Both ends + Disallow).
- If no elements selected, pops up UI to choose:
    * Ends: Start only / End only / Both ends
    * Action: Disallow or Allow
"""

from pyrevit import revit, DB, forms

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

doc = revit.doc
uidoc = revit.uidoc


def is_structural_framing(el):
    """Check element is in Structural Framing category."""
    try:
        return (el
                and el.Category
                and el.Category.Id.IntegerValue == int(DB.BuiltInCategory.OST_StructuralFraming))
    except Exception:
        return False


def get_framing_from_selection():
    """Return Structural Framing elements from current selection."""
    try:
        sel_ids = list(uidoc.Selection.GetElementIds())
    except Exception:
        sel_ids = []
    if not sel_ids:
        return []
    candidates = (doc.GetElement(eid) for eid in sel_ids)
    return [e for e in candidates if is_structural_framing(e)]


def get_all_framing():
    """Return all Structural Framing elements in the model."""
    return list(
        DB.FilteredElementCollector(doc)
        .OfCategory(DB.BuiltInCategory.OST_StructuralFraming)
        .WhereElementIsNotElementType()
        .ToElements()
    )


def apply_action(e, ends, action):
    """
    Apply Allow/Disallow for given ends on element e.
    Returns number of changes applied.
    """
    changes = 0
    for end in ends:
        try:
            is_allowed = DB.Structure.StructuralFramingUtils.IsJoinAllowedAtEnd(e, end)
            if action == 'Disallow' and is_allowed:
                DB.Structure.StructuralFramingUtils.DisallowJoinAtEnd(e, end)
                changes += 1
            elif action == 'Allow' and not is_allowed:
                DB.Structure.StructuralFramingUtils.AllowJoinAtEnd(e, end)
                changes += 1
        except Exception:
            # Ignore per-end issues, continue
            pass
    return changes


# --- Determine target elements and UI behavior ---
framing_elems = get_framing_from_selection()
ui_required = False

if framing_elems:
    # Selection exists: default to Both + Disallow (no UI)
    ends = (0, 1)   # 0 = Start, 1 = End
    action = 'Disallow'
else:
    # No selection: collect whole model and ask user for options
    framing_elems = get_all_framing()
    if not framing_elems:
        forms.alert('No Structural Framing elements found in the model.', exitscript=True)
    ui_required = True

# --- UI: only if no selection ---
if ui_required:
    # Ends selection (SelectFromList)
    end_choice = forms.SelectFromList.show(
        ['Start only', 'End only', 'Both ends'],
        title='Which end(s) to modify for Structural Framing joins?',
        multiselect=False
    )
    if not end_choice:
        forms.alert('Cancelled.', exitscript=True)

    if end_choice == 'Start only':
        ends = (0,)
    elif end_choice == 'End only':
        ends = (1,)
    else:
        ends = (0, 1)

    # Action selection (SelectFromList)
    action_choice = forms.SelectFromList.show(
        ['Disallow', 'Allow'],
        title='Do you want to Disallow or Allow joins at the selected end(s)?',
        multiselect=False
    )
    if not action_choice:
        forms.alert('Cancelled.', exitscript=True)
    action = action_choice

# --- Transaction name ---
end_labels = []
if 0 in ends:
    end_labels.append('Start')
if 1 in ends:
    end_labels.append('End')
tx_name = 'Structural Framing: {} joins ({})'.format(action, ' & '.join(end_labels))

# --- Execute ---
changed_elements = 0
changed_ends = 0
skipped = []

with revit.Transaction(tx_name):
    for e in framing_elems:
        try:
            changes = apply_action(e, ends, action)
            if changes > 0:
                changed_elements += 1
                changed_ends += changes
        except Exception:
            try:
                name = '{} ({})'.format(e.Name, e.Id.IntegerValue)
            except Exception:
                name = str(e.Id.IntegerValue)
            skipped.append(name)

# --- Report ---
if changed_elements == 0 and not skipped:
    forms.alert('No changes were required. Joins already {} at requested end(s).'.format(
        'disallowed' if action == 'Disallow' else 'allowed'
    ))
else:
    msg_lines = [
        '{} joins at {} end(s) on {} element(s).'.format(
            action, changed_ends, changed_elements
        )
    ]
    if skipped:
        msg_lines.append('Skipped {} element(s): {}'.format(len(skipped), ', '.join(skipped[:10])))
        if len(skipped) > 10:
            msg_lines.append('…and {} more.'.format(len(skipped) - 10))
    forms.alert('\n'.join(msg_lines))
