from pyrevit import revit, DB, forms

doc = revit.doc
uidoc = revit.uidoc
curView = revit.active_view

ownerView = None  # Initialize at top
primaryView = None  # Properly defined before use

# Try sheet view (e.g. if view is on a sheet)
try:
        # Get the sheet that contains this view (via Viewport)
        viewports = DB.FilteredElementCollector(doc).OfClass(DB.Viewport).ToElements()
        for vp in viewports:
            if vp.ViewId == curView.Id:
                sheet = doc.GetElement(vp.SheetId)
                if sheet:
                    uidoc.RequestViewChange(sheet)
                    ownerView = sheet
                    break
except:
        forms.alert('View is not placed on a sheet.', title='Script complete', warn_icon=False)

