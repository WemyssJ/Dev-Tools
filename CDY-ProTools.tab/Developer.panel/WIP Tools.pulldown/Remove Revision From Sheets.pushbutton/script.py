"""Remove selected revisions from selected sheets (Shift+Click for unsafe mode)."""

from pyrevit import revit, DB, forms, script
import clr
clr.AddReference("System.Windows.Forms")
from System.Windows.Forms import Control, Keys
from System.Collections.Generic import List

logger = script.get_logger()
doc = revit.doc

# --- Detect Shift for unsafe mode ---
unsafe_mode = (Control.ModifierKeys & Keys.Shift) == Keys.Shift

if unsafe_mode:
    forms.alert(
        "UNSAFE MODE ENABLED\n\n"
        "You are bypassing the 'Issued' check.\n"
        "Issued revisions and hidden clouds may be forcibly removed!",
        ok=True,
        warn_icon=True
    )
    filterfunc = None  # Include all revisions
else:
    def filterfunc(rev):
        return not rev.Issued  # Safe mode: only unissued

# --- Select revisions ---
revisions = forms.select_revisions(
    button_name='Select Revision',
    multiple=True,
    filterfunc=filterfunc
)
if not revisions:
    script.exit()

revision_ids = [r.Id for r in revisions]

# --- Select sheets ---
sheets = forms.select_sheets(
    button_name='Remove Revisions',
    include_placeholder=True
)
if not sheets:
    script.exit()

# --- Begin Transaction ---
with revit.Transaction("Remove Revision from Sheets (Unsafe Mode)" if unsafe_mode else "Remove Revision from Sheets"):

    if unsafe_mode:
        # Step 1: Save issued status
        revision_states = {r.Id: r.Issued for r in revisions}

        # Step 2: Temporarily unissue all revisions
        for r in revisions:
            if r.Issued:
                r.Issued = False
        doc.Regenerate()

        # Step 3: Optionally mark revisions as "Cloud and Tag"
        # (In Revit API, cloud visibility is per sheet; we'll focus on removing them)
        # Collect all clouds linked to selected revisions
        all_clouds = DB.FilteredElementCollector(doc) \
            .OfCategory(DB.BuiltInCategory.OST_RevisionClouds) \
            .WhereElementIsNotElementType() \
            .ToElements()

        total_clouds_deleted = 0
        per_sheet_summary = []

        # Step 4: Remove revisions and clouds per sheet
        for sheet in sheets:
            sheet_clouds_deleted = 0

            # Remove revision from the sheet itself
            try:
                current_sheet_revs = list(sheet.GetAllRevisionIds())
                new_sheet_revs = [rid for rid in current_sheet_revs if rid not in revision_ids]
                if len(new_sheet_revs) != len(current_sheet_revs):
                    sheet.SetAdditionalRevisionIds(List[DB.ElementId](new_sheet_revs))
            except Exception as ex:
                logger.warning("Failed to remove revisions from sheet {}: {}".format(sheet.SheetNumber, ex))

            # Remove revision from views on the sheet
            viewports = DB.FilteredElementCollector(doc, sheet.Id) \
                .OfCategory(DB.BuiltInCategory.OST_Viewports) \
                .WhereElementIsNotElementType() \
                .ToElements()
            view_ids = [vp.ViewId for vp in viewports]

            for vp in viewports:
                view = doc.GetElement(vp.ViewId)
                if hasattr(view, "GetAllRevisionIds") and hasattr(view, "SetAdditionalRevisionIds"):
                    try:
                        current_view_revs = list(view.GetAllRevisionIds())
                        new_view_revs = [rid for rid in current_view_revs if rid not in revision_ids]
                        if len(new_view_revs) != len(current_view_revs):
                            view.SetAdditionalRevisionIds(List[DB.ElementId](new_view_revs))
                    except Exception as ex:
                        logger.warning("Failed to remove revisions from view {}: {}".format(view.Name, ex))

            # Delete clouds linked to these revisions on this sheet
            for cloud in all_clouds:
                if cloud.RevisionId in revision_ids and cloud.OwnerViewId in view_ids + [DB.ElementId.InvalidElementId]:
                    try:
                        doc.Delete(cloud.Id)
                        sheet_clouds_deleted += 1
                        total_clouds_deleted += 1
                    except:
                        continue

            per_sheet_summary.append((sheet.SheetNumber, sheet.Name, sheet_clouds_deleted))

        doc.Regenerate()

        # Step 5: Restore original issued status
        for r in revisions:
            r.Issued = revision_states[r.Id]
        doc.Regenerate()

        # --- Report ---
        print("SELECTED REVISION REMOVAL COMPLETE\n")
        print("-" * 100)
        for sn, name, clouds_deleted in per_sheet_summary:
            print("{}   {}   - Deleted {} clouds".format(sn, name, clouds_deleted))
        print("\nTotal clouds deleted: {}".format(total_clouds_deleted))
        print("\nUNSAFE MODE COMPLETE: Issued and cloud-linked revisions forcibly removed from selected sheets.\n")

    else:
        # SAFE MODE: respect issued lock
        updated_sheets = revit.update.update_sheet_revisions(revisions, sheets, state=False)
        if updated_sheets:
            print('SELECTED REVISION REMOVED FROM THESE SHEETS:')
            print('-' * 100)
            cloudedsheets = []
            for s in sheets:
                if s in updated_sheets:
                    revit.report.print_sheet(s)
                else:
                    cloudedsheets.append(s)
        else:
            cloudedsheets = sheets

        if cloudedsheets:
            print('\n\nSELECTED REVISION IS CLOUDED ON THESE SHEETS AND CANNOT BE REMOVED.')
            print('-' * 100)
            for s in cloudedsheets:
                revit.report.print_sheet(s)
