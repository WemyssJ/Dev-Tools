# -*- coding: utf-8 -*-
"""Mark selected revisions as Issued."""

from pyrevit import revit, DB, forms, script

doc = revit.doc
logger = script.get_logger()

# --- Collect all revisions that are NOT yet issued ---
all_revisions = DB.FilteredElementCollector(doc).OfClass(DB.Revision).ToElements()
unissued_revs = [r for r in all_revisions if not r.Issued]

if not unissued_revs:
    forms.alert("All revisions are already issued.\nNothing to do.", ok=True)
    script.exit()

# --- Let user pick revisions to mark as issued ---
selected_revs = forms.SelectFromList.show(
    unissued_revs,
    name_attr='Description',
    multiselect=True,
    title="Select Revisions to Mark as Issued",
    button_name="Mark as Issued"
)

if not selected_revs:
    script.exit()

# --- Confirm ---
if not forms.alert(
    "Are you sure you want to mark the selected revisions as Issued?",
    yes=True,
    no=True,
    warn_icon=True
):
    script.exit()

# --- Transaction ---
with revit.Transaction("Mark Selected Revisions as Issued"):
    for rev in selected_revs:
        try:
            rev.Issued = True
            logger.info("Revision '{}' set to Issued.".format(rev.Description))
        except Exception as e:
            logger.error("Failed to update revision '{}': {}".format(rev.Description, e))

forms.alert(
    "✅ Selected revisions have been marked as Issued.",
    ok=True
)
