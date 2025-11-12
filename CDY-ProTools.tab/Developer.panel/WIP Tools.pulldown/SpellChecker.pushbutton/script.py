# -*- coding: utf-8 -*-
__title__ = 'Spell Check Project'
__author__ = 'Joe Wemyss'
__doc__ = 'Project-wide spell checker with a dialog similar to Revit Fn+F7'

from pyrevit import revit, script, forms
from Autodesk.Revit.DB import FilteredElementCollector, TextNote, Transaction
import os, re, difflib
from System.Windows.Documents import Paragraph, Run
from System.Windows.Media import Brushes
from System.Windows import FontWeights

doc = revit.doc
output = script.get_output()
output.set_title("Spelling Mistakes")

# -------- Paths --------
HERE = os.path.dirname(__file__)
XAMLFILE = os.path.join(HERE, "SpellCheckDialog.xaml")
DICTFILE = os.path.join(HERE, "english_words.txt")

if not os.path.exists(DICTFILE):
    forms.alert("❌ Dictionary file missing: english_words.txt", exitscript=True)

# -------- Load dictionary --------
with open(DICTFILE, "r") as f:
    ENGLISH_WORDS = set(w.strip().lower() for w in f if w.strip())

# Precompute list once for faster get_close_matches
ENGLISH_WORDS_LIST = list(ENGLISH_WORDS)

# -------- Configurable filters --------
MIN_WORD_LENGTH = 3
IGNORE_UPPERCASE = True
CUSTOM_IGNORE = set([])
COMMON_REVIT_WORDS = set([])
WORD_BOUNDARY = r"(?!\')\b"

def clean_word(word):
    return re.sub(r"[^\w']", "", word).lower()

def split_and_clean(word):
    parts = re.split(r"[\/\-\&\+\_:]", word)
    return [clean_word(p) for p in parts if p]

def looks_like_dimension(word):
    return (
        re.match(r'^\d+([xX*/]\d+)?(mm|cm|m|nmm|cc|knm2|sq|kg|knm|no|kn|kgm|hrs)?$', word) or
        word.startswith(u'Ø')
    )

def is_false_positive(word):
    if not word:
        return True
    if len(word) < MIN_WORD_LENGTH:
        return True
    if IGNORE_UPPERCASE and word.isupper():
        return True
    lw = word.lower()
    if lw in CUSTOM_IGNORE:
        return True
    if lw in COMMON_REVIT_WORDS:
        return True
    if looks_like_dimension(lw):
        return True
    return False

def get_suggestions(word, n=8):
    """Return close matches using precomputed dictionary list."""
    lw = word.lower()
    if len(lw) < MIN_WORD_LENGTH:
        return []
    return difflib.get_close_matches(lw, ENGLISH_WORDS_LIST, n=n, cutoff=0.7)

def replace_once(word, repl, text):
    pattern = r"{b}{w}{b2}".format(b=WORD_BOUNDARY, w=re.escape(word), b2=WORD_BOUNDARY)
    return re.sub(pattern, repl, text, count=1, flags=re.IGNORECASE)

def replace_all(word, repl, text):
    pattern = r"{b}{w}{b2}".format(b=WORD_BOUNDARY, w=re.escape(word), b2=WORD_BOUNDARY)
    return re.sub(pattern, repl, text, flags=re.IGNORECASE)

def highlight_in_rtb(rtb, word, text):
    """Highlight first occurrence of 'word' in bold red in RichTextBox."""
    rtb.Document.Blocks.Clear()
    paragraph = Paragraph()
    lowered_text = text.lower()
    lowered_word = word.lower()
    idx = lowered_text.find(lowered_word)

    if idx == -1:
        paragraph.Inlines.Add(Run(text))
    else:
        if idx > 0:
            paragraph.Inlines.Add(Run(text[:idx]))
        run_word = Run(text[idx:idx+len(word)])
        run_word.Foreground = Brushes.Red
        run_word.FontWeight = FontWeights.Bold
        paragraph.Inlines.Add(run_word)
        if idx + len(word) < len(text):
            paragraph.Inlines.Add(Run(text[idx+len(word):]))

    rtb.Document.Blocks.Add(paragraph)

# -------- Collect candidates --------
textnotes = FilteredElementCollector(doc).OfClass(TextNote).ToElements()
queue = []

