# import libraries
import clr
import os
from os import listdir
import System
from System.IO import SearchOption
from System import Environment

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