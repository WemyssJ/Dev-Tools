# import libraries
import clr
import os
from os import listdir
import System
from System.IO import SearchOption
from System import Environment

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

# import pyrevit libraries
from pyrevit import forms,revit,DB

# get document
doc = revit.doc

# try to open document, or cache
try:
	AppDataList = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData).split("\\")
	AppDataList.pop(-1)
	AppData = "\\".join(AppDataList)
	button_location = AppData + "\\pyRevit\\Extensions\\DevTools.extension\\DevTools.tab\\Test Button.panel\\Test Button.pushbutton\\"

	os.startfile(button_location)
except: 
	forms.alert('File could not be found.', title='Script completed')