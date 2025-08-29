__doc__ = "Syncronise Rebar Number to Schedule Mark - to use for FREEZING rebar after issue so that BM's can't change automatically"
__title__ = "Sync BM"
__author__ = "Joe Wemyss"

from Autodesk.Revit.DB import Transaction, BuiltInParameter


doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument

# Your RebarSelector is assumed to work correctly:
from rebar_selector import RebarSelector
rs = RebarSelector(doc, uidoc)
rebar_collector = rs.get_rebars()

t = Transaction(doc, "Set Schedule Mark to Rebar Number")
t.Start()

for rebar in rebar_collector:
    # Get Rebar Number (string)
    rebarNumberParam = rebar.get_Parameter(BuiltInParameter.REBAR_NUMBER)
    scheduleMarkParam = rebar.get_Parameter(BuiltInParameter.REBAR_ELEM_SCHEDULE_MARK)
    
    if rebarNumberParam and scheduleMarkParam:
        rebarNumber = rebarNumberParam.AsString()
        if rebarNumber:  # Ensure it's not None or empty
            scheduleMarkParam.Set(rebarNumber)

t.Commit()
