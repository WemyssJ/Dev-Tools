# -*- coding: utf-8 -*-
"""
CDY-ProTools Toggle Toolbar Colors (UI via XAML)
Click a custom preview swatch to open the standard Windows color dialog (RGB).
Apply Custom Colors writes the chosen colors into each panel's bundle.yaml and saves them to CDY-ProToolsColors.ini.
"""

import os
import clr
import json

# --- ConfigParser compatibility for IronPython ---
try:
    import configparser  # Python 3
except ImportError:
    import ConfigParser as configparser  # Python 2 / IronPython

# WPF references
clr.AddReference("PresentationFramework")
clr.AddReference("WindowsBase")
clr.AddReference("PresentationCore")
clr.AddReference("System.Xaml")

# Windows Forms for ColorDialog
clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")

import System
from System.IO import FileStream, FileMode
from System.Windows.Markup import XamlReader
from System.Windows import Application, Thickness
from System.Windows.Controls import Grid, TextBlock
from System.Windows.Media import SolidColorBrush, Color, ColorConverter
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption
from System.Windows.Shapes import Rectangle

import System.Windows.Forms as WinForms
import System.Drawing as Drawing

from pyrevit import script, forms, EXEC_PARAMS
from pyrevit.loader import sessionmgr, sessioninfo

# --- Paths ---
EXT_PATH = os.path.join(
    os.getenv("APPDATA"),
    "pyRevit",
    "Extensions",
    "BIMTools.extension",
    "CDY-ProTools.tab"
)

CONFIG_PATH = os.path.join(os.getenv("APPDATA"), "pyRevit", "CDY-ProToolsColors.ini")

PANEL_ORDER = ["General", "Quality Assurance", "Model Management",
               "Drawing Tools", "References", "Developer"]

# --- Default Colors ---
PANEL_COLORS_LIGHT = {
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

PANEL_COLORS_DARK = {
    panel: {
        "panel": darken_hex_color_simple(colors["panel"]),
        "title": darken_hex_color_simple(colors["title"]),
        "slideout": darken_hex_color_simple(colors["slideout"])
    } for panel, colors in PANEL_COLORS_LIGHT.items()
}

# --- Load saved custom colors ---
PANEL_COLORS_CUSTOM = {panel: colors.copy() for panel, colors in PANEL_COLORS_LIGHT.items()}

def load_custom_colors():
    if os.path.exists(CONFIG_PATH):
        config = configparser.ConfigParser()
        config.read(CONFIG_PATH)
        section = "ToolbarColors"
        if config.has_section(section):
            for panel in PANEL_ORDER:
                if config.has_option(section, panel):
                    val = config.get(section, panel)
                    try:
                        PANEL_COLORS_CUSTOM[panel] = json.loads(val)
                    except:
                        pass

load_custom_colors()

def save_custom_colors():
    ini_dir = os.path.dirname(CONFIG_PATH)
    if not os.path.exists(ini_dir):
        os.makedirs(ini_dir)

    config = configparser.ConfigParser()
    section = "ToolbarColors"
    if os.path.exists(CONFIG_PATH):
        config.read(CONFIG_PATH)
    if not config.has_section(section):
        config.add_section(section)
    for panel, colors in PANEL_COLORS_CUSTOM.items():
        config.set(section, panel, json.dumps(colors))
    with open(CONFIG_PATH, "w") as f:
        config.write(f)

# --- Helpers ---
def rgb_to_hex(r, g, b):
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))
    return "{:02x}{:02x}{:02x}".format(r, g, b)

def colors_to_yaml_block(colors):
    return "\n".join([
        "background:",
        "  panel: '{}'".format(colors["panel"].strip()),
        "  title: '{}'".format(colors["title"].strip()),
        "  slideout: '{}'".format(colors["slideout"].strip())
    ])

def update_panel_yaml(panel_name, colors=None):
    yaml_file = os.path.join(EXT_PATH, panel_name + ".panel", "bundle.yaml")
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

