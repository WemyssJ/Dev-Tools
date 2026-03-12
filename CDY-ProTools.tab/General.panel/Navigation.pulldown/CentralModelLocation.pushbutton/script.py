"""Print the full path to the central model (if model is workshared).

Shift+Click:
Open central model path in file browser
"""
#pylint: disable=E0401,invalid-name
import os.path as op

from pyrevit import revit
from pyrevit import forms
from pyrevit import script

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


if forms.check_workshared(doc=revit.doc):
    central_path = revit.query.get_central_path(doc=revit.doc)
    if __shiftclick__:  print(central_path)
    else:
         #pylint: disable=E0602
        script.show_folder_in_explorer(op.dirname(central_path))
