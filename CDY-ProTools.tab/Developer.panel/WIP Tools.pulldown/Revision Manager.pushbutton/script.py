# -*- coding: utf-8 -*-
"""Master Revision Tool — unified interface for managing revisions in Revit (IronPython compatible)."""

from pyrevit import revit, DB, forms, script
from System.Collections.Generic import List
import clr
clr.AddReference('System.Windows.Forms')
from System.Windows.Forms import Control, Keys
from pyrevit.forms import WPFWindow
import os

logger = script.get_logger()

# -----------------------------
# Helper functions
# -----------------------------
def get_all_revisions():
    return DB.FilteredElementCollector(revit.doc).OfClass(DB.Revision).ToElements()


# -----------------------------
# 1. Add revision(s) to sheets
# -----------------------------
def action_add_revisions_to_sheets():
    def filterfunc(rev):
        return not rev.Issued

    revisions = forms.select_revisions(button_name='Select Revision', multiple=True, filterfunc=filterfunc)
    if not revisions:
        return

    sheets = forms.select_sheets(button_name='Set Revision', include_placeholder=True)
    if not sheets:
        return

    with revit.Transaction('Set Revision on Sheets'):
        updated_sheets = revit.update.update_sheet_revisions(revisions, sheets)

    if updated_sheets:
        print('SELECTED REVISION ADDED TO THESE SHEETS:')
        print('-' * 100)
        for s in updated_sheets:
            snum = s.Parameter[DB.BuiltInParameter.SHEET_NUMBER].AsString().rjust(10)
            sname = s.Parameter[DB.BuiltInParameter.SHEET_NAME].AsString().ljust(50)
            print("NUMBER: {0}   NAME: {1}".format(snum, sname))
    else:
        print("No sheets were updated.")


# -----------------------------
# 2. Remove revisions from sheets
# -----------------------------
def action_remove_revisions_from_sheets():
    unsafe_mode = (Control.ModifierKeys & Keys.Shift) == Keys.Shift
    doc = revit.doc

    if unsafe_mode:
        forms.alert(
            "UNSAFE MODE ENABLED\n\nIssued revisions and hidden clouds may be forcibly removed!",
            ok=True, warn_icon=True
        )
        filterfunc = None
    else:
        def filterfunc(rev):
            return not rev.Issued

    revisions = forms.select_revisions(button_name='Select Revision', multiple=True, filterfunc=filterfunc)
    if not revisions:
        return

    revision_ids = [r.Id for r in revisions]
    sheets = forms.select_sheets(button_name='Remove Revisions', include_placeholder=True)
    if not sheets:
        return

    with revit.Transaction("Remove Revision from Sheets"):
        for sheet in sheets:
            try:
                current_sheet_revs = list(sheet.GetAllRevisionIds())
                new_sheet_revs = [rid for rid in current_sheet_revs if rid not in revision_ids]
                if len(new_sheet_revs) != len(current_sheet_revs):
                    sheet.SetAdditionalRevisionIds(List[DB.ElementId](new_sheet_revs))
            except Exception as ex:
                logger.warning("Failed to remove revisions from sheet {0}: {1}".format(sheet.SheetNumber, ex))

    forms.alert("Revisions removed from selected sheets.", ok=True)


# -----------------------------
# 3. Turn off all revision clouds
# -----------------------------
def action_turn_off_revision_clouds():
    revs = DB.FilteredElementCollector(revit.doc) \
             .OfCategory(DB.BuiltInCategory.OST_Revisions) \
             .WhereElementIsNotElementType()

    with revit.Transaction('Turn off Revisions'):
        for rev in revs:
            rev.Visibility = DB.RevisionVisibility.Hidden

    forms.alert("All revision clouds hidden.", ok=True)


