# -*- coding: utf-8 -*-
__context__ = 'OST_TextNotes'
__doc__ = 'Inserts a special character at the beginning of selected Text Notes.'
__title__ = 'Symbols'

from pyrevit import revit, coreutils

from pyrevit.framework import List
from pyrevit import revit, DB, UI
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


selection = revit.get_selection()

def addSymbol(symbol):
    with revit.Transaction('Symbols'):
        for el in selection.elements:
            el.Text = symbol + el.Text
            # el.Text = el.Text.upper()

# options = sorted(["±","°","Ø","€","<",">","#","&","Ʃ","λ","μ","≈","≠","≤","≥"])
options = ["±","Ø","€","°","<",">","≤","≥","≈","≠","#","&","Ʃ","λ","μ"]

selected_switch = \
    forms.CommandSwitchWindow.show(options,
                                   message='Vyber symbol:')

if selected_switch:
    addSymbol(selected_switch)