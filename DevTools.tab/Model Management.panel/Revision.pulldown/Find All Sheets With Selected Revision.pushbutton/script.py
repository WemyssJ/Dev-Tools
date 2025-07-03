from pyrevit import revit, DB, forms

selectedrevseq = []
hasSelectedRevision = False

revisions = forms.select_revisions(button_name='Select Revision',
                                   multiple=True)

for r in revisions:
    selectedrevseq.append(r.SequenceNumber)

print('REVISED SHEETS:\n\nNAME\tNUMBER\n' + '-'*70)

sheetsnotsorted = DB.FilteredElementCollector(revit.doc)\
                    .OfCategory(DB.BuiltInCategory.OST_Sheets)\
                    .WhereElementIsNotElementType()\
                    .ToElements()

sheets = sorted(sheetsnotsorted, key=lambda x: x.SheetNumber)

for s in sheets:
    hasSelectedRevision = False
    revision_ids = s.GetAllRevisionIds()
    for rev_id in revision_ids:
        rev = revit.doc.GetElement(rev_id)
        if rev.SequenceNumber in selectedrevseq:
            hasSelectedRevision = True
            break

    if hasSelectedRevision:
        print('{0}\t{1}'.format(s.Parameter[DB.BuiltInParameter.SHEET_NUMBER].AsString(),
                                s.Parameter[DB.BuiltInParameter.SHEET_NAME].AsString()))

