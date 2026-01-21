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

# Try parent view (e.g. for callouts)
try:
    parentViewId = curView.get_Parameter(DB.BuiltInParameter.SECTION_PARENT_VIEW_NAME).AsElementId()
    if parentViewId and parentViewId.IntegerValue != -1:
        ownerView = doc.GetElement(parentViewId)
        uidoc.RequestViewChange(ownerView)
except:
    pass

# Try primary view (e.g. for dependent views)
if ownerView is None:
    try:
        primaryViewId = curView.GetPrimaryViewId()
        if primaryViewId and primaryViewId.IntegerValue != -1:
            ownerView = doc.GetElement(primaryViewId)
            uidoc.RequestViewChange(ownerView)
    except:
        pass


# Alert if no owner view was found
if ownerView is None:
    forms.alert('View has no parent/primary view.', title='Script complete', warn_icon=False)
