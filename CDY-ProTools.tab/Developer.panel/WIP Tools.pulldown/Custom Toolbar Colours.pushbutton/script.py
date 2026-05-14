# -*- coding: utf-8 -*-
"""
CDY-ProTools Toolbar Colours with Extension Selector
Per-extension selectedmode, custom colours lowercased, BIMTools-only light/dark previews.
Includes full panel discovery, .tab ordering and bin exclusion.
Clicking a swatch sets the extension mode to 'custom' and updates preview + INI.
"""

import os
import re
import clr
try:
    import ConfigParser as configparser  # IronPython
except ImportError:
    import configparser

clr.AddReference("PresentationFramework")
clr.AddReference("WindowsBase")
clr.AddReference("PresentationCore")
clr.AddReference("System.Xaml")
clr.AddReference("System.Drawing")
clr.AddReference("System.Windows.Forms")

import System
from System.IO import FileStream, FileMode
from System.Windows.Markup import XamlReader
from System.Windows import Application, Thickness, Visibility
from System.Windows.Controls import TextBlock, Grid, Button
from System.Windows.Media import SolidColorBrush, Color, ColorConverter
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption
from System.Windows.Shapes import Rectangle
import System.Windows.Forms as WinForms
import System.Drawing as Drawing

from pyrevit import forms, script, EXEC_PARAMS
from pyrevit.loader import sessionmgr, sessioninfo

##############################################################################################
# TELEMETRY IMPORTS #
##############################################################################################
# Only works IF specified TELEMETRY_JSON path exists within %AppData%\pyRevit\Extensions\BIMTools.extension\lib\telemetry_auto.py"
# Records tool usage by date & revit version
import os, sys

# Add lib folder for telemetry_auto
lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'lib'))
if lib_path not in sys.path:
    sys.path.append(lib_path)

import telemetry_auto

tool_name = os.path.basename(os.path.dirname(__file__)) 
TOOL_NAME = tool_name.replace(".pushbutton", "")
telemetry_auto.log_tool_usage(TOOL_NAME)
##############################################################################################

# --- Config paths ---
EXT_ROOTS = [
    os.path.join(os.getenv("APPDATA"), "pyRevit", "Extensions"),
    os.path.join(os.getenv("APPDATA"), "pyRevit-Master", "extensions")
]
CONFIG_PATH = os.path.join(os.getenv("APPDATA"), "pyRevit", "ToolbarColors_config.ini")

# --- Per-extension modes and custom colors ---
EXT_MODES = {}       # ext_lower -> "light"/"dark"/"custom"/"none"
CUSTOM_COLORS = {}   # "ext.panel" (lower) -> {"panel":"xxxxxx","title":"xxxxxx","slideout":"xxxxxx"}

# --- Panel order & defaults ---
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

def darken_hex_color_simple(hex_color, amount=150):
    hex_color = hex_color.lstrip("#")
    r = max(0, int(hex_color[0:2], 16) - amount)
    g = max(0, int(hex_color[2:4], 16) - amount)
    b = max(0, int(hex_color[4:6], 16) - amount)
    return "{:02x}{:02x}{:02x}".format(r, g, b)

DEFAULT_DARK = {
    panel: {
        "panel": darken_hex_color_simple(colors["panel"]),
        "title": darken_hex_color_simple(colors["title"]),
        "slideout": darken_hex_color_simple(colors["slideout"])
    } for panel, colors in DEFAULT_LIGHT.items()
}

# --- Restore missing utilities (panel discovery, tab order, find_panels) ---
def get_extensions():
    exts = []
    for root in EXT_ROOTS:
        if os.path.exists(root):
            for item in os.listdir(root):
                path = os.path.join(root, item)
                if item.lower().endswith(".extension") and "bin" not in path.lower():
                    exts.append(item)
    return sorted(list(set(exts)))

def get_panel_order_from_tab(ext_path):
    try:
        for fname in os.listdir(ext_path):
            if fname.lower().endswith(".tab"):
                tab_path = os.path.join(ext_path, fname)
                try:
                    text = open(tab_path, "r").read()
                except:
                    continue
                found = re.findall(r'"([^"]+\.panel)"', text)
                ordered = []
                for full in found:
                    base = os.path.basename(full).replace(".panel", "")
                    if base not in ordered:
                        ordered.append(base)
                if ordered:
                    return ordered
    except:
        pass
    return list(PANEL_ORDER)

