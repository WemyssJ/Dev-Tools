from pyrevit import revit, DB, forms

doc = revit.doc
uidoc = revit.uidoc

selection = uidoc.Selection.GetElementIds()

if not selection:
    forms.alert('Please select a viewport on a sheet.', title='No selection', warn_icon=True)
else:
    selected_element = doc.GetElement(list(selection)[0])

    if isinstance(selected_element, DB.Viewport):
        placed_view = doc.GetElement(selected_element.ViewId)

        # Try parent view (e.g. for callouts)
        try:
            parent_view_id = placed_view.get_Parameter(DB.BuiltInParameter.SECTION_PARENT_VIEW_NAME).AsElementId()
            if parent_view_id and parent_view_id.IntegerValue != -1:
                parent_view = doc.GetElement(parent_view_id)
                uidoc.RequestViewChange(parent_view)
            else:
                raise Exception("No parent view.")
        except:
            # Try primary view (e.g. for dependent views)
            try:
                primary_view_id = placed_view.GetPrimaryViewId()
                if primary_view_id and primary_view_id.IntegerValue != -1:
                    primary_view = doc.GetElement(primary_view_id)
                    uidoc.RequestViewChange(primary_view)
                else:
                    raise Exception("No primary view.")
            except:
                # Fallback: just open the placed view itself
                uidoc.RequestViewChange(placed_view)
    else:
        forms.alert('Selected element is not a viewport.', title='Invalid selection', warn_icon=True)
