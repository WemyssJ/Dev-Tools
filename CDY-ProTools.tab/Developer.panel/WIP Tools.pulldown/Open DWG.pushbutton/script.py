# -*- coding: utf-8 -*-
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.DB import ExternalFileReference, ExternalFileUtils, ModelPathUtils
from Autodesk.Revit.UI.Selection import ObjectType
import subprocess
import os
from pyrevit import script

# Get current document
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

# --------------------------
# Check if a DWG is preselected
# --------------------------
sel_ids = uidoc.Selection.GetElementIds()
if sel_ids:
    # Use the first preselected element
    elem = doc.GetElement(list(sel_ids)[0])
else:
    # Prompt user to pick a DWG
    try:
        ref = uidoc.Selection.PickObject(ObjectType.Element, "Pick a linked DWG")
        elem = doc.GetElement(ref.ElementId)
    except:
        TaskDialog.Show("Cancelled", "Selection cancelled.")
        sys.exit()

# Validate element
if not isinstance(elem, ImportInstance):
    TaskDialog.Show("Error", "Selected element is not a linked DWG (ImportInstance).")
    sys.exit()

# --------------------------
# Get its type (ImportSymbol)
# --------------------------
import_symbol = doc.GetElement(elem.GetTypeId())

# --------------------------
# Get external file reference
# --------------------------
efr = ExternalFileUtils.GetExternalFileReference(doc, import_symbol.Id)
if not efr:
    TaskDialog.Show("Error", "No external file reference found for this DWG.")
    sys.exit()

dwg_path = ModelPathUtils.ConvertModelPathToUserVisiblePath(efr.GetAbsolutePath())

# --------------------------
# Open DWG function
# --------------------------
def open_dwg(path):
    if path and os.path.exists(path):
        try:
            # Attempt to open in existing AutoCAD session
            subprocess.Popen(['acad.exe', path])
        except Exception:
            # Fallback: open with default associated program
            os.startfile(path)
        # Show a Revit native TaskDialog confirmation
        TaskDialog.Show("DWG Opened", "DWG successfully opened in AutoCAD:\n\n{}".format(path))
    else:
        TaskDialog.Show("DWG Not Found", "The DWG path does not exist:\n\n{}".format(path))

# --------------------------
# Execute open
# --------------------------
open_dwg(dwg_path)