def find_panels(ext_path):
    panels = []
    for root, dirs, files in os.walk(ext_path):
        if "bin" in root.lower():
            continue
        for d in dirs:
            if d.endswith(".panel"):
                panels.append(os.path.join(root, d))
    order_list = get_panel_order_from_tab(ext_path)
    def panel_sort_key(p):
        name = os.path.basename(p).replace(".panel", "")
        if name in order_list:
            return order_list.index(name)
        try:
            return PANEL_ORDER.index(name)
        except ValueError:
            return 1000 + ord(name[0]) if name else 2000
    return sorted(panels, key=panel_sort_key)

# --- Config load/save (modes + custom colors) ---
def load_settings():
    import ast
    global EXT_MODES, CUSTOM_COLORS
    EXT_MODES = {}
    CUSTOM_COLORS = {}
    if not os.path.exists(CONFIG_PATH):
        return
    cfg = configparser.RawConfigParser()
    cfg.optionxform = str
    try:
        cfg.read(CONFIG_PATH)
    except:
        return
    section = "ToolbarColors"
    if not cfg.has_section(section):
        return
    for opt in cfg.options(section):
        opt_l = opt.lower().strip()
        val = cfg.get(section, opt).strip()
        if opt_l.endswith(".selectedmode"):
            ext = opt_l[:-len(".selectedmode")]
            EXT_MODES[ext] = val.lower()
            continue
        try:
            parsed = ast.literal_eval(val)
            if isinstance(parsed, dict):
                CUSTOM_COLORS[opt_l] = {k.lower(): str(v).lower() for k, v in parsed.items()}
        except Exception:
            pass

def save_settings():
    cfg = configparser.RawConfigParser()
    cfg.optionxform = str
    section = "ToolbarColors"
    if not cfg.has_section(section):
        cfg.add_section(section)
    for ext_l, mode in EXT_MODES.items():
        cfg.set(section, "{}.selectedmode".format(ext_l), mode)
    for ext_panel, colors in CUSTOM_COLORS.items():
        colors_write = {k: str(v).lower() for k, v in colors.items()}
        cfg.set(section, ext_panel, str(colors_write))
    cfg_dir = os.path.dirname(CONFIG_PATH)
    if cfg_dir and not os.path.exists(cfg_dir):
        try:
            os.makedirs(cfg_dir)
        except:
            pass
    with open(CONFIG_PATH, "w") as f:
        cfg.write(f)

# --- Misc helpers ---
def rgb_to_hex(r, g, b):
    return "{:02x}{:02x}{:02x}".format(max(0, min(255, int(r))),
                                        max(0, min(255, int(g))),
                                        max(0, min(255, int(b))))

def colors_to_yaml_block(colors):
    block = ["background:"]
    for key in ["panel", "title", "slideout"]:
        val = colors.get(key, "f5f5f5")
        if not isinstance(val, str) or len(val) != 6:
            val = "f5f5f5"
        block.append("  {}: '{}'".format(key, val))
    return "\n".join(block)

def read_panel_yaml(panel_path):
    """Return dict of colors stored in panel's bundle.yaml."""
    yaml_file = os.path.join(panel_path, "bundle.yaml")
    if not os.path.exists(yaml_file):
        return {"panel":"f5f5f5","title":"f5f5f5","slideout":"ffffff"}
    colors = {}
    with open(yaml_file, "r") as f:
        lines = f.readlines()
    bg_section = False
    for line in lines:
        if line.strip().startswith("background:"):
            bg_section = True
            continue
        if bg_section:
            m = re.match(r"\s*(panel|title|slideout):\s*'([0-9a-fA-F]{6})'", line)
            if m:
                colors[m.group(1).lower()] = m.group(2).lower()
            else:
                break
    return colors

