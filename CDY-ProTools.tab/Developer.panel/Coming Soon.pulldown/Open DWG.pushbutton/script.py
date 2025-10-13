# -*- coding: utf-8 -*-
# Link Options Script – Safe DWG opener + Reload Links
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens

import os
import threading
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.DB import ExternalFileUtils, ModelPathUtils
from Autodesk.Revit.UI.Selection import ObjectType
from pyrevit import revit, DB, forms, script

logger = script.get_logger()
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

# --------------------------
# Load XAML dynamically (same folder as this script)
# --------------------------
script_dir = os.path.dirname(__file__)
xaml_path = os.path.join(script_dir, "LinkOptions.xaml")

window = forms.WPFWindow(xaml_path)
window.show()

# --------------------------
# Functions
# --------------------------
def open_dwg_safe(dwg_path):
    """Open DWG in default program safely using a background thread."""
    if dwg_path and os.path.exists(dwg_path):
        subprocess.Popen(['cmd', '/c', 'start', '', dwg_path], shell=True)
        TaskDialog.Show("DWG Opened", "DWG successfully opened:\n\n{}".format(dwg_path))
    else:
        TaskDialog.Show("DWG Not Found", "The DWG path does not exist:\n\n{}".format(dwg_path))

def open_selected_dwg():
    sel_ids = uidoc.Selection.GetElementIds()
    if sel_ids:
        elem = doc.GetElement(list(sel_ids)[0])
    else:
        try:
            ref = uidoc.Selection.PickObject(ObjectType.Element, "Pick a linked DWG")
            elem = doc.GetElement(ref.ElementId)
        except:
            TaskDialog.Show("Cancelled", "Selection cancelled.")
            return

    if not isinstance(elem, ImportInstance):
        TaskDialog.Show("Error", "Selected element is not a linked DWG (ImportInstance).")
        return

    import_symbol = doc.GetElement(elem.GetTypeId())
    efr = ExternalFileUtils.GetExternalFileReference(doc, import_symbol.Id)
    if not efr:
        TaskDialog.Show("Error", "No external file reference found for this DWG.")
        return

    dwg_path = ModelPathUtils.ConvertModelPathToUserVisiblePath(efr.GetAbsolutePath())
    open_dwg_safe(dwg_path)

def reload_links_from_selection():
    selection = revit.get_selection()
    if not selection:
        forms.alert("No elements selected.")
        return

    revit_links = []
    cad_links = []

    for el in selection:
        if isinstance(el, DB.RevitLinkInstance):
            revit_links.append(revit.db.ExternalRef(el.GetLinkDocument(), None))
        elif isinstance(el, DB.ImportInstance):
            type_el = revit.doc.GetElement(el.GetTypeId())
            if isinstance(type_el, DB.CADLinkType):
                cad_links.append(revit.db.ExternalRef(type_el, None))

    if revit_links:
        reload_locally = False
        if revit.doc.IsWorkshared:
            reload_locally = forms.alert(
                'Do you want to reload links locally?',
                title='Reload locally?',
                yes=True, no=True
            )
        for xref in revit_links:
            if reload_locally:
                try:
                    if not xref.link.LocallyUnloaded:
                        xref.link.UnloadLocally(None)
                    xref.link.RevertLocalUnloadStatus()
                except Exception as e:
                    logger.debug('Error while locally reloading linked model: {}'.format(e))
            else:
                xref.reload()

    if cad_links:
        with revit.Transaction('Reload CAD Links'):
            for xref in cad_links:
                xref.reload()

    if not revit_links and not cad_links:
        forms.alert("No Revit or CAD links selected.")
    else:
        print("Reload completed.")

# --------------------------
# Event Handlers
# --------------------------
def on_ok(sender, e):
    if window.rbOpenDWG.IsChecked:
        open_selected_dwg()
    elif window.rbReloadLinks.IsChecked:
        reload_links_from_selection()
    window.close()

def on_cancel(sender, e):
    window.close()

window.okBtn.Click += on_ok
window.cancelBtn.Click += on_cancel
