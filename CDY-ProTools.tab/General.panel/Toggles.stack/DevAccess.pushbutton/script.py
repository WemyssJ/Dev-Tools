# -*- coding: utf-8 -*-
"""
DevAccess = WIP and potentially unstable/dangerous tools. 
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
PASSWORD = "password"  # Change this
XAML_FILE = "DeveloperUnlock.xaml"  # Your existing XAML window
UNLOCK_FILE = os.path.join(os.getenv("APPDATA"), "CDY-ProTools", "dev_unlock.json")
# ---------------------------------------- #

# ---------------- Ribbon Utilities ---------------- #
def get_ui_elements():
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

def save_unlock(state):
    folder = os.path.dirname(UNLOCK_FILE)
    if not os.path.exists(folder):
        os.makedirs(folder)
    with open(UNLOCK_FILE, "w") as f:
        json.dump({"unlocked": state}, f)

def is_unlocked():
    if os.path.exists(UNLOCK_FILE):
        try:
            with open(UNLOCK_FILE, "r") as f:
                return json.load(f).get("unlocked", False)
        except:
            return False
    return False

# ---------------- Main Logic ---------------- #
dev_panel, pyrvt_tab = get_ui_elements()
if not dev_panel:
    forms.alert("Developer panel not found.", title="Error")
    script.exit()

if is_unlocked():
    # Currently unlocked → relock immediately
    save_unlock(False)
    if dev_panel:
        dev_panel.IsVisible = False
        dev_panel.IsEnabled = False
    if pyrvt_tab:
        pyrvt_tab.IsVisible = False
    forms.alert("Developer panel relocked.", title="CDY-ProTools")
    script.exit()

# Currently locked → prompt for password
try:
    xaml_path = script.get_bundle_file(XAML_FILE)
    with open(xaml_path, 'r') as f:
        win = XamlReader.Parse(f.read())
except Exception as e:
    forms.alert("Failed to load password window:\n{}".format(e), title="Error")
    script.exit()

password_box = win.FindName("passwordBox")
okBtn = win.FindName("okBtn")
cancelBtn = win.FindName("cancelBtn")

def on_ok(sender, args):
    if password_box.Password == PASSWORD:
        save_unlock(True)
        if dev_panel:
            dev_panel.IsVisible = True
            dev_panel.IsEnabled = True
        if pyrvt_tab:
            pyrvt_tab.IsVisible = True
        win.Close()
        forms.alert("Developer panel unlocked.", title="CDY-ProTools")
    else:
        forms.alert("Incorrect password.", title="Access Denied")

def on_cancel(sender, args):
    win.Close()

okBtn.Click += on_ok
cancelBtn.Click += on_cancel

if isinstance(win, Window):
    win.Topmost = True
win.ShowDialog()
