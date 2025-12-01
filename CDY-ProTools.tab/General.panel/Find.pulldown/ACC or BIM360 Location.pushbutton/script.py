# -*- coding: utf-8 -*-
__title__ = 'ACC or BIM360 Location'
__author__  = 'Tay Othman, Joe Wemyss'
__doc__ = """Open the Autodesk Construction Cloud (ACC) website for the current project in the default web browser. EU = Normal Click, GB = Shift Click"""

# _________________________________________________________________________________________.NET imports
import clr
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import Document
from Autodesk.Revit.UI import TaskDialog
import webbrowser
import os

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

