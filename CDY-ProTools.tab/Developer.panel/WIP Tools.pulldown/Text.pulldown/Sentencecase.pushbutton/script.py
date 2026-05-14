"""Changes all characters in text box to Sentencecase"""


__context__ = 'OST_TextNotes'

from pyrevit import revit, coreutils

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

def sentencecase():
    with revit.Transaction('sentencecase'):
        for el in selection.elements:
            el.Text = el.Text[0].upper() + el.Text[1:].lower()

sentencecase()