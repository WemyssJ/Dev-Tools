"""Sets the revision visibility parameter to None for all revisions."""

from pyrevit import revit, DB

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

revs = DB.FilteredElementCollector(revit.doc)\
         .OfCategory(DB.BuiltInCategory.OST_Revisions)\
         .WhereElementIsNotElementType()

with revit.Transaction('Turn off Revisions'):
    for rev in revs:
        rev.Visibility = DB.RevisionVisibility.Hidden
