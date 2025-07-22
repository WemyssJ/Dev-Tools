__doc__ = "Select all same number rebars based on selected rebar object."
__title__ = "GetMass"
__author__ = "MWolinski"
import Autodesk
from Autodesk.Revit import DB
from Autodesk.Revit.UI import *
from Autodesk.Revit.DB import *
from rebar_selector import RebarSelector
from rebar_cog import RebarCoG

ROUNDING = 2

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
view = doc.ActiveView


rs = RebarSelector(doc, uidoc)
rebar_collector = rs.get_rebars()

rebar_cog = RebarCoG(rebar_collector)

mass = rebar_cog.get_cog()[1]

mass_text = "Total mass: " + str(round(mass, ROUNDING)) + " kg."

print(mass_text)
