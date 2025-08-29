# -*- coding: utf-8 -*-
__context__ = 'OST_TextNotes'
__doc__ = 'Inserts a special character at the beginning of selected Text Notes.'
__title__ = 'Symbols'

from pyrevit import revit, coreutils

from pyrevit.framework import List
from pyrevit import revit, DB, UI
from pyrevit import forms


selection = revit.get_selection()

def addSymbol(symbol):
    with revit.Transaction('Symbols'):
        for el in selection.elements:
            el.Text = symbol + el.Text
            # el.Text = el.Text.upper()

# options = sorted(["±","°","Ø","€","<",">","#","&","Ʃ","λ","μ","≈","≠","≤","≥"])
options = ["±","Ø","€","°","<",">","≤","≥","≈","≠","#","&","Ʃ","λ","μ"]

selected_switch = \
    forms.CommandSwitchWindow.show(options,
                                   message='Vyber symbol:')

if selected_switch:
    addSymbol(selected_switch)