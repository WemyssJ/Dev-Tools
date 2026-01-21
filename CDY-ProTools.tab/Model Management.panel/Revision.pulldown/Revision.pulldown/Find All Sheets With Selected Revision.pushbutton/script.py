from pyrevit import revit, DB, forms

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

selectedrevseq = []
selectedrevinfo = []

# Prompt user to select revisions
revisions = forms.select_revisions(button_name='Select Revision', multiple=True)

# Gather sequence numbers and descriptions
for r in revisions:
    selectedrevseq.append(r.SequenceNumber)
    rev_date = r.RevisionDate if r.RevisionDate else "N/A"
    description = r.Description if r.Description else "No Description"
    selectedrevinfo.append('Sequence {0}: {1} (Date: {2})'.format(r.SequenceNumber, description, rev_date))

# Print selected revision info
print('SEARCHING FOR SHEETS THAT CONTAIN ATLEAST ONE OF SELECTED REVISION IDS:')
for info in selectedrevinfo:
    print(info)

print('\nNAME\tNUMBER\n' + '-' * 70)

# Collect and sort sheets
sheetsnotsorted = DB.FilteredElementCollector(revit.doc)\
    .OfCategory(DB.BuiltInCategory.OST_Sheets)\
    .WhereElementIsNotElementType()\
    .ToElements()

sheets = sorted(sheetsnotsorted, key=lambda x: x.SheetNumber)

# Print sheets that include selected revisions
for s in sheets:
    hasSelectedRevision = False
    revision_ids = s.GetAllRevisionIds()

    for rev_id in revision_ids:
        rev = revit.doc.GetElement(rev_id)
        if rev.SequenceNumber in selectedrevseq:
            hasSelectedRevision = True
            break

    if hasSelectedRevision:
        print('{0}\t{1}'.format(
            s.Parameter[DB.BuiltInParameter.SHEET_NUMBER].AsString(),
            s.Parameter[DB.BuiltInParameter.SHEET_NAME].AsString()))
