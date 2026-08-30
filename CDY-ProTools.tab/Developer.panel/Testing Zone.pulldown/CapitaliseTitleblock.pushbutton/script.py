# -*- coding: utf-8 -*-
"""
Smart Sheet Name Formatter (Enhanced)
-------------------------------------
- ALL CAPS option
- Smart Title Case:
    * Preserves acronyms (GA, RCP, MEP, etc.)
    * Keeps numbers intact
    * Handles separators (- / :)
    * Keeps small words lowercase (of, and, the, etc.)
"""

from pyrevit import revit, DB, script, forms
import re

doc = revit.doc
output = script.get_output()

# -------------------------------
# USER DIALOG
# -------------------------------
options = ['ALL CAPS', 'Title Case']

selected_option = forms.CommandSwitchWindow.show(
    options,
    message='Select text format for Sheet Names:'
)

if not selected_option:
    script.exit()

# -------------------------------
# SETTINGS (EDITABLE)
# -------------------------------
ACRONYMS = {
    'GA', 'RCP', 'MEP', 'HVAC', 'ID', 'WC', 'SVP',
    'LV', 'MV', 'HV', 'UPS', 'AA', 'BB', 'CC', 'DD', 'EE', 'FF', 'GG', 'HH',
}

SMALL_WORDS = {
    'of', 'and', 'the', 'to', 'in', 'on', 'at',
    'for', 'by', 'with', 'a', 'an'
}

# -------------------------------
# SMART TITLE FUNCTION
# -------------------------------
def smart_title(text):
    tokens = re.split(r'(\W+)', text)

    # Identify word tokens (ignore separators)
    word_indices = [i for i, t in enumerate(tokens) if t.strip() and re.match(r'\w+', t)]

    if not word_indices:
        return text

    first_word_index = word_indices[0]
    last_word_index = word_indices[-1]

    result = []

    for i, token in enumerate(tokens):
        if not token.strip():
            result.append(token)
            continue

        if not re.match(r'\w+', token):
            result.append(token)
            continue

        upper_token = token.upper()
        lower_token = token.lower()

        # Rule 1: Acronyms
        if upper_token in ACRONYMS:
            result.append(upper_token)
            continue

        # Rule 2: Numbers / alphanumeric (e.g. 01, 2B)
        if re.match(r'^\d+[A-Za-z]*$', token):
            result.append(token.upper())
            continue

        # Rule 3: Small words (not first/last)
        if (
            lower_token in SMALL_WORDS and
            i != first_word_index and
            i != last_word_index
        ):
            result.append(lower_token)
            continue

        # Rule 4: Normal word
        result.append(token.capitalize())

    return ''.join(result)

# -------------------------------
# FORMAT FUNCTION
# -------------------------------
def format_name(name, option):
    if option == 'ALL CAPS':
        return name.upper()
    elif option == 'Title Case':
        return smart_title(name)
    else:
        return name

# -------------------------------
# COLLECT SHEETS
# -------------------------------
collector = DB.FilteredElementCollector(doc) \
    .OfClass(DB.ViewSheet) \
    .ToElements()

updated_count = 0
skipped_count = 0

# -------------------------------
# TRANSACTION
# -------------------------------
t = DB.Transaction(doc, "Format Sheet Names (Smart v2)")
t.Start()

for sheet in collector:
    try:
        current_name = sheet.Name

        if not current_name:
            skipped_count += 1
            continue

        new_name = format_name(current_name, selected_option)

        if current_name != new_name:
            sheet.Name = new_name
            updated_count += 1

            output.print_md(
                "**UPDATED:** {} → {}".format(current_name, new_name)
            )
        else:
            skipped_count += 1

    except Exception as e:
        output.print_md(
            "**ERROR on sheet {}:** {}".format(sheet.SheetNumber, str(e))
        )

t.Commit()

# -------------------------------
# RESULTS
# -------------------------------
output.print_md("---")
output.print_md("### ✅ Results")
output.print_md("- Format Chosen: {}".format(selected_option))
output.print_md("- Updated: {}".format(updated_count))
output.print_md("- Skipped: {}".format(skipped_count))