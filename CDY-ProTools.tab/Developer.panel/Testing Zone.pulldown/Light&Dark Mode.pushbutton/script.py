# -*- coding: utf-8 -*-
"""
Quick apply BIMTools toolbar colors to match Revit theme.
Reloads PyRevit only if colors actually change.
No UI.
"""

import os, clr
clr.AddReference("RevitAPIUI")
from Autodesk.Revit.UI import UIThemeManager, UITheme

from pyrevit import script
from pyrevit.loader import sessionmgr

# --- Paths & constants ---
EXT_ROOT = os.path.join(os.getenv("APPDATA"), "pyRevit", "Extensions", "BIMTools.extension")
PANEL_ORDER = ["General", "Quality Assurance", "Model Management",
               "Drawing Tools", "References", "Developer"]

DEFAULT_LIGHT = {
    "General": {"panel": "fffbfb", "title": "fff3f3", "slideout": "ffffff"},
    "Quality Assurance": {"panel": "fbfffb", "title": "f3fff3", "slideout": "ffffff"},
    "Model Management": {"panel": "fefbff", "title": "fef3ff", "slideout": "ffffff"},
    "Drawing Tools": {"panel": "fbffff", "title": "f3ffff", "slideout": "ffffff"},
    "References": {"panel": "fffffb", "title": "fefff3", "slideout": "ffffff"},
    "Developer": {"panel": "f5f5f5", "title": "ededed", "slideout": "ffffff"}
}

def darken(hex_color, amount=150):
    hex_color = hex_color.lstrip("#")
    r = max(0, int(hex_color[0:2],16)-amount)
    g = max(0, int(hex_color[2:4],16)-amount)
    b = max(0, int(hex_color[4:6],16)-amount)
    return "{:02x}{:02x}{:02x}".format(r,g,b)

DEFAULT_DARK = {p: {k: darken(v) for k,v in colors.items()} for p,colors in DEFAULT_LIGHT.items()}

# --- Find all panels ---
def find_panels(ext_root):
    panels = []
    for root, dirs, files in os.walk(ext_root):
        for d in dirs:
            if d.endswith(".panel"):
                panels.append(os.path.join(root,d))
    return panels

# --- Read existing panel colors ---
def read_panel_colors(panel_path):
    yaml_file = os.path.join(panel_path,"bundle.yaml")
    colors = {}
    if os.path.exists(yaml_file):
        with open(yaml_file,"r") as f:
            bg_section=False
            for line in f:
                if line.strip().startswith("background:"):
                    bg_section=True
                    continue
                if bg_section:
                    m = line.strip().split(":")
                    if len(m)==2:
                        colors[m[0].strip()] = m[1].strip().strip("'")
    return colors

# --- Update bundle.yaml ---
def update_panel_yaml(panel_path, colors):
    yaml_file = os.path.join(panel_path,"bundle.yaml")
    lines = []
    if os.path.exists(yaml_file):
        with open(yaml_file,"r") as f:
            skip=False
            for l in f:
                if l.strip().startswith("background:"): skip=True; continue
                if skip and (l.startswith(" ") or l.startswith("\t")): continue
                skip=False
                lines.append(l.rstrip("\n"))
    else:
        os.makedirs(panel_path, exist_ok=True)
        lines.append("name: '{}'".format(os.path.basename(panel_path).replace(".panel","")))
    lines.append("background:")
    for k,v in colors.items():
        lines.append("  {}: '{}'".format(k,v))
    with open(yaml_file,"w") as f:
        f.write("\n".join(lines)+"\n")

# --- Determine Revit theme ---
theme = UIThemeManager.CurrentTheme
is_dark_theme = theme==UITheme.Dark
print("Revit theme detected:", "Dark" if is_dark_theme else "Light")
target_palette = DEFAULT_DARK if is_dark_theme else DEFAULT_LIGHT

# --- Apply to all panels only if different ---
panels_changed = False
for panel_path in find_panels(EXT_ROOT):
    panel_name = os.path.basename(panel_path).replace(".panel","")
    target_colors = target_palette.get(panel_name, target_palette["General"])
    current_colors = read_panel_colors(panel_path)
    if current_colors != target_colors:
        update_panel_yaml(panel_path, target_colors)
        panels_changed = True

if panels_changed:
    print("BIMTools panel colors updated to match Revit theme.")
    try:
        sessionmgr.reload_pyrevit()
        print("PyRevit reloaded to apply new colors.")
    except Exception as e:
        print("Could not reload PyRevit:", e)
else:
    print("Toolbar already matches Revit theme — no reload needed.")
