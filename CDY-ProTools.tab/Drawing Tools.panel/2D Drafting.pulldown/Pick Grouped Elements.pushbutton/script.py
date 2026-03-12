# -*- coding: utf-8 -*-
__doc__ = "Window-select groups and expand selection to their member elements"

import clr

clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")
clr.AddReference("System")

from Autodesk.Revit.DB import Group, ElementId
from Autodesk.Revit.UI.Selection import ObjectType
from Autodesk.Revit.Exceptions import OperationCanceledException
from System.Collections.Generic import List

from pyrevit import revit, forms

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

uidoc = revit.uidoc
doc = revit.doc

try:
    # Window selection
    refs = uidoc.Selection.PickObjects(
        ObjectType.Element,
        "Window-select groups"
    )

    if not refs:
        forms.alert("No elements selected.", exitscript=True)

    member_ids = set()

    for ref in refs:
        element = doc.GetElement(ref.ElementId)

        if isinstance(element, Group):
            for mid in element.GetMemberIds():
                member_ids.add(mid)

    if not member_ids:
        forms.alert("No groups were selected.", exitscript=True)

    # Convert to .NET ICollection<ElementId>
    id_list = List[ElementId]()
    for mid in member_ids:
        id_list.Add(mid)

    uidoc.Selection.SetElementIds(id_list)

except OperationCanceledException:
    pass

except Exception as ex:
    forms.alert("Error:\n{}".format(str(ex)))