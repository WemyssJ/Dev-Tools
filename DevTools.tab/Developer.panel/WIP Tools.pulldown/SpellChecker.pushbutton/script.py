# -*- coding: utf-8 -*-
__title__ = 'Spell Check Text'
__author__ = 'Joe Wemyss'
__doc__ = 'Spell checks all TextNotes in the project with filters for abbreviations and dimensions.'

from pyrevit import revit, script, forms
from Autodesk.Revit.DB import FilteredElementCollector, TextNote
import os
import re

doc = revit.doc
output = script.get_output()
output.set_title("Spelling Mistakes")

# --- Load dictionary ---
word_file = os.path.join(os.path.dirname(__file__), 'english_words.txt')
if not os.path.exists(word_file):
    output.print_md("❌ Dictionary file missing: `english_words.txt`")
    script.exit()

with open(word_file, 'r') as f:
    ENGLISH_WORDS = set([w.strip().lower() for w in f.readlines()])

# --- Configurable filters ---
MIN_WORD_LENGTH = 3
IGNORE_UPPERCASE = True

CUSTOM_IGNORE = set([
    "resourced", "RAMS", "WPP", "CDM", "PPE", "COSHH",
    "BIM", "QA", "HSE", "HVAC", "FFE", "M&E"
])

COMMON_REVIT_WORDS = set([
    "beam", "slab", "wall", "void", "grid", "section", "column",
    "floor", "ceiling", "duct", "pipe", "revit", "level", "sheet",
    "tag", "dimension", "family", "schedule", "titleblock", "detail",
    "elevation", "symbol", "door", "window", "fire", "exit", "room",
])

# --- Helpers ---
def clean_word(word):
    return re.sub(r"[^\w']", '', word).lower()

def looks_like_dimension(word):
    return re.match(r'^\d+([xX*/]\d+)?(mm|cm|m)?$', word) or word.startswith('Ø')

def is_false_positive(word):
    if not word:
        return True
    if len(word) < MIN_WORD_LENGTH:
        return True
    if IGNORE_UPPERCASE and word.isupper():
        return True
    if word.lower() in CUSTOM_IGNORE:
        return True
    if word.lower() in COMMON_REVIT_WORDS:
        return True
    if looks_like_dimension(word):
        return True
    return False

# --- Collect TextNotes ---
textnotes = FilteredElementCollector(doc).OfClass(TextNote).ToElements()
mistakes = []

with forms.ProgressBar(step=1,
                       title='Spell checking TextNotes... {value} of {max_value}',
                       cancellable=True) as pb:

    total_notes = len(textnotes)
    for idx, tn in enumerate(textnotes):
        if pb.cancelled:
            output.print_md("⚠️ Spell check cancelled by user after {} notes.".format(idx))
            break

        if not tn.Text:
            pb.update_progress(idx + 1, total_notes)
            continue

        words = tn.Text.split()
        misspelled_words = set()
        for word in words:
            cleaned = clean_word(word)
            if is_false_positive(cleaned):
                continue
            if cleaned not in ENGLISH_WORDS:
                misspelled_words.add(cleaned)

        if misspelled_words:
            mistakes.extend([(w, tn.Text, tn, tn.OwnerViewId) for w in misspelled_words])
            view = doc.GetElement(tn.OwnerViewId)
            el_id = output.linkify(tn.Id)
            view_id_str = output.linkify(tn.OwnerViewId)
            # Format all misspelled words bold + underlined, joined by commas
            highlighted_words = ", ".join("**<u>{}</u>**".format(w) for w in sorted(misspelled_words))
            output.print_md("### ❌ Spelling Mistakes: {}".format(highlighted_words))
            output.print_md("- 📝 Context: `{}`".format(tn.Text))
            output.print_md("- 📍 In view: **{}** (id: {})".format(view.Name if view else "Unknown", view_id_str))
            output.print_md("- 🔗 Element ID: {}".format(el_id))
            output.print_md("---")

        pb.update_progress(idx + 1, total_notes)

# --- Output summary ---
if not mistakes:
    output.print_md("✅ No spelling mistakes found.")
else:
    unique_mistakes = set(w for (w, _, _, _) in mistakes)
    output.print_md("## 📊 Summary: Found {} unique spelling mistake(s).".format(len(unique_mistakes)))
