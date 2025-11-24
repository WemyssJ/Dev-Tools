# -*- coding: utf-8 -*-
"""
CDY-ProTools Toggle Toolbar Colors
- Works in IronPython 2.7 / PyRevit 5
- Adds/removes background colors in panel YAMLs
- Reloads pyRevit using standard safe reload logic
"""

import os
from pyrevit import script, forms, EXEC_PARAMS
clr = __import__('clr')
from pyrevit.loader import sessionmgr, sessioninfo

# --- Config ---
EXT_PATH = os.path.join(
    os.getenv("APPDATA"),
    "pyRevit",
    "Extensions",
    "BIMTools.extension",
    "CDY-ProTools.tab"
)

# Colors to apply for each panel
PANEL_COLORS = {
    "General": {"panel": "fffbfb", "title": "fff3f3", "slideout": "ffffff"},
    "Quality Assurance": {"panel": "fbfffb", "title": "f3fff3", "slideout": "ffffff"},
    "Model Management": {"panel": "fefbff", "title": "fef3ff", "slideout": "ffffff"},
    "Drawing Tools": {"panel": "fbffff", "title": "f3ffff", "slideout": "ffffff"},
    "References": {"panel": "fffffb", "title": "fefff3", "slideout": "ffffff"},
    "Developer": {"panel": "f5f5f5", "title": "ededed", "slideout": "ffffff"}
}

# State file location (safe folder)
STATE_FOLDER = os.path.join(os.getenv("APPDATA"), "CDY-ProTools")
if not os.path.exists(STATE_FOLDER):
    os.makedirs(STATE_FOLDER)
STATE_FILE = os.path.join(STATE_FOLDER, "color_toggle_state.txt")

# --- Helper Functions ---
def colors_to_yaml_block(colors):
    """Convert a color dict to a YAML text block"""
    lines = [
        "background:",
        "  panel: '" + colors["panel"] + "'",
        "  title: '" + colors["title"] + "'",
        "  slideout: '" + colors["slideout"] + "'"
    ]
    return "\n".join(lines)

def update_panel_yaml(panel_name, apply_colors=True):
    """Add or remove background block in YAML as text"""
    yaml_file = os.path.join(EXT_PATH, panel_name + ".panel", "bundle.yaml")
    if not os.path.exists(yaml_file):
        script.get_logger().info("YAML not found: " + yaml_file)
        return

    # Read YAML as text
    with open(yaml_file, "r") as f:
        lines = f.readlines()

    # Remove existing background block
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

    # Add background if applying colors
    if apply_colors:
        new_lines.append(colors_to_yaml_block(PANEL_COLORS[panel_name]))

    # Write YAML back
    with open(yaml_file, "w") as f:
        f.write("\n".join(new_lines) + "\n")

# --- Main ---
# Determine toggle state (applied or removed)
apply_colors = True
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        state = f.read().strip()
    apply_colors = state != "applied"

# Update all panels
for panel_name in PANEL_COLORS:
    update_panel_yaml(panel_name, apply_colors=apply_colors)

# Save new state
with open(STATE_FILE, "w") as f:
    f.write("applied" if apply_colors else "removed")

# --- Reload pyRevit safely ---
res = True
if EXEC_PARAMS.executed_from_ui:
    res = forms.alert('Reloading increases the memory footprint and is '
                      'automatically called by pyRevit when necessary.\n\n'
                      'pyRevit developers can manually reload when:\n'
                      '    - New buttons are added.\n'
                      '    - Buttons have been removed.\n'
                      '    - Button icons have changed.\n'
                      '    - Base C# code has changed.\n'
                      '    - Value of pyRevit parameters\n'
                      '      (e.g. __title__, __doc__, ...) have changed.\n'
                      '    - Cached engines need to be cleared.\n\n'
                      'Are you sure you want to reload?',
                      ok=False, yes=True, no=True)

if res:
    logger = script.get_logger()
    results = script.get_results()

    # re-load pyrevit session.
    logger.info('Reloading....')
    sessionmgr.reload_pyrevit()

    results.newsession = sessioninfo.get_session_uuid()

script.get_logger().info("CDY-ProTools toolbar colors " + ("applied" if apply_colors else "removed") + ".")