def update_panel_yaml(panel_path, colors=None):
    """
    Updates or creates a bundle.yaml in the panel folder with the given colors.
    If colors is None, resets the background section.
    Compatible with IronPython (no exist_ok argument).
    """
    yaml_file = os.path.join(panel_path, "bundle.yaml")

    # If YAML doesn't exist, create minimal default
    if not os.path.exists(yaml_file):
        script.get_logger().info("YAML not found, creating: " + yaml_file)
        # create panel folder if it doesn't exist
        if not os.path.exists(panel_path):
            os.makedirs(panel_path)
        with open(yaml_file, "w") as f:
            f.write(
                "name: '{}'\nbackground:\n  panel: 'f5f5f5'\n  title: 'f5f5f5'\n  slideout: 'ffffff'\n".format(
                    os.path.basename(panel_path).replace(".panel", "")
                )
            )

    # Read existing YAML
    with open(yaml_file, "r") as f:
        lines = f.readlines()

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

    # Append updated colors
    if colors:
        new_lines.append(colors_to_yaml_block(colors))

    with open(yaml_file, "w") as f:
        f.write("\n".join(new_lines) + "\n")

# --- UI XAML load ---
xaml_path = os.path.join(os.path.dirname(__file__), "ToolbarColors.xaml")
with FileStream(xaml_path, FileMode.Open) as fs:
    window = XamlReader.Load(fs)

# load logo
logo_path = os.path.join(os.path.dirname(__file__), "icon.png")
header_icon = window.FindName("headerIcon")
if header_icon and os.path.exists(logo_path):
    bmp = BitmapImage()
    bmp.BeginInit()
    bmp.UriSource = System.Uri(logo_path)
    bmp.CacheOption = BitmapCacheOption.OnLoad
    bmp.EndInit()
    bmp.Freeze()
    header_icon.Source = bmp

# --- Highlight buttons for a given extension ---
def highlight_buttons_for(ext_name):
    mode = None
    if ext_name:
        mode = EXT_MODES.get(ext_name.lower(), None)
    for name in ["btnLight", "btnDark", "btnCustom", "btnNone"]:
        btn = window.FindName(name)
        if not btn:
            continue
        highlight = False
        if name.lower().find("custom") != -1:
            # highlight only if custom colors match YAML
            sel_ext = ext_name.lower()
            matched = True
            for panel_path in current_panels:
                panel_name = os.path.basename(panel_path).replace(".panel","").lower()
                ext_panel_key = sel_ext + "." + panel_name
                saved_yaml = read_panel_yaml(panel_path)
                current_custom = CUSTOM_COLORS.get(ext_panel_key, {})
                # compare keys
                for k in ["panel","title","slideout"]:
                    if current_custom.get(k,"") != saved_yaml.get(k,""):
                        matched = False
                        break
                if not matched:
                    break
            highlight = matched
        elif mode and name.lower().find(mode.lower()) != -1:
            highlight = True

        if highlight:
            btn.Background = SolidColorBrush(Color.FromRgb(200, 230, 255))
        else:
            try:
                btn.ClearValue(Button.BackgroundProperty)
            except:
                pass