for tn in textnotes:
    txt = tn.Text or ""
    if not txt:
        continue
    for raw in txt.split():
        for w in split_and_clean(raw):
            if is_false_positive(w):
                continue
            if w not in ENGLISH_WORDS:
                queue.append((w, tn))

if not queue:
    forms.alert("✅ No spelling mistakes found.")
    script.exit()

# -------- WPF Dialog --------
class SpellCheckDialog(forms.WPFWindow):
    def __init__(self, xaml_file):
        forms.WPFWindow.__init__(self, xaml_file)
        self.result = None
        self.change_word = None

    def update(self, word, context, suggestions):
        self.word_box.Text = word
        highlight_in_rtb(self.context_box, word, context)
        self.suggestions_list.ItemsSource = suggestions
        self.change_to.Text = suggestions[0] if suggestions else word
        self.result = None
        self.change_word = None

    def do_ignore(self, sender, args): self.result = "Ignore"; self.Hide()
    def do_ignore_all(self, sender, args): self.result = "IgnoreAll"; self.Hide()
    def do_add(self, sender, args): self.result = "Add"; self.Hide()
    def do_change(self, sender, args): self.result = "Change"; self.change_word = self.change_to.Text; self.Hide()
    def do_change_all(self, sender, args): self.result = "ChangeAll"; self.change_word = self.change_to.Text; self.Hide()
    def do_undo(self, sender, args): self.result = "Undo"; self.Hide()
    def do_close(self, sender, args): self.result = "Close"; self.Hide()

    def on_select_suggestion(self, sender, args):
        if sender.SelectedItem: self.change_to.Text = sender.SelectedItem

# -------- Spellcheck loop --------
ignore_all = set()
change_all = {}
added_words = set()  # track added words for session summary
undo_stack = []

dlg = SpellCheckDialog(XAMLFILE)

i = 0
while i < len(queue):
    word, tn = queue[i]

    lw = word.lower()
    if lw in ENGLISH_WORDS or lw in ignore_all:
        i += 1
        continue

    if lw in change_all:
        newtxt = replace_once(change_all[lw], change_all[lw], tn.Text or "")
        if newtxt != (tn.Text or ""):
            with Transaction(doc, "Spellcheck Change All (auto)"):
                prev = tn.Text
                tn.Text = newtxt
            undo_stack.append((tn, prev))
        i += 1
        continue

    txt = tn.Text or ""
    dlg.update(word, txt, get_suggestions(word))
    dlg.ShowDialog()  # modal dialog

    action = dlg.result
    repl = (dlg.change_word or "").strip() if dlg.change_word else ""

    if action == "Ignore": ignore_all.add(lw); i += 1
    elif action == "IgnoreAll": ignore_all.add(lw); i += 1
    elif action == "Add":
        if lw not in ENGLISH_WORDS:
            with open(DICTFILE, "a") as f:
                f.write("\n" + lw)
            ENGLISH_WORDS.add(lw)
            ENGLISH_WORDS_LIST.append(lw)  # keep list in sync
            added_words.add(lw)
        i += 1
    elif action == "Change":
        if repl and repl.lower() != lw:
            newtxt = replace_once(word, repl, txt)
            if newtxt != txt:
                with Transaction(doc, "Spellcheck Change"):
                    prev = tn.Text
                    tn.Text = newtxt
                undo_stack.append((tn, prev))
        i += 1
    elif action == "ChangeAll":
        if repl and repl.lower() != lw:
            change_all[lw] = repl
            newtxt = replace_all(word, repl, txt)
            if newtxt != txt:
                with Transaction(doc, "Spellcheck ChangeAll"):
                    prev = tn.Text
                    tn.Text = newtxt
                undo_stack.append((tn, prev))
        i += 1
    elif action == "Undo":
        if undo_stack:
            last_tn, last_text = undo_stack.pop()
            with Transaction(doc, "Spellcheck Undo"):
                last_tn.Text = last_text
    elif action == "Close":
        break

# -------- Summary --------
output.print_md("### Session complete.")
output.print_md("- Ignored words (session): `{}`".format(", ".join(sorted(ignore_all)) if ignore_all else "none"))
if change_all:
    pairs = ", ".join(["{}→{}".format(k, v) for k, v in change_all.items()])
    output.print_md("- Change All rules: `{}`".format(pairs))
if added_words:
    output.print_md("- Words added to dictionary this session: **`{}`**".format(", ".join(sorted(added_words))))
