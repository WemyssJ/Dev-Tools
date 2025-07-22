__doc__ = "Make all bars obscured in view."
__title__ = "Obscure Bars"
__author__ = "Wolinski"
import Autodesk
from Autodesk.Revit import DB
from Autodesk.Revit.UI import *
from Autodesk.Revit.DB import *
from rebar_selector import RebarSelector

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
view = doc.ActiveView

rs = RebarSelector(doc, uidoc)
rebar_collector = rs.get_all_rebars()

x = False

t = DB.Transaction(doc, "ObscuredBars")
t.Start()
for rebar in rebar_collector:
    rebar.SetUnobscuredInView(view, x)
t.Commit()