def apply_colors(option):
    if option == "light":
        colors_dict = PANEL_COLORS_LIGHT
    elif option == "dark":
        colors_dict = PANEL_COLORS_DARK
    elif option == "custom":
        colors_dict = PANEL_COLORS_CUSTOM
        save_custom_colors()
    elif option == "none":
        colors_dict = None
    else:
        colors_dict = PANEL_COLORS_CUSTOM

    if colors_dict is None:
        for panel in PANEL_ORDER:
            update_panel_yaml(panel, None)
    else:
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
def add_panel_grid(container, colors_dict, dark_mode=False, custom_clickable=False):
    container.Children.Clear()
    grid = Grid()
    grid.Margin = Thickness(4,4,4,4)

    col_count = len(PANEL_ORDER) + 1
    for i in range(col_count):
        col = System.Windows.Controls.ColumnDefinition()
        col.Width = System.Windows.GridLength(120 if i>0 else 60)
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
        System.Windows.Controls.Grid.SetRow(tb,row_index)
        System.Windows.Controls.Grid.SetColumn(tb,0)
        grid.Children.Add(tb)

    for col_index, panel in enumerate(PANEL_ORDER,start=1):
        tb = TextBlock(
            Text=panel,
            HorizontalAlignment=System.Windows.HorizontalAlignment.Center,
            VerticalAlignment=System.Windows.VerticalAlignment.Center,
            FontWeight=System.Windows.FontWeights.Bold,
            Foreground=SolidColorBrush(Color.FromRgb(255,255,255) if dark_mode else Color.FromRgb(0,0,0))
        )
        System.Windows.Controls.Grid.SetRow(tb,0)
        System.Windows.Controls.Grid.SetColumn(tb,col_index)
        grid.Children.Add(tb)

        for row_index, key in enumerate(["panel","title","slideout"],start=1):
            rect = Rectangle()
            rect.Width = 100
            rect.Height = 25
            rect.RadiusX = 5
            rect.RadiusY = 5
            rect.Margin = Thickness(2,2,2,2)

            hex_color = colors_dict[panel][key]
            try:
                wpf_color = ColorConverter.ConvertFromString("#{}".format(hex_color))
                rect.Fill = SolidColorBrush(wpf_color)
            except:
                rect.Fill = SolidColorBrush(Color.FromRgb(220,220,220))

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
                def make_handler(rect_ref, p=panel, k=key):
                    def handler(sender, args):
                        dlg = WinForms.ColorDialog()
                        try:
                            hex_val = PANEL_COLORS_CUSTOM[p][k]
                            r = int(hex_val[0:2],16)
                            g = int(hex_val[2:4],16)
                            b = int(hex_val[4:6],16)
                            dlg.Color = Drawing.Color.FromArgb(r,g,b)
                        except:
                            pass
                        if dlg.ShowDialog() == WinForms.DialogResult.OK:
                            chosen = dlg.Color
                            PANEL_COLORS_CUSTOM[p][k] = rgb_to_hex(chosen.R, chosen.G, chosen.B)
                            rect_ref.Fill = SolidColorBrush(Color.FromRgb(chosen.R, chosen.G, chosen.B))
                    return handler
                overlay.MouseLeftButtonUp += make_handler(rect)

            System.Windows.Controls.Grid.SetRow(overlay,row_index)
            System.Windows.Controls.Grid.SetColumn(overlay,col_index)
            grid.Children.Add(overlay)

    container.Children.Add(grid)

# --- Containers ---
light_container = window.FindName("lightPreviewContainer")
dark_container  = window.FindName("darkPreviewContainer")
custom_container = window.FindName("customPreviewContainer")

add_panel_grid(light_container, PANEL_COLORS_LIGHT, dark_mode=False, custom_clickable=False)
add_panel_grid(dark_container, PANEL_COLORS_DARK, dark_mode=True, custom_clickable=False)
add_panel_grid(custom_container, PANEL_COLORS_CUSTOM, dark_mode=False, custom_clickable=True)

# --- Wire Buttons ---
btn_apply_custom = window.FindName("btnApplyCustom")
if btn_apply_custom:
    btn_apply_custom.Click += lambda s,e: (apply_colors("custom") or window.Close())

if window.FindName("btnLight"):
    window.FindName("btnLight").Click  += lambda s,e: (apply_colors("light") or window.Close())
if window.FindName("btnDark"):
    window.FindName("btnDark").Click   += lambda s,e: (apply_colors("dark") or window.Close())
if window.FindName("btnNone"):
    window.FindName("btnNone").Click   += lambda s,e: (apply_colors("none") or window.Close())

if window.FindName("closeBtn"):
    window.FindName("closeBtn").Click  += lambda s,e: window.Close()

# --- Show Window ---
app = Application.Current
if not app:
    app = Application()
window.ShowDialog()
