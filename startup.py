# -*- coding: utf-8 -*-
"""
CDY-ProTools Startup: Developer Panel lock state
- Ensures Developer panel and pyRevit tab are locked on first launch
- Handles ribbon timing issues in IronPython / Revit
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
    folder = os.path.dirname(UNLOCK_FILE)
    if not os.path.exists(folder):
        os.makedirs(folder)
    if not os.path.exists(UNLOCK_FILE):
        # First-time creation: not initialized
        f = open(UNLOCK_FILE, "w")
        json.dump({"unlocked": False, "initialized": False}, f)
        f.close()

def read_unlock_file():
    try:
        f = open(UNLOCK_FILE, "r")
        data = json.load(f)
        f.close()
        return data
    except:
        return {"unlocked": False, "initialized": False}

def save_unlock_file(data):
    f = open(UNLOCK_FILE, "w")
    json.dump(data, f)
    f.close()

# ---------------- Ribbon Utilities ---------------- #

def wait_for_ribbon(max_attempts=20, delay=0.5):
    """Wait until the ribbon is initialized with tabs."""
    for i in range(max_attempts):
        ribbon = AdWindows.ComponentManager.Ribbon
        if ribbon and ribbon.Tabs.Count > 0:
            return ribbon
        time.sleep(delay)
    return None

def get_ui_elements(ribbon):
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

def enforce_lock(dev_panel, pyrvt_tab, attempts=10, delay=0.3):
    """Repeatedly force Developer panel disabled and pyRevit hidden."""
    for i in range(attempts):
        if dev_panel:
            dev_panel.IsEnabled = False
            dev_panel.IsVisible = True  # panel always visible but disabled
        if pyrvt_tab:
            pyrvt_tab.IsVisible = False
        time.sleep(delay)

# ---------------- Main Logic ---------------- #

ensure_unlock_file_exists()
data = read_unlock_file()

ribbon = wait_for_ribbon()
if not ribbon:
    script.exit()

dev_panel, pyrvt_tab = get_ui_elements(ribbon)

# First launch: force lock
if not data.get("initialized", False):
    enforce_lock(dev_panel, pyrvt_tab)
    # Mark initialized so subsequent launches behave normally
    data["initialized"] = True
    save_unlock_file(data)
else:
    # Normal behavior: respect unlocked state
    unlocked = data.get("unlocked", False)
    if dev_panel:
        dev_panel.IsEnabled = unlocked
        dev_panel.IsVisible = True
    if pyrvt_tab:
        pyrvt_tab.IsVisible = unlocked