# --- Panel Grid Preview ---
def add_panel_grid(container, colors_dict, panels_list, dark_mode=False, custom_clickable=False):
    container.Children.Clear()
    grid = Grid()
    grid.Margin = Thickness(4, 4, 4, 4)

    col_count = len(panels_list) + 1
    for i in range(col_count):
        col = System.Windows.Controls.ColumnDefinition()
        col.Width = System.Windows.GridLength(120 if i > 0 else 60)
        grid.ColumnDefinitions.Add(col)

    for r in range(4):
        row = System.Windows.Controls.RowDefinition()
        row.Height = System.Windows.GridLength(30)
        grid.RowDefinitions.Add(row)

    for row_index, label in enumerate(["", "Panel", "Title", "Slideout"]):
        tb = TextBlock(
            Text=label,
            HorizontalAlignment=System.Windows.HorizontalAlignment.Center,
            VerticalAlignment=System.Windows.VerticalAlignment.Center,
            FontWeight=System.Windows.FontWeights.Bold,
            Foreground=SolidColorBrush(Color.FromRgb(255,255,255) if dark_mode else Color.FromRgb(0,0,0))
        )
        System.Windows.Controls.Grid.SetRow(tb, row_index)
        System.Windows.Controls.Grid.SetColumn(tb, 0)
        grid.Children.Add(tb)

    selected_ext = ext_combo.SelectedItem.ToString().lower() if ext_combo and ext_combo.SelectedItem else ""

    for col_index, panel_path in enumerate(panels_list, start=1):
        panel_name = os.path.basename(panel_path).replace(".panel", "").lower()
        tb = TextBlock(
            Text=panel_name,
            HorizontalAlignment=System.Windows.HorizontalAlignment.Center,
            VerticalAlignment=System.Windows.VerticalAlignment.Center,
            FontWeight=System.Windows.FontWeights.Bold,
            Foreground=SolidColorBrush(Color.FromRgb(255,255,255) if dark_mode else Color.FromRgb(0,0,0))
        )
        System.Windows.Controls.Grid.SetRow(tb, 0)
        System.Windows.Controls.Grid.SetColumn(tb, col_index)
        grid.Children.Add(tb)

        for row_index, key in enumerate(["panel", "title", "slideout"], start=1):
            rect = Rectangle()
            rect.Width = 100
            rect.Height = 25
            rect.RadiusX = 5
            rect.RadiusY = 5
            rect.Margin = Thickness(2,2,2,2)

            ext_panel_key = (selected_ext + "." + panel_name) if selected_ext else panel_name
            ext_panel_key = ext_panel_key.lower()
            hex_color = colors_dict.get(ext_panel_key, {}).get(key, "f5f5f5") if colors_dict else "f5f5f5"

            try:
                wpf_color = ColorConverter.ConvertFromString("#{}".format(hex_color.lower()))
                rect.Fill = SolidColorBrush(wpf_color)
            except:
                rect.Fill = SolidColorBrush(Color.FromRgb(245,245,245))

            tb_inner = TextBlock(
                Text=key.capitalize(),
                HorizontalAlignment=System.Windows.HorizontalAlignment.Center,
                VerticalAlignment=System.Windows.VerticalAlignment.Center,
                FontWeight=System.Windows.FontWeights.Bold,
                Foreground=SolidColorBrush(Color.FromRgb(255,255,255) if dark_mode else Color.FromRgb(0,0,0))
            )

            overlay = Grid()
            overlay.Children.Add(rect)
            overlay.Children.Add(tb_inner)

            if custom_clickable:
                # capture p_name and k_name in defaults to avoid late-binding issues
                def make_handler(rect_ref, p_name=panel_name, k_name=key):
                    def handler(sender, args):
                        sel_ext = ext_combo.SelectedItem.ToString() if ext_combo and ext_combo.SelectedItem else ""
                        ext_panel_key_local = (sel_ext + "." + p_name).lower() if sel_ext else p_name.lower()
                        # get current hex (normalized)
                        current_hex = CUSTOM_COLORS.get(ext_panel_key_local, {"panel":"f5f5f5","title":"f5f5f5","slideout":"f5f5f5"}).get(k_name,"f5f5f5")
                        try:
                            r = int(current_hex[0:2], 16)
                            g = int(current_hex[2:4], 16)
                            b = int(current_hex[4:6], 16)
                        except:
                            r, g, b = 245, 245, 245
                        dlg = WinForms.ColorDialog()
                        try:
                            dlg.Color = Drawing.Color.FromArgb(r, g, b)
                        except:
                            pass
                        if dlg.ShowDialog() == WinForms.DialogResult.OK:
                            chosen = dlg.Color
                            # ensure entry exists
                            if ext_panel_key_local not in CUSTOM_COLORS:
                                CUSTOM_COLORS[ext_panel_key_local] = {"panel":"f5f5f5","title":"f5f5f5","slideout":"f5f5f5"}
                            CUSTOM_COLORS[ext_panel_key_local][k_name] = rgb_to_hex(chosen.R, chosen.G, chosen.B).lower()
                            # update rect fill immediately
                            rect_ref.Fill = SolidColorBrush(Color.FromRgb(chosen.R, chosen.G, chosen.B))
                            # set this extension's mode to custom and save (so UI highlights)
                            if sel_ext:
                                EXT_MODES[sel_ext.lower()] = "custom"
                                save_settings()
                                highlight_buttons_for(sel_ext)
                    return handler
                overlay.MouseLeftButtonUp += make_handler(rect)

            System.Windows.Controls.Grid.SetRow(overlay, row_index)
            System.Windows.Controls.Grid.SetColumn(overlay, col_index)
            grid.Children.Add(overlay)

    container.Children.Add(grid)

