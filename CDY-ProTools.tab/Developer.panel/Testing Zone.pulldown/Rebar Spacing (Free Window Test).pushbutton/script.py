# -*- coding: utf-8 -*-

import clr
import math

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


uidoc = revit.uidoc


# ----------------------------
# External Event Handler
# ----------------------------

class MeasureHandler(IExternalEventHandler):

    def __init__(self):
        self.spacing_box = None
        self.result_distance = None
        self.result_bars = None
        self.result_rounded = None

    def Execute(self, uiapp):

        try:
            spacing_mm = float(self.spacing_box.Text)
        except:
            self.result_distance.Text = "Invalid spacing"
            return

        try:
            p1 = uidoc.Selection.PickPoint(ObjectSnapTypes.Endpoints, "Pick first point")
            p2 = uidoc.Selection.PickPoint(ObjectSnapTypes.Endpoints, "Pick second point")
        except:
            return

        dist_internal = p1.DistanceTo(p2)

        dist_mm = UnitUtils.ConvertFromInternalUnits(dist_internal, UnitTypeId.Millimeters)

        bars = dist_mm / spacing_mm

        rounded_qty = int(math.ceil(bars)) + 1

        self.result_distance.Text = "Distance: {:.0f} mm".format(dist_mm)
        self.result_bars.Text = "Bars: {:.2f}".format(bars)
        self.result_rounded.Text = "Rounded Qty: {}".format(rounded_qty)

    def GetName(self):
        return "Spacing Measure Handler"


handler = MeasureHandler()
ext_event = ExternalEvent.Create(handler)


# ----------------------------
# Modeless Window
# ----------------------------

class SpacingWindow(Window):

    def __init__(self):

        self.Title = "Spacing Calculator"
        self.Width = 260
        self.Height = 200
        self.Topmost = True

        stack = StackPanel()
        stack.Margin = Thickness(10)

        stack.Children.Add(TextBlock(Text="Spacing (mm):"))

        self.spacing = TextBox()
        self.spacing.Text = "200"
        stack.Children.Add(self.spacing)

        self.measure_btn = Button(Content="Measure")
        self.measure_btn.Margin = Thickness(0,10,0,10)
        stack.Children.Add(self.measure_btn)

        self.distance = TextBlock(Text="Distance:")
        stack.Children.Add(self.distance)

        self.bars = TextBlock(Text="Bars:")
        stack.Children.Add(self.bars)

        self.rounded = TextBlock(Text="Rounded Qty:")
        self.rounded.FontWeight = FontWeights.Bold
        self.rounded.Foreground = Brushes.Red
        stack.Children.Add(self.rounded)

        self.Content = stack

        handler.spacing_box = self.spacing
        handler.result_distance = self.distance
        handler.result_bars = self.bars
        handler.result_rounded = self.rounded

        self.measure_btn.Click += self.measure_click

    def measure_click(self, sender, args):
        ext_event.Raise()


# ----------------------------
# Launch Window
# ----------------------------

win = SpacingWindow()
win.Show()