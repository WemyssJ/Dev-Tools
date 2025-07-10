# -*- coding: utf-8 -*-
"""
Checks GitHub for update.
Clones a panel to the Modify tab when a document is opened.
Shows a popup listing DevTools panels on startup.
Hides the "Other" panel for unauthorized users.
"""
# --- Imports ---
import clr
clr.AddReference('AdWindows')
import Autodesk.Windows as AdWindows
clr.AddReference('System.Windows.Forms')
from System.Windows.Forms import SendKeys

from pyrevit import HOST_APP, forms
from pyrevit.coreutils import logger
from System import EventHandler
from Autodesk.Revit.UI.Events import IdlingEventArgs
from Autodesk.Revit.DB import Events

import os
import core

# --- Flags ---
DEBUG_UI = False               # Toggle detailed UI debug output
already_hooked = False         # Ensure idling is hooked only once

# --- User Info ---
windows_username = os.getenv('USERNAME')
revit_username = HOST_APP.username

# --- Logger ---
script_logger = logger.get_logger('switchback_api')

# --- Check for updates ---
try:
    if core.update_needed():
        forms.toaster.send_toast("New update for DevTools extension available: {}".format(core.get_git_version()))
except Exception:
    pass


def find_and_clone_target_panel1():
    ribbon = AdWindows.ComponentManager.Ribbon
    if not ribbon:
        return

    target_tab = next((tab for tab in ribbon.Tabs 
                      if tab.Title == "Modify" and tab.IsVisible), None)
    if not target_tab:
        return

    source_panel = None
    for tab in ribbon.Tabs:
        if not tab.IsVisible:
            continue
        for panel in tab.Panels:
            if panel.Source and panel.Source.Title == "Test Button":
                source_panel = panel
                break
        if source_panel:
            break

    if not source_panel:
        return

    if any(panel.Source and panel.Source.Title == source_panel.Source.Title 
           for panel in target_tab.Panels):
        return

    target_tab.Panels.Add(AdWindows.RibbonPanel())
    new_panel = target_tab.Panels[target_tab.Panels.Count - 1]
    new_panel.Source = source_panel.Source.Clone()
    new_panel.IsEnabled = True


def Hidden_Panel():
    authorized_users = ["joe.wemyss", "james.scrivens", "andrew.owen"]

    ribbon = AdWindows.ComponentManager.Ribbon
    HiddenPanel = "Developer"
    if not ribbon:
        return

    for tab in ribbon.Tabs:
        if tab.Title == "DevTools" and tab.IsVisible:
            for panel in tab.Panels:
                if panel.Source and panel.Source.Title == HiddenPanel:
                    if revit_username not in authorized_users:
                        panel.IsVisible = False
                        panel.IsEnabled = False
                        script_logger.info("Unloading {} panel for {}".format(HiddenPanel, revit_username))
                    else:
                        script_logger.info("Loading {} panel for {}".format(HiddenPanel, revit_username))
                    return


def debug_list_panels_ui():
    ribbon = AdWindows.ComponentManager.Ribbon
    if not ribbon:
        script_logger.info("Ribbon not found")
        return

    for tab in ribbon.Tabs:
        if tab.Title == "DevTools":
            msg = "DevTools tab found, Visible={}\n\nPanels:\n".format(tab.IsVisible)
            for panel in tab.Panels:
                title = panel.Source.Title if panel.Source else "<No Source>"
                msg += " - '{}' Visible={}\n".format(title, panel.IsVisible)
            script_logger.info(msg)
            return
    script_logger.info("DevTools tab not found")


def on_idling(sender, args):
    try:
        if DEBUG_UI:
            debug_list_panels_ui()  # Show popup with panel info
        Hidden_Panel()              # Hide the Other panel if needed
    except Exception as e:
        script_logger.info("Error during panel debug or hiding:\n{}".format(str(e)))
    HOST_APP.uiapp.Idling -= on_idling  # Unsubscribe after running once


# --- Initial clone on startup ---
find_and_clone_target_panel1()

# --- Hook the idling event only once ---
global already_hooked
if not already_hooked:
    HOST_APP.uiapp.Idling += EventHandler[IdlingEventArgs](on_idling)
    already_hooked = True

# --- Also run clone on document opening ---
def doc_opening_handler(sender, args):
    find_and_clone_target_panel1()

HOST_APP.app.DocumentOpening += EventHandler[Events.DocumentOpeningEventArgs](doc_opening_handler)