# --- Containers & combo references from XAML ---
light_container = window.FindName("lightPreviewContainer")
dark_container = window.FindName("darkPreviewContainer")
custom_container = window.FindName("customPreviewContainer")
panel_container = window.FindName("panelGridContainer")
ext_combo = window.FindName("extensionComboBox")

# --- Populate extensions dropdown (only those with panels) ---
if ext_combo:
    try:
        ext_combo.Items.Clear()
    except:
        pass

    extensions = []  # assign here so rest of script still sees it
    for ext in get_extensions():
        # find extension path
        ext_path = None
        for root in EXT_ROOTS:
            path = os.path.join(root, ext)
            if os.path.exists(path):
                ext_path = path
                break
        if not ext_path:
            continue

        panels = find_panels(ext_path)
        if panels:  # only include if there are panels
            extensions.append(ext)

    # add valid extensions to combo
    for ext in extensions:
        ext_combo.Items.Add(ext)

current_panels = []

# --- Apply colors per-extension ---
def apply_colors(option, panels_list):
    selected_ext = ext_combo.SelectedItem.ToString() if ext_combo and ext_combo.SelectedItem else None
    if not selected_ext:
        return
    ext_l = selected_ext.lower()

    # persist per-extension mode if relevant
    if option in ("light", "dark", "custom", "none"):
        EXT_MODES[ext_l] = option
        save_settings()
        highlight_buttons_for(selected_ext)

    # construct colors_dict (keys lowercased)
    if option == "light":
        colors_dict = { (ext_l + "." + p.lower()): {k: v.lower() for k,v in DEFAULT_LIGHT[p].items()} for p in PANEL_ORDER }
    elif option == "dark":
        colors_dict = { (ext_l + "." + p.lower()): {k: v.lower() for k,v in DEFAULT_DARK[p].items()} for p in PANEL_ORDER }
    elif option == "custom":
        colors_dict = CUSTOM_COLORS
        save_settings()
    elif option == "none":
        colors_dict = None
    else:
        colors_dict = CUSTOM_COLORS

    for panel_path in panels_list:
        panel_name = os.path.basename(panel_path).replace(".panel", "").lower()
        ext_panel_key = ext_l + "." + panel_name if ext_l else panel_name
        if colors_dict is None:
            update_panel_yaml(panel_path, None)
        else:
            panel_colors = colors_dict.get(ext_panel_key, None)
            if panel_colors:
                update_panel_yaml(panel_path, panel_colors)

# --- Update panels for selected extension ---
def update_panels_for_extension(ext_name):
    """
    Updates the panel previews and mode buttons for the selected extension.
    Light/Dark mode grids are only visible for BIMTools.extension.
    Custom grid is always shown.
    """
    global current_panels

    ext_path = None
    for root in EXT_ROOTS:
        path = os.path.join(root, ext_name)
        if os.path.exists(path):
            ext_path = path
            break

    if not ext_path:
        current_panels = []
        return

    current_panels = find_panels(ext_path)
    is_bimtools = ext_name.lower() == "bimtools.extension"

    # --- Light/Dark Buttons ---
    for btn_name in ["btnLight", "btnDark"]:
        btn = window.FindName(btn_name)
        if btn is not None:
            btn.Visibility = Visibility.Visible if is_bimtools else Visibility.Collapsed

    # --- Light/Dark ScrollViewers ---
    for sv_name in ["lightScrollViewer", "darkScrollViewer"]:
        sv = window.FindName(sv_name)
        if sv is not None:
            if is_bimtools:
                sv.Visibility = Visibility.Visible
                sv.Height = 140
            else:
                sv.Visibility = Visibility.Collapsed
                sv.Height = 0

    # --- Populate Light/Dark Previews (only for BIMTools) ---
    if is_bimtools:
        sel_l = ext_name.lower()
        light_map = { sel_l + "." + p.lower(): {k: v.lower() for k, v in DEFAULT_LIGHT[p].items()} for p in PANEL_ORDER }
        dark_map  = { sel_l + "." + p.lower(): {k: v.lower() for k, v in DEFAULT_DARK[p].items()}  for p in PANEL_ORDER }

        if light_container is not None:
            add_panel_grid(light_container, light_map, current_panels)
        if dark_container is not None:
            add_panel_grid(dark_container, dark_map, current_panels, dark_mode=True)

    # --- Always show Custom Grid ---
    add_panel_grid(custom_container, CUSTOM_COLORS, current_panels, custom_clickable=True)

    # --- Highlight the buttons according to stored mode for this extension ---
    highlight_buttons_for(ext_name)

