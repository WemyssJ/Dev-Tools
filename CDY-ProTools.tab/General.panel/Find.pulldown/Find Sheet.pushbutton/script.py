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
curView = revit.active_view

ownerView = None  # Initialize at top
primaryView = None  # Properly defined before use

# Try sheet view (e.g. if view is on a sheet)
try:
        # Get the sheet that contains this view (via Viewport)
        viewports = DB.FilteredElementCollector(doc).OfClass(DB.Viewport).ToElements()
        for vp in viewports:
            if vp.ViewId == curView.Id:
                sheet = doc.GetElement(vp.SheetId)
                if sheet:
                    uidoc.RequestViewChange(sheet)
                    ownerView = sheet
                    break
except:
        forms.alert('View is not placed on a sheet.', title='Script complete', warn_icon=False)

