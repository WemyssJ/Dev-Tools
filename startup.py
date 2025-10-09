# -*- coding: utf-8 -*-
"""
CDY-ProTools Startup: Developer Panel lock state
- Ensures Developer panel and pyRevit tab are correctly locked/unlocked on Revit launch
"""

import clr
clr.AddReference('AdWindows')
import Autodesk.Windows as AdWindows
import os, json

TAB_NAME = "CDY-ProTools"
DEV_PANEL_NAME = "Developer"
PYRVT_TAB_NAME = "pyRevit"
UNLOCK_FILE = os.path.join(os.getenv("APPDATA"), "CDY-ProTools", "dev_unlock.json")


def ensure_unlock_file_exists():
    """Create the unlock file with default locked state if missing."""
    folder = os.path.dirname(UNLOCK_FILE)
    if not os.path.exists(folder):
        os.makedirs(folder)
    if not os.path.exists(UNLOCK_FILE):
        with open(UNLOCK_FILE, "w") as f:
            json.dump({"unlocked": False}, f)


def is_unlocked():
    """Return True if developer panel is unlocked."""
    try:
        with open(UNLOCK_FILE, "r") as f:
            return json.load(f).get("unlocked", False)
    except Exception:
        return False


def update_dev_panel_state():
    """Apply lock state to Developer panel and pyRevit tab."""
    ribbon = AdWindows.ComponentManager.Ribbon
    if not ribbon:
        return

    dev_panel, pyrvt_tab = None, None
    for tab in ribbon.Tabs:
        if tab.Title == TAB_NAME:
            for panel in tab.Panels:
                if panel.Source and panel.Source.Title == DEV_PANEL_NAME:
                    dev_panel = panel
                    break
        elif tab.Title == PYRVT_TAB_NAME:
            pyrvt_tab = tab

    unlocked = is_unlocked()

    # Developer panel: visible but enabled only if unlocked
    if dev_panel:
        dev_panel.IsEnabled = unlocked
        dev_panel.IsVisible = True

    # pyRevit tab: visible only if unlocked
    if pyrvt_tab:
        pyrvt_tab.IsVisible = unlocked


# --- Ensure file exists before touching UI ---
ensure_unlock_file_exists()

# --- Apply panel/tab state ---
update_dev_panel_state()
