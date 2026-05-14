# -*- coding: utf-8 -*-

from pyrevit import revit, DB, forms
import re
from collections import defaultdict

doc = revit.doc
uidoc = revit.uidoc

selection_ids = uidoc.Selection.GetElementIds()

if not selection_ids:
    forms.alert("Please select some tags or text notes.", exitscript=True)

totals = defaultdict(int)

pattern = re.compile(r"(\d+)\s+(H\d+-\d+)", re.IGNORECASE)

for el_id in selection_ids:
    el = doc.GetElement(el_id)

    text = None

    if isinstance(el, DB.TextNote):
        text = el.Text
    elif isinstance(el, DB.IndependentTag):
        try:
            text = el.TagText
        except:
            continue

    if not text:
        continue

    matches = pattern.findall(text)

    for qty_str, bar_mark in matches:
        qty = int(qty_str)
        totals[bar_mark.upper()] += qty

# Output
if not totals:
    forms.alert("No rebar marks found.")
else:
    report = ["REBAR TALLY:\n"]

    for mark in sorted(totals.keys()):
        report.append("{} = {} no.".format(mark, totals[mark]))

    forms.alert("\n".join(report))