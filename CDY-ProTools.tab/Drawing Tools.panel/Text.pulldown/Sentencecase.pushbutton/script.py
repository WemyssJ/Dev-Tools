"""Changes all characters in text box to Sentencecase"""


__context__ = 'OST_TextNotes'

from pyrevit import revit, coreutils

selection = revit.get_selection()

def sentencecase():
    with revit.Transaction('sentencecase'):
        for el in selection.elements:
            el.Text = el.Text[0].upper() + el.Text[1:].lower()

sentencecase()