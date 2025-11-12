# -*- coding: utf-8 -*-
# Link Options – colourful one-click buttons

import os
import subprocess
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.UI.Selection import ObjectType
from pyrevit import revit, DB, forms, script
from System import Uri
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption

logger = script.get_logger()
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

# --------------------------
# Load WPF UI from separate file
# --------------------------
script_dir = os.path.dirname(__file__)
xaml_path = os.path.join(script_dir, "LinkOptions.xaml")
if not os.path.exists(xaml_path):
    forms.alert("Could not find LinkOptions.xaml in script folder.", exitscript=True)


window = forms.WPFWindow(xaml_path)

icon_path = os.path.join(script_dir, "icon.png")
if os.path.exists(icon_path):
    bmp = BitmapImage()
    bmp.BeginInit()
    bmp.UriSource = Uri(icon_path)
    bmp.CacheOption = BitmapCacheOption.OnLoad
    bmp.EndInit()
    window.FindName("headerIcon").Source = bmp

# --------------------------
# Helper Functions
# --------------------------
def pick_single_element(prompt="Select an element"):
    """Prompt user to pick one element; hides WPF window for selection."""
    try:
        window.Hide()
        ref = uidoc.Selection.PickObject(ObjectType.Element, prompt)
        if ref:
            return doc.GetElement(ref.ElementId)
    except:
        # User cancelled — reopen window
        TaskDialog.Show("Cancelled", "Selection cancelled.")
        window.Show()
        return None
    return None

def open_dwg_safe(path):
    if path and os.path.exists(path):
        try:
            subprocess.Popen(['acad.exe', path])
        except Exception:
            os.startfile(path)
        TaskDialog.Show("DWG Opened", "DWG successfully opened:\n\n{}".format(path))
    else:
        TaskDialog.Show("DWG Not Found", "The DWG path does not exist:\n\n{}".format(path))

# --------------------------
# Event Handlers
# --------------------------
def open_selected_dwg(sender, args):
    sel_ids = uidoc.Selection.GetElementIds()
    elem = None

    if sel_ids:
        elem = doc.GetElement(list(sel_ids)[0])
    else:
        # ✅ If nothing selected, just prompt silently
        elem = pick_single_element("Pick a linked DWG")
        if not elem:
            return  # user cancelled

    if not isinstance(elem, ImportInstance):
        forms.alert("Selected element is not a linked DWG (ImportInstance).")
        return

    import_symbol = doc.GetElement(elem.GetTypeId())
    efr = ExternalFileUtils.GetExternalFileReference(doc, import_symbol.Id)
    if not efr:
        forms.alert("No external file reference found for this DWG.")
        return

    dwg_path = ModelPathUtils.ConvertModelPathToUserVisiblePath(efr.GetAbsolutePath())
    open_dwg_safe(dwg_path)

    # ✅ Close WPF window after operation completes
    window.Close()

def reload_links_from_selection(sender, args):
    selection = revit.get_selection()

    # ✅ If nothing selected, just pick silently
    if not selection or len(selection) == 0:
        picked_elem = pick_single_element("Pick a Revit or CAD link to reload")
        if not picked_elem:
            return  # user cancelled
        selection = [picked_elem]

    revit_links = []
    cad_links = []

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

    if not revit_links and not cad_links:
        forms.alert("No valid Revit or CAD links found in your selection.")
        return

    # Reload Revit links
    if revit_links:
        reload_locally = False
        if doc.IsWorkshared:
            reload_locally = forms.alert(
                'Reload links locally without affecting other users?',
                title='Reload locally?',
                yes=True, no=True
            )
        for xref in revit_links:
            try:
                if reload_locally:
                    if not xref.link.LocallyUnloaded:
                        xref.link.UnloadLocally(None)
                    xref.link.RevertLocalUnloadStatus()
                else:
                    xref.reload()
            except Exception as e:
                logger.debug("Error reloading Revit link: {}".format(e))

    # Reload CAD links
    if cad_links:
        with revit.Transaction('Reload CAD Links'):
            for xref in cad_links:
                try:
                    xref.reload()
                except Exception as e:
                    logger.debug("Error reloading CAD link: {}".format(e))

    print("Reload completed.")
    # ✅ Close WPF window after operation
    window.Close()

def cancel(sender, args):
    window.Close()

# --------------------------
# Connect buttons
# --------------------------
window.btnOpenDWG.Click += open_selected_dwg
window.btnReloadLinks.Click += reload_links_from_selection
window.cancelBtn.Click += cancel

# --------------------------
# Show Dialog
# --------------------------
window.ShowDialog()
