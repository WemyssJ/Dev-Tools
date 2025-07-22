__doc__ = "Select rebar type in view."
__title__ = "Same Size Bar"
__author__ = "Wolinski"
from Autodesk.Revit import DB
from Autodesk.Revit.UI import *
from Autodesk.Revit.DB import *
import clr

clr.AddReference("System.Windows.Forms")
#clr.AddReference("Ironpython.Wpf")

from System import Windows
from pyrevit import script
from pyrevit.forms import WPFWindow
from System.Collections.Generic import List
from rebar_selector import RebarSelector
import wpf

# from pyrevit import UI

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
view = doc.ActiveView

xaml_file = script.get_bundle_file("view.xaml")

rebar_type_collector = (
    DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Rebar).WhereElementIsElementType()
)


rebar_types = {}

# Get all availble in doc RebarType names
for rebartype in rebar_type_collector:
    if isinstance(rebartype, DB.Structure.RebarBarType):
        name_param = rebartype.LookupParameter("Type Name")
        if name_param not in rebar_types:
            rebar_types[name_param.AsString()] = rebartype.Id


rs = RebarSelector(doc, uidoc)
rebar_collector = rs.get_all_rebars()


class MainWindow(WPFWindow):
    def __init__(self, xaml_file):
        WPFWindow.__init__(self, xaml_file)
        # TODO: Improve sorting
        self.cmbBox.ItemsSource = sorted(key for key in rebar_types)
        self.ShowDialog()

    def _get_rebars_id_of_type(self, rebar_collector, type_id):
        rebar_ids = []
        for rebar in rebar_collector:
            if rebar.GetTypeId() == type_id:
                rebar_ids.append(rebar.Id)
        return rebar_ids

    def select_rebar_type(self, sender, args):
        idlist = List[DB.ElementId]()
        name_to_select = self.cmbBox.SelectedItem
        id_type = rebar_types[name_to_select]
        # idlist.Add(
        #     self.get_rebars_id_of_type(rebar_collector=rebar_collector, type_id=id_type)
        # )
        for x in self._get_rebars_id_of_type(rebar_collector=rebar_collector, type_id=id_type):
            idlist.Add(x)
        uidoc.Selection.SetElementIds(idlist)
        self.Close()

    def window_close(self, sender, args):
        self.Close()


window = MainWindow(xaml_file=xaml_file)
