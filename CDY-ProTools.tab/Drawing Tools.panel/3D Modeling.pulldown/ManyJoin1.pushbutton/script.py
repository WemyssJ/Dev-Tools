# -*- coding: utf-8 -*-
# pylint: skip-file

__doc__ = """Batch Join or Unjoin By Category (Shift = Unjoin)"""

__author__ = 'Roman Golev & Joe Wemyss'
__title__ = "Batch Join/Unjoin By Category"

import clr
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB import JoinGeometryUtils
import Autodesk
import sys
import os
from core.catlistenum import get_catlist
from pyrevit import forms


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

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
transaction = Autodesk.Revit.DB.Transaction(doc)

def main():
    catlist = get_catlist(doc)
    ops = ['Walls', 'Floors',
           'Structural Columns', 'Structural Foundations', 'Structural Framing']

    # Ask first category
    choice1 = forms.SelectFromList.show(ops, title='Select First Category')
    if not choice1:
        sys.exit()
    elements1 = catlist[choice1].WhereElementIsNotElementType().ToElements()

    # Ask second category
    choice2 = forms.SelectFromList.show(ops, title='Select Second Category (can be same)')
    if not choice2:
        sys.exit()
    elements2 = catlist[choice2].WhereElementIsNotElementType().ToElements()

    # Determine action based on Shift-click
    if __shiftclick__:
        action = "Unjoin"
    else:
        action = "Join"

    processed_pairs = set()
    transaction.Start("Batch {}".format(action))

    for A in elements1:
        for B in elements2:
            if A.Id == B.Id:
                continue

            pair_key = tuple(sorted([A.Id.IntegerValue, B.Id.IntegerValue]))
            if pair_key in processed_pairs:
                continue
            processed_pairs.add(pair_key)

            try:
                if __shiftclick__:
                    if JoinGeometryUtils.AreElementsJoined(doc, A, B):
                        JoinGeometryUtils.UnjoinGeometry(doc, A, B)
                else:
                    if not JoinGeometryUtils.AreElementsJoined(doc, A, B):
                        JoinGeometryUtils.JoinGeometry(doc, A, B)
            except:
                pass

    transaction.Commit()
    forms.alert("Batch {} complete!".format(action), title='Done')

if __name__ == '__main__':
    main()
