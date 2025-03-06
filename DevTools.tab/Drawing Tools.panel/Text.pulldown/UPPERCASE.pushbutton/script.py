"""Changes all characters in text box to Uppercase"""

__context__ = 'OST_TextNotes'

from pyrevit import revit, coreutils

selection = revit.get_selection()

def uppercase():
    with revit.Transaction('uppercase'):
        for el in selection.elements:
            el.Text = el.Text.upper()

uppercase()