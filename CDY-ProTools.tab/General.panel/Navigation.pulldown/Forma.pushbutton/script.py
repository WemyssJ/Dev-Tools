# -*- coding: utf-8 -*-
__title__ = 'Forma'
__author__  = 'Tay Othman, Joe Wemyss'
__doc__ = """Open the Autodesk Construction Cloud (ACC) website for the current project in the default web browser. EU = Normal Click, GB = Shift Click"""

# _________________________________________________________________________________________.NET imports
import clr
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import Document
from Autodesk.Revit.UI import TaskDialog
import webbrowser
import os

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

# _________________________________________________________________________________________Get the current version of Revit
revit_version = __revit__.Application.VersionNumber
doc = __revit__.ActiveUIDocument.Document

# -----------------------------
# Determine URL
# -----------------------------
hub_id = Document.GetHubId(doc)
proj_id = Document.GetProjectId(doc)
hub_str = hub_id[2:]
proj_str = proj_id[2:]

try:
    if __shiftclick__:  # Shift-click → GBR region
        accurl = "https://acc.gbr.autodesk.com/insight/accounts/" + hub_str + "/projects/" + proj_str + "/my-dashboard"
    else:  # Normal click → EU region
        accurl = "https://acc.autodesk.eu/insight/accounts/" + hub_str + "/projects/" + proj_str + "/home"
except NameError:
    # Fallback if __shiftclick__ is not defined
    accurl = "https://acc.autodesk.eu/insight/accounts/" + hub_str + "/projects/" + proj_str + "/home"

# -----------------------------
# Open URL based on Revit version
# -----------------------------
if revit_version == "2020":
    TaskDialog.Show("Revit Version", "Revit Version is 2020, this tool is compatible with Revit 2022 and Newer")
else:
    webbrowser.open_new_tab(accurl)

