# -*- coding: utf-8 -*-
"""
CDY-ProTools Startup: Hide Developer and pyRevit until unlocked
- Uses Idling event to ensure ribbon exists before hiding
"""

import clr
clr.AddReference('AdWindows')
import Autodesk.Windows as AdWindows
from pyrevit import HOST_APP, script
from Autodesk.Revit.UI.Events import IdlingEventArgs
from System import EventHandler
import os, json

TAB_NAME = "CDY-ProTools"
DEV_PANEL_NAME = "Developer"
PYRVT_TAB_NAME = "pyRevit"
UNLOCK_FILE = os.path.join(os.getenv("APPDATA"), "CDY-ProTools", "dev_unlock.json")

def hide_panels():
    ribbon = AdWindows.ComponentManager.Ribbon
    if not ribbon:
        return

    # Default: hide
    visible = False
    if os.path.exists(UNLOCK_FILE):
        try:
            with open(UNLOCK_FILE, "r") as f:
                data = json.load(f)
            if data.get("unlocked", False):
                visible = True
        except:
            visible = False

    # Hide or show Developer panel
    for tab in ribbon.Tabs:
        if tab.Title == TAB_NAME:
            for panel in tab.Panels:
                if panel.Source and panel.Source.Title == DEV_PANEL_NAME:
                    panel.IsVisible = visible
                    panel.IsEnabled = visible

        # Hide or show pyRevit tab
        if tab.Title == PYRVT_TAB_NAME:
            tab.IsVisible = visible

def on_idling(sender, args):
    try:
        hide_panels()
    except:
        pass
    finally:
        HOST_APP.uiapp.Idling -= EventHandler[IdlingEventArgs](on_idling)  # Unsubscribe after first run

# Hook Idling event safely
HOST_APP.uiapp.Idling += EventHandler[IdlingEventArgs](on_idling)

# =============================================================================
# Dockable Panel - Spacing Calculator
# =============================================================================

import clr
import math
import datetime
import os.path as op

clr.AddReference("PresentationFramework")
clr.AddReference("PresentationCore")
clr.AddReference("WindowsBase")

from System.Windows import Window, Thickness, FontWeights
from System.Windows.Controls import StackPanel, TextBox, Button, TextBlock
from System.Windows.Media import Brushes

from Autodesk.Revit.UI import IExternalEventHandler, ExternalEvent
from Autodesk.Revit.DB import UnitUtils, UnitTypeId
from Autodesk.Revit.UI.Selection import ObjectSnapTypes

from pyrevit import revit
from pyrevit import forms


# ----------------------------
# External Event Handler
# ----------------------------

class MeasureHandler(IExternalEventHandler):

    def __init__(self):
        self.spacing_box = None
        self.cover_box = None
        self.result_distance = None
        self.result_bars = None
        self.result_rounded = None
        self.console = None
        self.last_result = ""

    def Execute(self, uiapp):
        uidoc = uiapp.ActiveUIDocument
        if not uidoc:
            return

        # --- parse spacing ---
        try:
            spacing_mm = float(self.spacing_box.Text)
            if spacing_mm <= 0:
                raise ValueError("spacing must be > 0")
        except Exception as e:
            self.result_distance.Text = "Invalid spacing: {}".format(e)
            return

        # --- parse cover ---
        try:
            cover_mm = float(self.cover_box.Text)
        except:
            cover_mm = 50.0

        # --- pick points ---
        try:
            p1 = uidoc.Selection.PickPoint(ObjectSnapTypes.Endpoints, "Pick first point")
            p2 = uidoc.Selection.PickPoint(ObjectSnapTypes.Endpoints, "Pick second point")
        except:
            self.result_distance.Text = "Cancelled"
            return

        # --- calculate ---
        dist_internal = p1.DistanceTo(p2)
        dist_mm = UnitUtils.ConvertFromInternalUnits(dist_internal, UnitTypeId.Millimeters)
        net_mm = dist_mm - (2 * cover_mm)
        bars = net_mm / spacing_mm
        rounded_up = int(math.ceil(bars)) + 1

        # --- update results ---
        self.result_distance.Text = "Distance: {:.0f} mm  (net: {:.0f} mm)".format(dist_mm, net_mm)
        self.result_bars.Text = "Bars: {:.2f}".format(bars)
        self.result_rounded.Text = "Rounded Qty: {}".format(rounded_up)

        # --- build history entry ---
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        result_str = "[{}] {:.0f}mm @ {}mm spacing  →  {} bars".format(
            timestamp, dist_mm, int(spacing_mm), rounded_up)

        self.last_result = result_str

        # --- update console ---
        if self.console is not None:
            existing = self.console.Text
            self.console.Text = result_str + ("\n" + existing if existing else "")

    def GetName(self):
        return "Spacing Measure Handler"


handler = MeasureHandler()
ext_event = ExternalEvent.Create(handler)


# ----------------------------
# Find Xaml
# ----------------------------
def find_file(filename, search_root):
    for root, dirs, files in os.walk(search_root):
        if filename in files:
            return op.join(root, filename)
    return None

_tab_root = op.join(op.dirname(__file__), "CDY-ProTools.tab")
_xaml_path = find_file("RebarSpacingCalculator.xaml", _tab_root)


# ----------------------------
# Dockable Panel
# ----------------------------

class RebarSpacingCalculator(forms.WPFPanel):
    panel_title = "Rebar Spacing Calculator"
    panel_id = "3110e336-f81c-4927-87da-4e0d30d4d64b"
    panel_source = _xaml_path

    def SetupDockablePane(self, data):
        data.FrameworkElement = self
        data.VisibleByDefault = False

    def __init__(self):
        super(RebarSpacingCalculator, self).__init__()
        handler.spacing_box     = self.spacingBox
        handler.cover_box       = self.coverBox
        handler.result_distance = self.distanceText
        handler.result_bars     = self.barsText
        handler.result_rounded  = self.roundedText
        handler.console         = self.consoleText

    def measureBtn_Click(self, sender, args):
        ext_event.Raise()

    def clearBtn_Click(self, sender, args):
        self.consoleText.Text = ""
        handler.last_result = ""


# ----------------------------
# Register panel
# ----------------------------

if not forms.is_registered_dockable_panel(RebarSpacingCalculator):
    forms.register_dockable_panel(RebarSpacingCalculator)
else:
    print("Skipped registering dockable pane. Already exists.")