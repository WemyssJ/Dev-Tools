# -*- coding: utf-8 -*-
# Link Options – Safe DWG Opener + Reload Selected Links
# pylint: disable=import-error,invalid-name,broad-except,superfluous-parens

import os
import subprocess
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.UI.Selection import ObjectType
from pyrevit import revit, DB, forms, script

logger = script.get_logger()
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

# --------------------------
# Load WPF UI
# --------------------------
script_dir = os.path.dirname(__file__)
xaml_path = os.path.join(script_dir, "LinkOptions.xaml")
window = forms.WPFWindow(xaml_path)
window.result = None

# --------------------------
# Event Handlers
# --------------------------
def on_ok(sender, e):
    if window.rbOpenDWG.IsChecked:
        window.result = "open_dwg"
    elif window.rbReloadLinks.IsChecked:
        window.result = "reload_links"
    window.Close()

def on_cancel(sender, e):
    window.result = None
    window.Close()

window.okBtn.Click += on_ok
window.cancelBtn.Click += on_cancel

# Show window modally and safely
window.show_dialog()

# --------------------------
# After window closes → run user choice
# --------------------------
def open_dwg_safe(path):
    """Safely open DWG using AutoCAD or default program."""
    if path and os.path.exists(path):
        try:
            subprocess.Popen(['acad.exe', path])
        except Exception:
            os.startfile(path)
        TaskDialog.Show("DWG Opened", "DWG successfully opened:\n\n{}".format(path))
    else:
        TaskDialog.Show("DWG Not Found", "The DWG path does not exist:\n\n{}".format(path))


def open_selected_dwg():
    """Find selected DWG link and open it."""
    sel_ids = uidoc.Selection.GetElementIds()
    elem = None

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
    """Reloads selected Revit and CAD links."""
    selection = revit.get_selection()
    if not selection:
        forms.alert("No elements selected.")
        return

    revit_links = []
    cad_links = []

    # Separate selection by type
    for el in selection:
        if isinstance(el, DB.RevitLinkInstance):
            try:
                link_doc = el.GetLinkDocument()
                if link_doc:
                    revit_links.append(revit.db.ExternalRef(link_doc, None))
            except Exception as e:
                logger.debug("Error accessing link doc: {}".format(e))
        elif isinstance(el, DB.ImportInstance):
            type_el = doc.GetElement(el.GetTypeId())
            if isinstance(type_el, DB.CADLinkType):
                cad_links.append(revit.db.ExternalRef(type_el, None))

    # Reload Revit links
    if revit_links:
        reload_locally = False
        if doc.IsWorkshared:
            reload_locally = forms.alert(
                'Do you want to reload links locally, without taking ownership and without affecting other users?\n'
                'Clicking "No" will reload for all users.',
                title='Reload locally?',
                yes=True, no=True
            )

        for xref in revit_links:
            print("Reloading Revit Link: {}".format(xref.name))
            if reload_locally:
                try:
                    if not xref.link.LocallyUnloaded:
                        xref.link.UnloadLocally(None)
                    xref.link.RevertLocalUnloadStatus()
                except Exception as e:
                    logger.debug('Error while locally reloading linked model: {}'.format(e))
            else:
                try:
                    xref.reload()
                except Exception as e:
                    logger.debug('Error reloading Revit link: {}'.format(e))

    # Reload CAD links
    if cad_links:
        with revit.Transaction('Reload CAD Links'):
            for xref in cad_links:
                print("Reloading CAD Link: {}".format(xref.name))
                try:
                    xref.reload()
                except Exception as e:
                    logger.debug('Error reloading CAD link: {}'.format(e))

    if not revit_links and not cad_links:
        forms.alert("No Revit or CAD links selected.")
    else:
        print("Reload completed.")


# --------------------------
# Execute selected action
# --------------------------
if window.result == "open_dwg":
    open_selected_dwg()
elif window.result == "reload_links":
    reload_links_from_selection()
