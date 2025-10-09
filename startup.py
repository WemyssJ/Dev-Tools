# -*- coding: utf-8 -*-
"""
CDY-ProTools Startup: Developer Panel lock state
- Ensures Developer panel and pyRevit tab are correctly locked/unlocked on Revit launch
- Works even on first launch with IronPython 2.7
"""

import clr
clr.AddReference('AdWindows')
import Autodesk.Windows as AdWindows
import os, json, time
from pyrevit import script

TAB_NAME = "CDY-ProTools"
DEV_PANEL_NAME = "Developer"
PYRVT_TAB_NAME = "pyRevit"
UNLOCK_FILE = os.path.join(os.getenv("APPDATA"), "CDY-ProTools", "dev_unlock.json")


# ---------------- File Utilities ---------------- #

def ensure_unlock_file_exists():
    """Create the unlock file with default locked state if missing."""
    folder = os.path.dirname(UNLOCK_FILE)
    if not os.path.exists(folder):
        os.makedirs(folder)
    if not os.path.exists(UNLOCK_FILE):
        f = open(UNLOCK_FILE, "w")
        json.dump({"unlocked": False}, f)
        f.close()


def is_unlocked():
    """Return True if developer panel is unlocked."""
    try:
        f = open(UNLOCK_FILE, "r")
        data = json.load(f)
        f.close()
        return data.get("unlocked", False)
    except Exception:
        return False


# ---------------- Ribbon Utilities ---------------- #

def wait_for_ribbon(max_attempts=20, delay=0.5):
    """Wait until the ribbon object is initialized with tabs."""
    ribbon = None
    for i in range(max_attempts):
        ribbon = AdWindows.ComponentManager.Ribbon
        if ribbon and ribbon.Tabs.Count > 0:
            return ribbon
        time.sleep(delay)
    return None


def get_ui_elements(ribbon):
    """Get Developer panel and pyRevit tab from the ribbon."""
    dev_panel, pyrvt_tab = None, None
    for tab in ribbon.Tabs:
        if tab.Title == TAB_NAME:
            for panel in tab.Panels:
                if panel.Source and panel.Source.Title == DEV_PANEL_NAME:
                    dev_panel = panel
                    break
        elif tab.Title == PYRVT_TAB_NAME:
            pyrvt_tab = tab
    return dev_panel, pyrvt_tab


def update_dev_panel_state():
    """Apply lock state to Developer panel and pyRevit tab."""
    ribbon = wait_for_ribbon()
    if not ribbon:
        # Ribbon never initialized; exit safely
        script.exit()

    dev_panel, pyrvt_tab = get_ui_elements(ribbon)
    unlocked = is_unlocked()

    # Developer panel: always visible, enabled only if unlocked
    if dev_panel:
        dev_panel.IsEnabled = unlocked
        dev_panel.IsVisible = True

    # pyRevit tab: visible only if unlocked
    if pyrvt_tab:
        pyrvt_tab.IsVisible = unlocked


# ---------------- MAIN ---------------- #

# Ensure the unlock file exists first
ensure_unlock_file_exists()

# Apply lock state to ribbon panels
update_dev_panel_state()