# --- Handlers wiring ---
def on_ext_selection_changed(sender, args):
    if ext_combo.SelectedItem:
        # reload settings (in case INI changed externally) and refresh UI
        load_settings()
        update_panels_for_extension(ext_combo.SelectedItem.ToString())

if ext_combo:
    ext_combo.SelectionChanged += on_ext_selection_changed

# wire mode buttons
if window.FindName("btnLight"):
    window.FindName("btnLight").Click += lambda s,e: (apply_colors("light", current_panels) or None)
if window.FindName("btnDark"):
    window.FindName("btnDark").Click  += lambda s,e: (apply_colors("dark", current_panels) or None)
if window.FindName("btnCustom"):
    window.FindName("btnCustom").Click += lambda s,e: (apply_colors("custom", current_panels) or None)
if window.FindName("btnNone"):
    window.FindName("btnNone").Click  += lambda s,e: (apply_colors("none", current_panels) or None)

# --- Reset Custom Colours Button ---
btn_reset = window.FindName("btnResetCustom")
if btn_reset:
    def reset_custom_colors(sender, args):
        sel_ext = ext_combo.SelectedItem.ToString() if ext_combo and ext_combo.SelectedItem else None
        if not sel_ext:
            return

        ext_l = sel_ext.lower()
        # confirm reset with user
        dlg = WinForms.MessageBox.Show(
            "This will remove all custom colours for '{}'. Are you sure?".format(sel_ext),
            "Reset Custom Colours",
            WinForms.MessageBoxButtons.YesNo,
            WinForms.MessageBoxIcon.Warning
        )
        if dlg != WinForms.DialogResult.Yes:
            return

        # delete all custom colors for this extension
        keys_to_remove = [k for k in CUSTOM_COLORS.keys() if k.startswith(ext_l + ".")]
        for k in keys_to_remove:
            del CUSTOM_COLORS[k]

        # NOTE: Do NOT change EXT_MODES[ext_l] here
        # This ensures the current mode highlight remains intact
        save_settings()

        # refresh custom preview grid only
        add_panel_grid(custom_container, CUSTOM_COLORS, current_panels, custom_clickable=True)

    btn_reset.Click += reset_custom_colors


# reload/save buttons
btn_reload = window.FindName("btnReloadPyRevit")
if btn_reload:
    def do_reload(sender, args):
        save_settings()
        try:
            sessionmgr.reload_pyrevit()
        except:
            pass
        try:
            app.Current.MainWindow.Close()
        except:
            pass
    btn_reload.Click += do_reload

# close
if window.FindName("closeBtn"):
    window.FindName("closeBtn").Click += lambda s,e: window.Close()

# --- default selection + initial refresh ---
if ext_combo:
    if "BIMTools.extension" in extensions:
        ext_combo.SelectedItem = "BIMTools.extension"
    elif extensions:
        ext_combo.SelectedItem = extensions[0]

if ext_combo and ext_combo.SelectedItem:
    # load settings then refresh UI so previous session selection is shown
    load_settings()
    update_panels_for_extension(ext_combo.SelectedItem.ToString())

# show dialog
app = Application.Current
if not app:
    app = Application()
window.ShowDialog()
