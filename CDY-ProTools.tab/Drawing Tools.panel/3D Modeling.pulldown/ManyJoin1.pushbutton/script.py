# -*- coding: utf-8 -*-
# pylint: skip-file

__doc__ = """Joins multiple elements / Присоединяет множественные элементы"""

__author__ = 'Roman Golev & Joe Wemyss'
__title__ = "Batch Join By Category"

import clr
clr.AddReference('RevitAPI')
import Autodesk
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI.Selection import ObjectType
import sys
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
    ops = ['Columns', 'Walls', 'Floors', 'Roofs',
           'Structural Columns', 'Structural Foundations', 'Structural Framing']

    # First category
    choice1 = forms.CommandSwitchWindow.show(ops, message='Select First Category to join')
    try:
        elements1 = catlist[choice1].WhereElementIsNotElementType().ToElements()
    except:
        sys.exit()

    # Second category (now allows same category)
    choice2 = forms.CommandSwitchWindow.show(ops, message='Select Second Category (can be same)')
    try:
        elements2 = catlist[choice2].WhereElementIsNotElementType().ToElements()
    except:
        sys.exit()

    # Avoid double-joins and self-joins
    processed_pairs = set()

    transaction.Start('Batch Join')

    for A in elements1:
        for B in elements2:
            # Skip joining element with itself
            if A.Id == B.Id:
                continue

            # Prevent duplicate A-B and B-A joins
            pair_key = tuple(sorted([A.Id.IntegerValue, B.Id.IntegerValue]))
            if pair_key in processed_pairs:
                continue
            processed_pairs.add(pair_key)

            try:
                JoinGeometryUtils.JoinGeometry(doc, A, B)
            except:
                pass

    transaction.Commit()


if __name__ == '__main__':
    main()
