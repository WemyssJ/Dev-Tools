# -*- coding: utf-8 -*-
__title__ = 'Spell Check Text'
__author__ = 'Joe Wemyss'
__doc__ = 'Spell checks all TextNotes in the project with filters for abbreviations and dimensions.'

from pyrevit import revit, script, forms
from Autodesk.Revit.DB import FilteredElementCollector, TextNote, Transaction
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
    "BIM", "QA", "HSE", "HVAC", "FFE", "M&E", "tof",
    "bof", "toc", "tow", "ffl", "ssl", "ga", "ga's",
    "dpc", "dpm", "debonded", "craddys", "h6", "h8",
    "h10", "h12", "h16", "h20", "h25", "h32", "h40",
    "blockwork", "a393", "a252", "a193", "a142", "b1131",
    "b785", "b503", "b385", "b283", "c785", "c636", "c503",
    "c385", "c283", "d98", "d49", "nsss", "s275", "s355", "uno",
    "thk", "b500a", "b500b", "b500c", "kingspan", "multibeam", "tbc",
    "citb", "svp", "nhbc", "windpost", "csunk", "ubar", "lbar", "c/c's",
    "bjr", "st1", "rt2", "er1", "naylor", "baseplates", "fosorc", "insitu"
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

def split_and_clean(word):
    parts = re.split(r'[\/\-\&\+\_:]', word)
    return [clean_word(part) for part in parts if part]

def looks_like_dimension(word):
    return re.match(r'^\d+([xX*/]\d+)?(mm|cm|m|nmm|cc|knm2|sq|kg|knm|no|kn|kgm|hrs)?$', word) or word.startswith('Ø')

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

def highlight_misspelled(word, text):
    pattern = r'\b({})\b'.format(re.escape(word))
    return re.sub(pattern, r'>>\1<<', text, count=1, flags=re.IGNORECASE)

# --- Ask user if they want to correct mistakes interactively ---
enable_corrections = forms.alert(
    "Would you like to correct spelling mistakes interactively?",
    options=["Yes", "No"]
) == "Yes"

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
            subwords = split_and_clean(word)
            for cleaned in subwords:
                if is_false_positive(cleaned):
                    continue
                if cleaned not in ENGLISH_WORDS:
                    misspelled_words.add(cleaned)

        if misspelled_words:
            original_text = tn.Text
            updated_text = original_text

            if enable_corrections:
                for misspelled in sorted(misspelled_words):
                    context_preview = highlight_misspelled(misspelled, updated_text)
                    prompt = (
                        "Misspelled word: '{}'\n\n"
                        "Context:\n{}\n\n"
                        "Enter correction (leave blank to ignore):"
                    ).format(misspelled, context_preview)
                    correction = forms.ask_for_string(prompt=prompt, default="")
                    if correction and correction != misspelled:
                        updated_text = re.sub(r'\b{}\b'.format(re.escape(misspelled)), correction, updated_text)

                if updated_text != original_text:
                    with Transaction(doc, "Correct Spelling in TextNote"):
                        tn.Text = updated_text

            # Log output
            mistakes.extend([(w, original_text, tn, tn.OwnerViewId) for w in misspelled_words])
            view = doc.GetElement(tn.OwnerViewId)
            el_id = output.linkify(tn.Id)
            view_id_str = output.linkify(tn.OwnerViewId)
            highlighted_words = ", ".join("**<u>{}</u>**".format(w) for w in sorted(misspelled_words))
            output.print_md("### ❌ Spelling Mistakes: {}".format(highlighted_words))
            output.print_md("- 📝 Original: `{}`".format(original_text))
            if updated_text != original_text:
                output.print_md("- ✅ Corrected: `{}`".format(updated_text))
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