# -----------------------------
# 4. Set selected revisions as issued
# -----------------------------
def action_set_revisions_as_issued():
    doc = revit.doc
    all_revs = DB.FilteredElementCollector(doc).OfClass(DB.Revision).ToElements()
    unissued = [r for r in all_revs if not r.Issued]

    if not unissued:
        forms.alert("All revisions are already issued.", ok=True)
        return

    selected = forms.SelectFromList.show(
        unissued, name_attr='Description', multiselect=True,
        title='Select Revisions to Mark as Issued',
        button_name='Mark as Issued'
    )
    if not selected:
        return

    if not forms.alert("Mark selected revisions as Issued?", yes=True, no=True, warn_icon=True):
        return

    with revit.Transaction('Mark Revisions as Issued'):
        for rev in selected:
            try:
                rev.Issued = True
                logger.info("Revision '{0}' set to Issued.".format(rev.Description))
            except Exception as e:
                logger.error("Failed to update revision '{0}': {1}".format(rev.Description, e))

    forms.alert("Selected revisions marked as Issued.", ok=True)


# -----------------------------
# 5. Create revision sheet set
# -----------------------------
def action_create_sheet_set():
    revisions = forms.select_revisions(button_name='Create Sheet Set', multiple=True)
    if not revisions:
        return

    if len(revisions) > 1:
        selected_switch = forms.CommandSwitchWindow.show(
            ['Matching ANY revision', 'Matching ALL revisions'],
            message='Pick an option:'
        )
    else:
        selected_switch = 'Matching ALL revisions'

    if not selected_switch:
        return

    match_any = (selected_switch == 'Matching ANY revision')
    with revit.Transaction('Create Revision Sheet Set'):
        rev_sheetset = revit.create.create_revision_sheetset(revisions, match_any=match_any)

    empty_sheets = [s for s in rev_sheetset if revit.query.is_sheet_empty(s)]
    if empty_sheets:
        print("These sheets appear empty:")
        for es in empty_sheets:
            revit.report.print_sheet(es)

    forms.alert("Sheet set created successfully.", ok=True)


# -----------------------------
# 6. Find all sheets with selected revision
# -----------------------------
def action_find_sheets_with_revision():
    revisions = forms.select_revisions(button_name='Select Revision', multiple=True)
    if not revisions:
        return

    seqs = [r.SequenceNumber for r in revisions]
    print("SEARCHING FOR SHEETS WITH SELECTED REVISIONS...\n")

    sheets = DB.FilteredElementCollector(revit.doc) \
        .OfCategory(DB.BuiltInCategory.OST_Sheets) \
        .WhereElementIsNotElementType() \
        .ToElements()

    for s in sorted(sheets, key=lambda x: x.SheetNumber):
        rev_ids = s.GetAllRevisionIds()
        if any(revit.doc.GetElement(rid).SequenceNumber in seqs for rid in rev_ids):
            print("{0}\t{1}".format(
                s.Parameter[DB.BuiltInParameter.SHEET_NUMBER].AsString(),
                s.Parameter[DB.BuiltInParameter.SHEET_NAME].AsString()
            ))

    forms.alert("Search complete — see console for results.", ok=True)


# -----------------------------
# Main Window
# -----------------------------
class MasterRevisionWindow(WPFWindow):
    def __init__(self, xaml_file):
        WPFWindow.__init__(self, xaml_file)
        # Wire up button events
        self.cancelBtn.Click += lambda s, e: self.Close()
        self.btnAdd.Click += lambda s, e: (self.Close(), action_add_revisions_to_sheets())
        self.btnRemove.Click += lambda s, e: (self.Close(), action_remove_revisions_from_sheets())
        self.btnHideClouds.Click += lambda s, e: (self.Close(), action_turn_off_revision_clouds())
        self.btnIssued.Click += lambda s, e: (self.Close(), action_set_revisions_as_issued())
        self.btnSheetSet.Click += lambda s, e: (self.Close(), action_create_sheet_set())
        self.btnFind.Click += lambda s, e: (self.Close(), action_find_sheets_with_revision())


# -----------------------------
# Launch UI
# -----------------------------
xaml_path = os.path.join(os.path.dirname(__file__), "RevManager.xaml")
win = MasterRevisionWindow(xaml_path)
win.ShowDialog()
