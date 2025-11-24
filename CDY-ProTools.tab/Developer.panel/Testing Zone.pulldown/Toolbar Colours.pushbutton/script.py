# -*- coding: utf-8 -*-
"""
CDY-ProTools Toggle Toolbar Colors (UI via XAML)
Displays previews for all panels in light/dark modes in a grid layout.
"""

import os
import clr

clr.AddReference("PresentationFramework")
clr.AddReference("WindowsBase")
clr.AddReference("PresentationCore")
clr.AddReference("System.Xaml")

import System
from System.IO import FileStream, FileMode
from System.Windows.Markup import XamlReader
from System.Windows import Application, Thickness, HorizontalAlignment, VerticalAlignment
from System.Windows.Controls import StackPanel, TextBlock, Grid
from System.Windows.Media import SolidColorBrush, Color
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption
from System.Windows.Shapes import Rectangle

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

PANEL_ORDER = ["General", "Quality Assurance", "Model Management",
               "Drawing Tools", "References", "Developer"]

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

# --- YAML update functions ---
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
    else:
        colors_dict = {k: {"panel":"ffffff","title":"ffffff","slideout":"ffffff"} for k in PANEL_ORDER}

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

# --- Add panel grid previews ---
def add_panel_grid(container, colors_dict, dark_mode=False):
    grid = Grid()
    grid.Margin = Thickness(4, 4, 4, 4)

    # Columns: first for row labels + one per panel
    col_count = len(PANEL_ORDER) + 1
    for i in range(col_count):
        col = System.Windows.Controls.ColumnDefinition()
        col.Width = System.Windows.GridLength(120 if i > 0 else 60)
        grid.ColumnDefinitions.Add(col)

    # Rows: 1 header + 3 for Panel / Title / Slideout
    for r in range(4):
        row = System.Windows.Controls.RowDefinition()
        row.Height = System.Windows.GridLength(30)
        grid.RowDefinitions.Add(row)

    # Row labels
    for row_index, label in enumerate(["", "Panel", "Title", "Slideout"]):
        tb = TextBlock(
            Text=label,
            HorizontalAlignment=HorizontalAlignment.Center,
            VerticalAlignment=VerticalAlignment.Center,
            FontWeight=System.Windows.FontWeights.Bold,
            Foreground=SolidColorBrush(Color.FromRgb(255, 255, 255) if dark_mode else Color.FromRgb(0, 0, 0))
        )
        Grid.SetRow(tb, row_index)
        Grid.SetColumn(tb, 0)
        grid.Children.Add(tb)

    # Fill headers and color boxes
    for col_index, panel in enumerate(PANEL_ORDER, start=1):
        # Panel header
        tb = TextBlock(
            Text=panel,
            HorizontalAlignment=HorizontalAlignment.Center,
            VerticalAlignment=VerticalAlignment.Center,
            FontWeight=System.Windows.FontWeights.Bold,
            Foreground=SolidColorBrush(Color.FromRgb(255, 255, 255) if dark_mode else Color.FromRgb(0, 0, 0))
        )
        Grid.SetRow(tb, 0)
        Grid.SetColumn(tb, col_index)
        grid.Children.Add(tb)

        # Color boxes with bold inner text
        for row_index, key in enumerate(["panel", "title", "slideout"], start=1):
            rect = Rectangle()
            rect.Width = 100
            rect.Height = 25
            rect.RadiusX = 5
            rect.RadiusY = 5
            rect.Margin = Thickness(2, 2, 2, 2)
            color_hex = colors_dict[panel][key]
            c = Color.FromRgb(
                int(color_hex[0:2], 16),
                int(color_hex[2:4], 16),
                int(color_hex[4:6], 16)
            )
            rect.Fill = SolidColorBrush(c)

            tb_inner = TextBlock(
                Text=key.capitalize(),
                HorizontalAlignment=HorizontalAlignment.Center,
                VerticalAlignment=VerticalAlignment.Center,
                FontWeight=System.Windows.FontWeights.Bold,  # bold
                Foreground=SolidColorBrush(
                    Color.FromRgb(255, 255, 255) if dark_mode else Color.FromRgb(0, 0, 0)
                )
            )

            grid_overlay = Grid()
            grid_overlay.Children.Add(rect)
            grid_overlay.Children.Add(tb_inner)

            Grid.SetRow(grid_overlay, row_index)
            Grid.SetColumn(grid_overlay, col_index)
            grid.Children.Add(grid_overlay)

    container.Children.Add(grid)


# --- Containers in XAML ---
light_container = window.FindName("lightPreviewContainer")
dark_container  = window.FindName("darkPreviewContainer")
# none_container  = window.FindName("nonePreviewContainer")  # removed completely

# Add previews only for light and dark modes
add_panel_grid(light_container, PANEL_COLORS_LIGHT, dark_mode=False)
add_panel_grid(dark_container, PANEL_COLORS_DARK, dark_mode=True)

# --- Bind Buttons ---
window.FindName("btnLight").Click += lambda s,e: apply_colors("light") or window.Close()
window.FindName("btnDark").Click  += lambda s,e: apply_colors("dark")  or window.Close()
window.FindName("btnNone").Click  += lambda s,e: apply_colors("none")  or window.Close()  # button still works

# --- Show Window ---
app = Application.Current
if not app:
    app = Application()
window.ShowDialog()
