# import libraries
import clr
import os
from os import listdir
import System
from System.IO import SearchOption
from System import Environment


# import pyrevit libraries
from pyrevit import forms,revit,DB

if __shiftclick__:  
    AppDataList = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData).split("\\")
    AppDataList.pop(-1)
    AppData = "\\".join(AppDataList)
    button_location = AppData + "\Roaming\pyRevit\Extensions\DevTools.extension\DevTools.tab\Developer.panel\WIP Tools.pulldown\Test Button.pushbutton"
    print(button_location)

    os.startfile(button_location)
else:
    print("No script added to test button. Shift click to navigate to file location")


