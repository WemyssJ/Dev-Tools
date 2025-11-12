# -*- coding: utf-8 -*-
"""
Align Text Notes (Left / Centre / Right)
Pretty modern WPF version with buttons
"""

from Autodesk.Revit.DB import TextNote, HorizontalTextAlignment, FilteredElementCollector, Transaction
from pyrevit import revit, forms
import clr, os
from System import Uri
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption

doc = revit.doc
uidoc = revit.uidoc

clr.AddReference('PresentationFramework')
clr.AddReference('PresentationCore')
clr.AddReference('WindowsBase')
from System.Windows import Window

# -------------------- Gather TextNotes --------------------
sel_ids = list(uidoc.Selection.GetElementIds())
textnotes = []

if sel_ids:
    for elid in sel_ids:
        el = doc.GetElement(elid)
        if isinstance(el, TextNote):
            textnotes.append(el)
else:
    collector = FilteredElementCollector(doc, doc.ActiveView.Id).OfClass(TextNote)
    textnotes = list(collector)
    if not textnotes:
        forms.alert("No Text Notes found in this view.", exitscript=True)

# -------------------- Load WPF UI --------------------
HERE = os.path.dirname(__file__)
XAMLFILE = os.path.join(HERE, "AlignTextNotes.xaml")
dlg = forms.WPFWindow(XAMLFILE)

icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
if os.path.exists(icon_path):
    bmp = BitmapImage()
    bmp.BeginInit()
    bmp.UriSource = Uri(icon_path)
    bmp.CacheOption = BitmapCacheOption.OnLoad
    bmp.EndInit()
    dlg.FindName("headerIcon").Source = bmp


# Buttons
left_btn = dlg.leftBtn
centre_btn = dlg.centreBtn
right_btn = dlg.rightBtn
cancel_btn = dlg.cancelBtn

alignment_map = {
    "Left": HorizontalTextAlignment.Left,
    "Centre": HorizontalTextAlignment.Center,
    "Right": HorizontalTextAlignment.Right,
}

# -------------------- Handlers --------------------
def apply_alignment(alignment_name):
    chosen_alignment = alignment_map[alignment_name]

    t = Transaction(doc, "Set TextNote Justification ({})".format(alignment_name))
    t.Start()
    count = 0
    for tn in textnotes:
        try:
            tn.HorizontalAlignment = chosen_alignment
            count += 1
        except Exception as e:
            print("Failed on TextNote ID {}: {}".format(tn.Id.IntegerValue, e))
    t.Commit()

    forms.alert("Adjusted justification for {} text note(s) to {}.".format(count, alignment_name.lower()))
    dlg.Close()

left_btn.Click += lambda s, a: apply_alignment("Left")
centre_btn.Click += lambda s, a: apply_alignment("Centre")
right_btn.Click += lambda s, a: apply_alignment("Right")
cancel_btn.Click += lambda s, a: dlg.Close()

# -------------------- Show Dialog --------------------
dlg.ShowDialog()

