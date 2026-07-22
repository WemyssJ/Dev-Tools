# -*- coding: utf-8 -*-
"""Master Revision Tool — unified interface for managing revisions in Revit (IronPython compatible)."""

from pyrevit import revit, DB, forms, script
from System.Collections.Generic import List
import clr
clr.AddReference('System.Windows.Forms')
from System.Windows.Forms import Control, Keys
from pyrevit.forms import WPFWindow
import os
from System import Uri
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption

##############################################################################################
# TELEMETRY IMPORTS #
##############################################################################################
# Only works IF specified TELEMETRY_JSON path exists within %AppData%\pyRevit\Extensions\BIMTools.extension\lib\telemetry_auto.py"
# Records tool usage by date & revit version
import os, sys

# Add lib folder for telemetry_auto
lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'lib'))
if lib_path not in sys.path:
    sys.path.append(lib_path)

import telemetry_auto

tool_name = os.path.basename(os.path.dirname(__file__)) 
TOOL_NAME = tool_name.replace(".pushbutton", "")
telemetry_auto.log_tool_usage(TOOL_NAME)
##############################################################################################


logger = script.get_logger()

# -----------------------------
# Helper functions
# -----------------------------
def get_all_revisions(doc=None):
    if doc is None:
        doc = revit.doc
    return DB.FilteredElementCollector(doc).OfClass(DB.Revision).ToElements()


def safe_get_revision_number(rev):
    """Safely get RevisionNumber (handles Per-Sheet numbering)."""
    try:
        return rev.RevisionNumber
    except:
        return "<per-sheet>"


def copy_revision_to_doc(src_rev, dest_doc):
    """Create a new Revision in dest_doc, copying key properties safely."""
    new_rev = DB.Revision.Create(dest_doc)

    # --- copy standard text fields ---
    try:
        new_rev.Description = src_rev.Description
    except:
        pass

    try:
        new_rev.IssuedBy = src_rev.IssuedBy
    except:
        pass

    try:
        new_rev.IssuedTo = src_rev.IssuedTo
    except:
        pass

    try:
        new_rev.RevisionDate = src_rev.RevisionDate
    except:
        pass

    # --- safely handle RevisionNumber (can fail under per-sheet mode) ---
    try:
        new_rev.RevisionNumber = src_rev.RevisionNumber
    except:
        # per-sheet numbering or API restriction — ignore
        pass

    # --- safely handle properties that may not exist in some Revit versions ---
    if hasattr(src_rev, "RevisionVisibility") and hasattr(new_rev, "RevisionVisibility"):
        try:
            new_rev.RevisionVisibility = src_rev.RevisionVisibility
        except:
            pass

    if hasattr(src_rev, "NumberType") and hasattr(new_rev, "NumberType"):
        try:
            new_rev.NumberType = src_rev.NumberType
        except:
            pass

    # --- sequence and flags ---
    try:
        new_rev.SequenceNumber = src_rev.SequenceNumber
    except:
        pass

    if hasattr(src_rev, "Issued"):
        try:
            new_rev.Issued = src_rev.Issued
        except:
            pass
    if hasattr(src_rev, "SheetIssued"):
        try:
            new_rev.SheetIssued = src_rev.SheetIssued
        except:
            pass
    if hasattr(src_rev, "ProjectIssued"):
        try:
            new_rev.ProjectIssued = src_rev.ProjectIssued
        except:
            pass

    return new_rev


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
            # Some Revit versions expose Revision.Visibility, some expose RevisionVisibility enum etc.
            try:
                if hasattr(rev, "Visibility"):
                    rev.Visibility = DB.RevisionVisibility.Hidden
                elif hasattr(rev, "RevisionVisibility"):
                    rev.RevisionVisibility = DB.RevisionVisibility.Hidden
            except Exception:
                # Best effort — skip if property not available
                pass

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
# 7. Copy revisions to other open documents
# -----------------------------
def action_copy_revisions():
    """
    Show a selection of revisions in the active document, let user pick one or more,
    then select one or more destination open documents and copy the revisions into them.
    """
    src_doc = revit.doc
    all_revs = get_all_revisions(src_doc)
    if not all_revs:
        forms.alert("No revisions found in active document.", exitscript=True)
        return

    # Build display list (safe on per-sheet numbering)
    rev_options = [
        "Seq {} | Rev {} | {}".format(
            r.SequenceNumber,
            safe_get_revision_number(r),
            r.Description or "<no description>"
        )
        for r in all_revs
    ]

    selected_names = forms.SelectFromList.show(
        rev_options,
        title="Select Revisions to Copy",
        multiselect=True,
        button_name="Copy Selected Revisions"
    )

    if not selected_names:
        return

    # Map selections back to revision objects
    selected_revs = [r for name, r in zip(rev_options, all_revs) if name in selected_names]

    # Choose destination documents (one or more open docs)
    dest_docs = forms.select_open_docs(title='Select Destination Documents')
    if not dest_docs:
        return

    # Copy revisions into destination docs inside transactions
    for ddoc in dest_docs:
        try:
            with revit.Transaction("Copy Revisions", doc=ddoc):
                for src_rev in selected_revs:
                    copy_revision_to_doc(src_rev, ddoc)
        except Exception as ex:
            logger.error("Failed copying revisions to document {0}: {1}".format(ddoc.Title, ex))
            forms.alert("Failed copying revisions to: {0}\nSee console for details.".format(ddoc.Title), ok=True)

    forms.alert("{} revision(s) copied to {} document(s).".format(len(selected_revs), len(dest_docs)), ok=True)


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
        self.btnFind.Click += lambda s, e: (self.Close(), action_find_sheets_with_revision())
        self.btnIssued.Click += lambda s, e: (self.Close(), action_set_revisions_as_issued())
        self.btnHideClouds.Click += lambda s, e: (self.Close(), action_turn_off_revision_clouds())
        self.btnSheetSet.Click += lambda s, e: (self.Close(), action_create_sheet_set())
        # NEW: Copy Revisions button
        # If the XAML doesn't contain btnCopy this will raise — ensure XAML updated below.
        self.btnCopy.Click += lambda s, e: (self.Close(), action_copy_revisions())


# -----------------------------
# Launch UI
# -----------------------------
xaml_path = os.path.join(os.path.dirname(__file__), "RevManager.xaml")
win = MasterRevisionWindow(xaml_path)

icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
if os.path.exists(icon_path):
    bmp = BitmapImage()
    bmp.BeginInit()
    bmp.UriSource = Uri(icon_path)
    bmp.CacheOption = BitmapCacheOption.OnLoad
    bmp.EndInit()
    win.FindName("headerIcon").Source = bmp
win.ShowDialog()

