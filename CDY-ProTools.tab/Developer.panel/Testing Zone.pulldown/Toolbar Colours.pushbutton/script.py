# -*- coding: utf-8 -*-
"""
CDY-ProTools Toggle Toolbar Colors (UI via XAML)
- Nothing runs until a button is pressed
"""

import os
import clr

clr.AddReference("PresentationFramework")
clr.AddReference("WindowsBase")
clr.AddReference("System.Xaml")

from System.IO import FileStream, FileMode
from System.Windows.Markup import XamlReader
from System.Windows import Application
from System import Uri
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption

from pyrevit import script, forms, EXEC_PARAMS
from pyrevit.loader import sessionmgr, sessioninfo


# --- Config ---
EXT_PATH = os.path.join(
    os.getenv("APPDATA"),
    "pyRevit",
    "Extensions",
    "BIMTools.extension",
    "CDY-ProTools.tab"
)

PANEL_COLORS_LIGHT = {
    "General": {"panel": "fffbfb", "title": "fff3f3", "slideout": "ffffff"},
    "Quality Assurance": {"panel": "fbfffb", "title": "f3fff3", "slideout": "ffffff"},
    "Model Management": {"panel": "fefbff", "title": "fef3ff", "slideout": "ffffff"},
    "Drawing Tools": {"panel": "fbffff", "title": "f3ffff", "slideout": "ffffff"},
    "References": {"panel": "fffffb", "title": "fefff3", "slideout": "ffffff"},
    "Developer": {"panel": "f5f5f5", "title": "ededed", "slideout": "ffffff"}
}


# --- Helpers ---
def darken_hex_color_simple(hex_color, amount=150):
    """Subtract fixed value from RGB channels to make darker."""
    hex_color = hex_color.lstrip("#")
    r = max(0, int(hex_color[0:2], 16) - amount)
    g = max(0, int(hex_color[2:4], 16) - amount)
    b = max(0, int(hex_color[4:6], 16) - amount)
    return "{:02x}{:02x}{:02x}".format(r, g, b)


# Dark mode colors generated from light mode
PANEL_COLORS_DARK = {
    panel: {
        "panel": darken_hex_color_simple(colors["panel"]),
        "title": darken_hex_color_simple(colors["title"]),
        "slideout": darken_hex_color_simple(colors["slideout"])
    }
    for panel, colors in PANEL_COLORS_LIGHT.items()
}


def colors_to_yaml_block(colors):
    lines = [
        "background:",
        "  panel: '{}'".format(colors["panel"]),
        "  title: '{}'".format(colors["title"]),
        "  slideout: '{}'".format(colors["slideout"])
    ]
    return "\n".join(lines)


def update_panel_yaml(panel_name, colors=None):
    yaml_file = os.path.join(EXT_PATH, panel_name + ".panel", "bundle.yaml")
    if not os.path.exists(yaml_file):
        script.get_logger().info("YAML not found: " + yaml_file)
        return

    with open(yaml_file, "r") as f:
        lines = f.readlines()

    # Remove existing background: block
    new_lines = []
    skip = False
    for line in lines:
        if line.strip().startswith("background:"):
            skip = True
            continue
        if skip:
            if line.startswith(" ") or line.startswith("\t"):
                continue
            else:
                skip = False
        new_lines.append(line.rstrip("\n"))

    # Add block if specified
    if colors:
        new_lines.append(colors_to_yaml_block(colors))

    with open(yaml_file, "w") as f:
        f.write("\n".join(new_lines) + "\n")


def apply_colors(option):
    """Apply light, dark, or none → then reload."""
    if option == "light":
        colors_dict = PANEL_COLORS_LIGHT
    elif option == "dark":
        colors_dict = PANEL_COLORS_DARK
    else:  # none
        colors_dict = {k: None for k in PANEL_COLORS_LIGHT}

    for panel in colors_dict:
        update_panel_yaml(panel, colors_dict[panel])

    if EXEC_PARAMS.executed_from_ui:
        res = forms.alert(
            "Colors updated! PyRevit needs to reload to apply changes.",
            ok=False, yes=True, no=True
        )
        if res:
            logger = script.get_logger()
            results = script.get_results()
            logger.info("Reloading PyRevit...")
            sessionmgr.reload_pyrevit()
            results.newsession = sessioninfo.get_session_uuid()


# --- Load XAML Window ---
xaml_path = os.path.join(os.path.dirname(__file__), "ToolbarColors.xaml")
with FileStream(xaml_path, FileMode.Open) as fs:
    window = XamlReader.Load(fs)


# --- Load Logo into headerIcon ---
logo_path = os.path.join(os.path.dirname(__file__), "icon.png")
if os.path.exists(logo_path):
    bmp = BitmapImage()
    bmp.BeginInit()
    bmp.UriSource = Uri(logo_path)
    bmp.CacheOption = BitmapCacheOption.OnLoad
    bmp.EndInit()

    header_icon = window.FindName("headerIcon")
    if header_icon:
        header_icon.Source = bmp


# --- Bind Buttons ---
window.FindName("btnLight").Click += lambda s, e: apply_colors("light") or window.Close()
window.FindName("btnDark").Click += lambda s, e: apply_colors("dark") or window.Close()
window.FindName("btnNone").Click += lambda s, e: apply_colors("none") or window.Close()


# --- Show Window ---
app = Application.Current
if not app:
    app = Application()

window.ShowDialog()
