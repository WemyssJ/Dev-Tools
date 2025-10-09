# -*- coding: utf-8 -*-
"""
CDY-ProTools Startup: Developer Panel lock state
- Enables/disables Developer panel and pyRevit tab on Revit launch
"""

import clr
clr.AddReference('AdWindows')
import Autodesk.Windows as AdWindows
import os, json

TAB_NAME = "CDY-ProTools"
DEV_PANEL_NAME = "Developer"
PYRVT_TAB_NAME = "pyRevit"
UNLOCK_FILE = os.path.join(os.getenv("APPDATA"), "CDY-ProTools", "dev_unlock.json")


def is_unlocked():
    """Return True if developer panel is unlocked (file may not exist)."""
    if not os.path.exists(UNLOCK_FILE):
        # Ensure file exists for first-time startup
        folder = os.path.dirname(UNLOCK_FILE)
        if not os.path.exists(folder):
            os.makedirs(folder)
        with open(UNLOCK_FILE, "w") as f:
            json.dump({"unlocked": False}, f)
        return False
    try:
        with open(UNLOCK_FILE, "r") as f:
            data = json.load(f)
        return data.get("unlocked", False)
    except Exception:
        return False


def update_dev_panel_state():
    """Apply lock state to UI panels."""
    ribbon = AdWindows.ComponentManager.Ribbon
    if not ribbon:
        return

    dev_panel = None
    pyrvt_tab = None

    for tab in ribbon.Tabs:
        if tab.Title == TAB_NAME:
            for panel in tab.Panels:
                if panel.Source and panel.Source.Title == DEV_PANEL_NAME:
                    dev_panel = panel
                    break
        elif tab.Title == PYRVT_TAB_NAME:
            pyrvt_tab = tab

    unlocked = is_unlocked()

    # Apply Developer panel state
    if dev_panel:
        dev_panel.IsEnabled = unlocked
        dev_panel.IsVisible = True  # panel is always visible, just disabled if locked

    # Hide pyRevit tab when locked
    if pyrvt_tab:
        pyrvt_tab.IsVisible = unlocked  # visible only when unlocked


# Execute on load
update_dev_panel_state()
