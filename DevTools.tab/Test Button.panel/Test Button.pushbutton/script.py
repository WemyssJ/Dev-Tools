# import libraries
import clr
import os
from os import listdir
import System
from System.IO import SearchOption
from System import Environment


# import pyrevit libraries
from pyrevit import forms,revit,DB


AppDataList = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData).split("\\")
AppDataList.pop(-1)
AppData = "\\".join(AppDataList)
button_location = AppData + "\Roaming\pyRevit\Extensions\DevTools.extension\DevTools.tab\Test Button.panel\Test Button.pushbutton"
print(button_location)

os.startfile(button_location)

