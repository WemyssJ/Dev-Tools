"""Changes all characters in text box to Lowercase"""


__context__ = 'OST_TextNotes'

from pyrevit import revit, coreutils

selection = revit.get_selection()

def lowercase():
    with revit.Transaction('lowercase'):
        for el in selection.elements:
            el.Text = el.Text.lower()

lowercase()