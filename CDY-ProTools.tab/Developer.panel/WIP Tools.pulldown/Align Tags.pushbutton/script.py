# -*- coding: utf-8 -*-
import clr

from pyrevit import revit, forms, script
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType
from System.Collections.Generic import List

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


# -----------------------------
# Selection Filter (Tags Only)
# -----------------------------
class TagSelectionFilter(ISelectionFilter):
    def AllowElement(self, element):
        if isinstance(element, IndependentTag):
            return True
        return False

    def AllowReference(self, reference, point):
        return True


# -----------------------------
# Ask User Alignment Direction
# -----------------------------
alignment_choice = forms.CommandSwitchWindow.show(
    ["Align Vertically", "Align Horizontally"],
    message="How would you like to align the selected tags?"
)

if not alignment_choice:
    script.exit()


uidoc = revit.uidoc
doc = revit.doc


# -----------------------------
# Select Tags
# -----------------------------
try:
    references = uidoc.Selection.PickObjects(
        ObjectType.Element,
        TagSelectionFilter(),
        "Select tags to align"
    )
except:
    script.exit()

if not references:
    forms.alert("No tags selected.", exitscript=True)

tags = [doc.GetElement(ref.ElementId) for ref in references]

if len(tags) < 2:
    forms.alert("Select at least two tags to align.", exitscript=True)


# -----------------------------
# Determine Alignment Target
# -----------------------------
base_tag = tags[0]
base_point = base_tag.TagHeadPosition

move_vectors = {}

if alignment_choice == "Align Vertically":
    target_x = base_point.X
    for tag in tags:
        current = tag.TagHeadPosition
        delta = XYZ(target_x - current.X, 0, 0)
        move_vectors[tag.Id] = delta

elif alignment_choice == "Align Horizontally":
    target_y = base_point.Y
    for tag in tags:
        current = tag.TagHeadPosition
        delta = XYZ(0, target_y - current.Y, 0)
        move_vectors[tag.Id] = delta


# -----------------------------
# Move Tags
# -----------------------------
with revit.Transaction("Align Tags"):
    for tag in tags:
        delta = move_vectors[tag.Id]
        if not delta.IsZeroLength():
            ElementTransformUtils.MoveElement(doc, tag.Id, delta)


# -----------------------------
# Reselect Tags
# -----------------------------
id_list = List[ElementId]()
for tag in tags:
    id_list.Add(tag.Id)

uidoc.Selection.SetElementIds(id_list)


forms.alert("Tags aligned and reselected.", title="Complete")