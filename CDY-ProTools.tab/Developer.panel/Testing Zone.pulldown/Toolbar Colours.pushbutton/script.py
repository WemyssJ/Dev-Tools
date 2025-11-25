# -*- coding: utf-8 -*-
"""
CDY-ProTools Toolbar Colours with Extension Selector
Allows customizing panel colors for any selected .extension.
Minimal fixes: replace missing forms.pick_color with WinForms ColorDialog
and sort panels according to .tab bundle order when available.

Added:
 - Persistent selected mode (light/dark/custom/none)
 - Highlight active button across sessions
 - Exclude any .panel or .extension located inside a "bin" folder
 - All custom color references normalized to lowercase
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
from System.Windows.Controls import StackPanel, TextBlock, Grid, Button
from System.Windows.Media import SolidColorBrush, Color, ColorConverter
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption
from System.Windows.Shapes import Rectangle
import System.Windows.Forms as WinForms
import System.Drawing as Drawing

from pyrevit import forms
from pyrevit import script, EXEC_PARAMS
from pyrevit.loader import sessionmgr, sessioninfo

# --- Config paths ---
EXT_ROOTS = [
    os.path.join(os.getenv("APPDATA"), "pyRevit", "Extensions"),
    os.path.join(os.getenv("APPDATA"), "pyRevit-Master", "extensions")
]
CONFIG_PATH = os.path.join(os.getenv("APPDATA"), "pyRevit", "ToolbarColors_config.ini")

# --- Persistent selected mode ---
SELECTED_MODE = None

def load_selected_mode():
    global SELECTED_MODE
    cfg = configparser.ConfigParser()
    if os.path.exists(CONFIG_PATH):
        cfg.read(CONFIG_PATH)
        if cfg.has_section("ToolbarColors"):
            if cfg.has_option("ToolbarColors", "SelectedMode"):
                SELECTED_MODE = cfg.get("ToolbarColors", "SelectedMode")
            else:
                SELECTED_MODE = None

def save_selected_mode(mode):
    global SELECTED_MODE
    SELECTED_MODE = mode
    cfg = configparser.ConfigParser()
    if os.path.exists(CONFIG_PATH):
        cfg.read(CONFIG_PATH)
    if not cfg.has_section("ToolbarColors"):
        cfg.add_section("ToolbarColors")
    cfg.set("ToolbarColors", "SelectedMode", mode)
    with open(CONFIG_PATH, "w") as f:
        cfg.write(f)

load_selected_mode()

# --- Button highlight logic ---
def highlight_buttons():
    """Highlights whichever mode is currently saved."""
    mode = SELECTED_MODE
    for name in ["btnLight", "btnDark", "btnCustom", "btnNone"]:
        btn = window.FindName(name)
        if not btn:
            continue
        if mode and name.lower().find(mode.lower()) != -1:
            btn.Background = SolidColorBrush(Color.FromRgb(200, 230, 255))
        else:
            try:
                btn.ClearValue(Button.BackgroundProperty)
            except:
                pass

# --- Panel order ---
PANEL_ORDER = ["General", "Quality Assurance", "Model Management",
               "Drawing Tools", "References", "Developer"]

# --- Default colors for BIMTools ---
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

# --- Custom colors dictionary ---
CUSTOM_COLORS = {}

def load_custom_colors():
    """
    Load saved custom colors from ToolbarColors_config.ini into CUSTOM_COLORS.
    All keys and hex values are normalized to lowercase for consistent lookup.
    """
    import ast
    global CUSTOM_COLORS
    CUSTOM_COLORS = {}
    if not os.path.exists(CONFIG_PATH):
        return
    config = configparser.RawConfigParser()
    config.optionxform = str
    config.read(CONFIG_PATH)
    section = "ToolbarColors"
    if config.has_section(section):
        for key in config.options(section):
            if key.lower() == "selectedmode":
                continue
            val_str = config.get(section, key).strip()
            try:
                raw_dict = ast.literal_eval(val_str)
                CUSTOM_COLORS[key.lower()] = {k: str(v).lower() for k, v in raw_dict.items()}
            except Exception as ex:
                print("Failed to parse key '{}': {}".format(key, ex))

def save_custom_colors():
    """
    Save CUSTOM_COLORS back to ToolbarColors_config.ini
    All hex values are written in lowercase.
    """
    cfg_dir = os.path.dirname(CONFIG_PATH)
    if cfg_dir and not os.path.exists(cfg_dir):
        os.makedirs(cfg_dir)
    config = configparser.RawConfigParser()
    config.optionxform = str
    section = "ToolbarColors"
    if not config.has_section(section):
        config.add_section(section)
    if SELECTED_MODE:
        config.set(section, "SelectedMode", SELECTED_MODE)
    for ext_panel, colors in CUSTOM_COLORS.items():
        colors_lower = {k: str(v).lower() for k, v in colors.items()}
        config.set(section, ext_panel, str(colors_lower))
    with open(CONFIG_PATH, "w") as f:
        config.write(f)

load_custom_colors()

# --- Helper functions ---
def rgb_to_hex(r, g, b):
    return "{:02x}{:02x}{:02x}".format(max(0, min(255, int(r))),
                                        max(0, min(255, int(g))),
                                        max(0, min(255, int(b))))

def colors_to_yaml_block(colors):
    block = ["background:"]
    for key in ["panel", "title", "slideout"]:
        val = colors.get(key, "f5f5f5").lower()
        if not isinstance(val, str) or len(val) != 6:
            val = "f5f5f5"
        block.append("  {}: '{}'".format(key, val))
    return "\n".join(block)

def update_panel_yaml(panel_path, colors=None):
    yaml_file = os.path.join(panel_path, "bundle.yaml")
    if not os.path.exists(yaml_file):
        script.get_logger().info("YAML not found: " + yaml_file)
        return
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
    if colors:
        new_lines.append(colors_to_yaml_block(colors))
    with open(yaml_file, "w") as f:
        f.write("\n".join(new_lines) + "\n")

def apply_colors(option, panels_list):
    global SELECTED_MODE
    selected_ext = ext_combo.SelectedItem.ToString() if ext_combo.SelectedItem else None
    if option in ["light", "dark", "custom", "none"]:
        save_selected_mode(option)
        highlight_buttons()
    if option == "light" and selected_ext:
        colors_dict = {selected_ext.lower() + "." + p.lower(): {k: v.lower() for k,v in DEFAULT_LIGHT[p].items()} for p in PANEL_ORDER}
    elif option == "dark" and selected_ext:
        colors_dict = {selected_ext.lower() + "." + p.lower(): {k: v.lower() for k,v in DEFAULT_DARK[p].items()} for p in PANEL_ORDER}
    elif option == "custom":
        colors_dict = CUSTOM_COLORS
        save_custom_colors()
    elif option == "none":
        colors_dict = None
    else:
        colors_dict = CUSTOM_COLORS

    for panel_path in panels_list:
        panel_name = os.path.basename(panel_path).replace(".panel", "").lower()
        ext_panel_key = (selected_ext.lower() + "." + panel_name) if selected_ext else panel_name
        if colors_dict is None:
            update_panel_yaml(panel_path, None)
        else:
            panel_colors = colors_dict.get(ext_panel_key, None)
            if panel_colors:
                update_panel_yaml(panel_path, panel_colors)

# --- Extension & panel utilities ---
def get_extensions():
    exts = []
    for root in EXT_ROOTS:
        if os.path.exists(root):
            for f in os.listdir(root):
                path = os.path.join(root, f)
                if f.lower().endswith(".extension") and "bin" not in path.lower():
                    exts.append(f)
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

# --- Load XAML ---
xaml_path = os.path.join(os.path.dirname(__file__), "ToolbarColors.xaml")
with FileStream(xaml_path, FileMode.Open) as fs:
    window = XamlReader.Load(fs)

# --- Load Logo ---
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

    # Header
    for row_index, label in enumerate(["", "Panel", "Title", "Slideout"]):
        tb = TextBlock(
            Text=label,
            HorizontalAlignment=System.Windows.HorizontalAlignment.Center,
            VerticalAlignment=System.Windows.VerticalAlignment.Center,
            FontWeight=System.Windows.FontWeights.Bold,
            Foreground=SolidColorBrush(Color.FromRgb(255, 255, 255) if dark_mode else Color.FromRgb(0, 0, 0))
        )
        System.Windows.Controls.Grid.SetRow(tb, row_index)
        System.Windows.Controls.Grid.SetColumn(tb, 0)
        grid.Children.Add(tb)

    selected_ext = ext_combo.SelectedItem.ToString().lower() if ext_combo.SelectedItem else ""

    for col_index, panel_path in enumerate(panels_list, start=1):
        panel_name = os.path.basename(panel_path).replace(".panel", "").lower()
        tb = TextBlock(
            Text=panel_name,
            HorizontalAlignment=System.Windows.HorizontalAlignment.Center,
            VerticalAlignment=System.Windows.VerticalAlignment.Center,
            FontWeight=System.Windows.FontWeights.Bold,
            Foreground=SolidColorBrush(Color.FromRgb(255, 255, 255) if dark_mode else Color.FromRgb(0, 0, 0))
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
            rect.Margin = Thickness(2, 2, 2, 2)

            ext_panel_key = selected_ext + "." + panel_name if selected_ext else panel_name
            hex_color = colors_dict.get(ext_panel_key, {}).get(key, "f5f5f5") if colors_dict else "f5f5f5"

            try:
                wpf_color = ColorConverter.ConvertFromString("#{}".format(hex_color.lower()))
                rect.Fill = SolidColorBrush(wpf_color)
            except:
                rect.Fill = SolidColorBrush(Color.FromRgb(245, 245, 245))

            tb_inner = TextBlock(
                Text=key.capitalize(),
                HorizontalAlignment=System.Windows.HorizontalAlignment.Center,
                VerticalAlignment=System.Windows.VerticalAlignment.Center,
                FontWeight=System.Windows.FontWeights.Bold,
                Foreground=SolidColorBrush(Color.FromRgb(255, 255, 255) if dark_mode else Color.FromRgb(0, 0, 0))
            )

            overlay = Grid()
            overlay.Children.Add(rect)
            overlay.Children.Add(tb_inner)

            if custom_clickable:
                def make_handler(rect_ref, p_name, k_name):
                    def handler(sender, args):
                        ext_panel_key_local = selected_ext + "." + p_name if selected_ext else p_name
                        current_hex = CUSTOM_COLORS.get(ext_panel_key_local, {"panel":"f5f5f5","title":"f5f5f5","slideout":"f5f5f5"}).get(k_name,"f5f5f5")
                        try:
                            r = int(current_hex[0:2],16)
                            g = int(current_hex[2:4],16)
                            b = int(current_hex[4:6],16)
                        except:
                            r, g, b = 245, 245, 245
                        dlg = WinForms.ColorDialog()
                        dlg.Color = Drawing.Color.FromArgb(r,g,b)
                        if dlg.ShowDialog() == WinForms.DialogResult.OK:
                            chosen = dlg.Color
                            if ext_panel_key_local not in CUSTOM_COLORS:
                                CUSTOM_COLORS[ext_panel_key_local] = {"panel":"f5f5f5","title":"f5f5f5","slideout":"f5f5f5"}
                            CUSTOM_COLORS[ext_panel_key_local][k_name] = rgb_to_hex(chosen.R, chosen.G, chosen.B).lower()
                            rect_ref.Fill = SolidColorBrush(Color.FromRgb(chosen.R, chosen.G, chosen.B))
                    return handler
                overlay.MouseLeftButtonUp += make_handler(rect, panel_name, key)

            System.Windows.Controls.Grid.SetRow(overlay, row_index)
            System.Windows.Controls.Grid.SetColumn(overlay, col_index)
            grid.Children.Add(overlay)

    container.Children.Add(grid)

# --- Containers ---
light_container = window.FindName("lightPreviewContainer")
dark_container = window.FindName("darkPreviewContainer")
custom_container = window.FindName("customPreviewContainer")
panel_container = window.FindName("panelGridContainer")
ext_combo = window.FindName("extensionComboBox")

# --- Populate extensions dropdown ---
extensions = get_extensions()
for ext in extensions:
    ext_combo.Items.Add(ext)

current_panels = []

def update_panels_for_extension(ext_name):
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

    # Show/hide light/dark buttons only for BIMTools
    if light_container is not None:
        light_container.Visibility = Visibility.Visible if is_bimtools else Visibility.Collapsed
    if dark_container is not None:
        dark_container.Visibility = Visibility.Visible if is_bimtools else Visibility.Collapsed
    if window.FindName("btnLight"):
        window.FindName("btnLight").Visibility = Visibility.Visible if is_bimtools else Visibility.Collapsed
    if window.FindName("btnDark"):
        window.FindName("btnDark").Visibility = Visibility.Visible if is_bimtools else Visibility.Collapsed

    if is_bimtools:
        selected_ext_lower = ext_name.lower()
        light_map = {selected_ext_lower + "." + k.lower(): {kk: vv.lower() for kk,vv in v.items()} for k,v in DEFAULT_LIGHT.items()}
        dark_map  = {selected_ext_lower + "." + k.lower(): {kk: vv.lower() for kk,vv in v.items()} for k,v in DEFAULT_DARK.items()}
        add_panel_grid(light_container, light_map, current_panels)
        add_panel_grid(dark_container, dark_map, current_panels, dark_mode=True)

    # Always show custom grid
    load_custom_colors()
    add_panel_grid(custom_container, CUSTOM_COLORS, current_panels, custom_clickable=True)

    highlight_buttons()

def on_ext_selection_changed(sender, args):
    if ext_combo.SelectedItem:
        update_panels_for_extension(ext_combo.SelectedItem.ToString())

ext_combo.SelectionChanged += on_ext_selection_changed

# --- Wire buttons ---
btn_apply_custom = window.FindName("btnCustom")
if btn_apply_custom:
    btn_apply_custom.Click += lambda s, e: apply_colors("custom", current_panels)
if window.FindName("btnLight"):
    window.FindName("btnLight").Click  += lambda s, e: apply_colors("light", current_panels)
if window.FindName("btnDark"):
    window.FindName("btnDark").Click   += lambda s, e: apply_colors("dark", current_panels)
if window.FindName("btnNone"):
    window.FindName("btnNone").Click   += lambda s, e: apply_colors("none", current_panels)

btn_reload = window.FindName("btnReloadPyRevit")
if btn_reload:
    def do_reload(sender, args):
        save_custom_colors()
        try:
            sessionmgr.reload_pyrevit()
        except:
            pass
        try:
            app.Current.MainWindow.Close()
        except:
            pass
    btn_reload.Click += do_reload

if window.FindName("closeBtn"):
    window.FindName("closeBtn").Click  += lambda s, e: window.Close()

# --- Set default selection ---
if "BIMTools.extension" in extensions:
    ext_combo.SelectedItem = "BIMTools.extension"
elif extensions:
    ext_combo.SelectedItem = extensions[0]

update_panels_for_extension(ext_combo.SelectedItem)

# --- Show Window ---
app = Application.Current
if not app:
    app = Application()
window.ShowDialog()
