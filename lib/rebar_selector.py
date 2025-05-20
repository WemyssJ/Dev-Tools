from Autodesk.Revit.UI import *
from Autodesk.Revit import DB
from Autodesk.Revit import UI


class RebarSelector:
    def __init__(self, doc, uidoc):
        self.doc = doc
        self.uidoc = uidoc

    def is_rebar(self, obj):
        """Checks if object is Rebar type."""
        return obj.Category.BuiltInCategory == DB.BuiltInCategory.OST_Rebar

    def is_rebar_group(rebar_object):
        n_bars = rebar_object.NumberOfBarPositions
        if n_bars > 1:
            return True
        else:
            return False

    def return_rebars(self, selection):
        elements = []
        for e in selection:
            if self.is_rebar(e):
                elements.append(e)
        return elements

    def get_rebars(self):
        """Gets Rebar type objects from selected elements, if no objects selected
        triggers Pick Objects method"""
        # elements = []
        selection = [self.doc.GetElement(x) for x in self.uidoc.Selection.GetElementIds()]
        # If no object is selected prompt user to select
        if len(selection) < 1:
            selected_obj = self.uidoc.Selection.PickObjects(UI.Selection.ObjectType.Element, "Choose rebars")
            selection = [self.doc.GetElement(reference.ElementId) for reference in selected_obj]
        return self.return_rebars(selection)

    def get_all_rebars(self):
        """Gets Rebar type objects from selected elements, if no objects selected
        gets all rebars in view"""
        selection = [self.doc.GetElement(x) for x in self.uidoc.Selection.GetElementIds()]
        # If no object is selected get all rebars
        if len(selection) < 1:
            elements = (
                DB.FilteredElementCollector(self.doc)
                .OfCategory(DB.BuiltInCategory.OST_Rebar)
                .WhereElementIsNotElementType()
            )
        else:
            elements = []
            for e in selection:
                if self.is_rebar(e):
                    elements.append(e)
        return elements

    def get_all_model_rebars(self):
        """Gets Rebar all rebars in view"""
        elements = (
            DB.FilteredElementCollector(self.doc)
            .OfCategory(DB.BuiltInCategory.OST_Rebar)
            .WhereElementIsNotElementType()
        )
        return elements
