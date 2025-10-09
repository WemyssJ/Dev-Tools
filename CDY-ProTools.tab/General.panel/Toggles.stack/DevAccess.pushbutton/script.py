# -*- coding: utf-8 -*-
"""
PushButton: (Un)Lock Developer Panel
"""

import clr
clr.AddReference('PresentationFramework')
clr.AddReference('WindowsBase')
clr.AddReference('System.Xaml')
clr.AddReference('AdWindows')

import Autodesk.Windows as AdWindows
from pyrevit import forms, script
from System.Windows.Markup import XamlReader
from System.Windows import Window
import os, json

# ---------------- CONFIG ---------------- #
TAB_NAME = "CDY-ProTools"
DEV_PANEL_NAME = "Developer"
PYRVT_TAB_NAME = "pyRevit"
PASSWORD = "password"  # change this
XAML_FILE = "DeveloperUnlock.xaml"
UNLOCK_FILE = os.path.join(os.getenv("APPDATA"), "CDY-ProTools", "dev_unlock.json")
# ---------------------------------------- #

# --- Ensure unlock file exists ---
folder = os.path.dirname(UNLOCK_FILE)
if not os.path.exists(folder):
    os.makedirs(folder)
if not os.path.exists(UNLOCK_FILE):
    with open(UNLOCK_FILE, "w") as f:
        json.dump({"unlocked": False}, f)


def is_unlocked():
    try:
        with open(UNLOCK_FILE, "r") as f:
            return json.load(f).get("unlocked", False)
    except Exception:
        return False


def save_unlock(state: bool):
    with open(UNLOCK_FILE, "w") as f:
        json.dump({"unlocked": state}, f)


def get_ui_elements():
    """Get Developer panel and pyRevit tab from the ribbon."""
    ribbon = AdWindows.ComponentManager.Ribbon
    if not ribbon:
        return None, None

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


def load_xaml_window(xaml_file):
    """Loads the XAML file as a WPF window."""
    from pyrevit import script
    xaml_path = script.get_bundle_file(xaml_file)
    with open(xaml_path, 'r') as f:
        xaml_str = f.read()
    return XamlReader.Parse(xaml_str)


# ---------------- MAIN ---------------- #

dev_panel, pyrvt_tab = get_ui_elements()

if not dev_panel:
    forms.alert("Developer panel not found in CDY-ProTools tab.", title="Error")
    script.exit()

unlocked = is_unlocked()

if unlocked:
    # --- Relock ---
    save_unlock(False)
    dev_panel.IsEnabled = False
    if pyrvt_tab:
        pyrvt_tab.IsVisible = False
    forms.alert("LOCKED", title="CDY-ProTools")
    script.exit()

# --- Unlock (with password) ---
try:
    win = load_xaml_window(XAML_FILE)
except Exception as e:
    forms.alert("Failed to load password window:\n{}".format(e), title="Error")
    script.exit()

password_box = win.FindName("passwordBox")
okBtn = win.FindName("okBtn")
cancelBtn = win.FindName("cancelBtn")


def on_ok(sender, args):
    if password_box.Password == PASSWORD:
        save_unlock(True)
        dev_panel.IsEnabled = True
        if pyrvt_tab:
            pyrvt_tab.IsVisible = True
        win.Close()
    else:
        forms.alert("Incorrect password.", title="Access Denied")


def on_cancel(sender, args):
    win.Close()


okBtn.Click += on_ok
cancelBtn.Click += on_cancel

if isinstance(win, Window):
    win.Topmost = True

win.ShowDialog()
