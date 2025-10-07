# -*- coding: utf-8 -*-
"""
Align Text Notes (Left / Centre / Right)
Sets justification for selected TextNotes or all notes in the active view.
Fast, no moving/alignment of boxes.
"""

from Autodesk.Revit.DB import *
from pyrevit import revit, forms

doc = revit.doc
uidoc = revit.uidoc

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

# -------------------- WPF / PyRevit selection --------------------
alignment_choice = forms.CommandSwitchWindow.show(
    {
        "Left": "Left justification (UK writing style)",
        "Centre": "Centre justification",
        "Right": "Right justification",
    },
    message="Select text justification:"
)
if not alignment_choice:
    forms.alert("No justification selected.", exitscript=True)

alignment_map = {
    "Left": HorizontalTextAlignment.Left,
    "Centre": HorizontalTextAlignment.Center,
    "Right": HorizontalTextAlignment.Right,
}
chosen_alignment = alignment_map[alignment_choice]

# -------------------- Transaction --------------------
t = Transaction(doc, "Set TextNote Justification ({})".format(alignment_choice))
t.Start()

count = 0
for tn in textnotes:
    try:
        tn.HorizontalAlignment = chosen_alignment
        count += 1
    except Exception as e:
        print("Failed on TextNote ID {}: {}".format(tn.Id.IntegerValue, e))

t.Commit()

# -------------------- Report --------------------
forms.alert("Adjusted justification for {} text note(s) to {}.".format(count, alignment_choice.lower()))
