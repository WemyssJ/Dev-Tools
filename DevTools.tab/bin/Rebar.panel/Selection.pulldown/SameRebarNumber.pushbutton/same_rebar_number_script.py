__doc__ = "Select all same number rebars based on selected rebar object."
__title__ = "Same RN"
__author__ = "MWolinski"
import Autodesk
from Autodesk.Revit import DB
from Autodesk.Revit.UI import *
from Autodesk.Revit.DB import *
from rebar_selector import RebarSelector
from System.Collections.Generic import List

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
view = doc.ActiveView

rs = RebarSelector(doc, uidoc)
rebar_collector = rs.get_rebars()


# Get rebar numbers from collector
def get_selected_numbers(rebar_collector):
    rebar_numbers = {}
    for rebar in rebar_collector:
        number = rebar.LookupParameter("Rebar Number").AsString()
        partition = rebar.LookupParameter("Partition").AsString()
        # rebar_numbers.append([number, partition])
        rebar_numbers.update({number: partition})
    return rebar_numbers


# Loop through all rebars and find their id's
all_rebars = rs.get_all_model_rebars()

rebar_numbers = get_selected_numbers(rebar_collector)

idlist = List[DB.ElementId]()

for rebar in all_rebars:
    number = rebar.LookupParameter("Rebar Number").AsString()
    partition = rebar.LookupParameter("Partition").AsString()
    if number in rebar_numbers.keys() and partition == rebar_numbers[number]:
        idlist.Add(rebar.Id)


uidoc.Selection.SetElementIds(idlist)
