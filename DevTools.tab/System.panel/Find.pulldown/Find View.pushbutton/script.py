from pyrevit import revit, DB, forms

doc = revit.doc
uidoc = revit.uidoc
curView = revit.active_view

ownerView = None  # Initialize at top
primaryView = None  # Properly defined before use

# Try parent view (e.g. for callouts)
try:
    parentViewId = curView.get_Parameter(DB.BuiltInParameter.SECTION_PARENT_VIEW_NAME).AsElementId()
    if parentViewId and parentViewId.IntegerValue != -1:
        ownerView = doc.GetElement(parentViewId)
        uidoc.RequestViewChange(ownerView)
except:
    pass

# Try primary view (e.g. for dependent views)
if ownerView is None:
    try:
        primaryViewId = curView.GetPrimaryViewId()
        if primaryViewId and primaryViewId.IntegerValue != -1:
            ownerView = doc.GetElement(primaryViewId)
            uidoc.RequestViewChange(ownerView)
    except:
        pass

# Try sheet view (e.g. if view is on a sheet)
if ownerView is None and primaryView is None:
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
        pass

# Alert if no owner view was found
if ownerView is None:
    forms.alert('View has no parent, primary, or sheet view.', title='Script complete', warn_icon=False)
