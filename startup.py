# -*- coding: utf-8 -*-
"""
CDY-ProTools Startup: Hide Developer and pyRevit until unlocked
- Uses Idling event to ensure ribbon exists before hiding
"""

import clr
clr.AddReference('AdWindows')
import Autodesk.Windows as AdWindows
from pyrevit import HOST_APP, script
from Autodesk.Revit.UI.Events import IdlingEventArgs
from System import EventHandler
import os, json

TAB_NAME = "CDY-ProTools"
DEV_PANEL_NAME = "Developer"
PYRVT_TAB_NAME = "pyRevit"
UNLOCK_FILE = os.path.join(os.getenv("APPDATA"), "CDY-ProTools", "dev_unlock.json")

def hide_panels():
    ribbon = AdWindows.ComponentManager.Ribbon
    if not ribbon:
        return

    # Default: hide
    visible = False
    if os.path.exists(UNLOCK_FILE):
        try:
            with open(UNLOCK_FILE, "r") as f:
                data = json.load(f)
            if data.get("unlocked", False):
                visible = True
        except:
            visible = False

    # Hide or show Developer panel
    for tab in ribbon.Tabs:
        if tab.Title == TAB_NAME:
            for panel in tab.Panels:
                if panel.Source and panel.Source.Title == DEV_PANEL_NAME:
                    panel.IsVisible = visible
                    panel.IsEnabled = visible

        # Hide or show pyRevit tab
        if tab.Title == PYRVT_TAB_NAME:
            tab.IsVisible = visible

def on_idling(sender, args):
    try:
        hide_panels()
    except:
        pass
    finally:
        HOST_APP.uiapp.Idling -= EventHandler[IdlingEventArgs](on_idling)  # Unsubscribe after first run

# Hook Idling event safely
HOST_APP.uiapp.Idling += EventHandler[IdlingEventArgs](on_idling)
