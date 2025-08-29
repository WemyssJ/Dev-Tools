__doc__ = "Calculate rebar weight to concrete volume ratio. If multiple elements are selected, ratio is computed as sum.\
        You can pre-select element or pick after script is triggered."
__title__ = "Rebar ratio"
__author__ = "MWolinski"
from Autodesk.Revit import DB
from Autodesk.Revit import UI
from Autodesk.Revit.UI import *
from Autodesk.Revit.DB import *
from pyrevit import forms
from rebar_selector import RebarSelector

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
view = doc.ActiveView

# TODO: if user selects element and rebars, ignore rebars, filter only valid formwork
# TODO: if no valid elements in selection raise error


def get_objects(doc, uidoc):
    """Gets selected objects or prompts for selection"""
    selection = [doc.GetElement(x) for x in uidoc.Selection.GetElementIds()]
    # If no object is selected prompt user to select
    if len(selection) < 1:
        selected_obj = uidoc.Selection.PickObjects(UI.Selection.ObjectType.Element, "Choose elements")
        selection = [doc.GetElement(reference.ElementId) for reference in selected_obj]
    return selection


def can_host_rebar(element):
    """Verifies if element is valid and can host rebars
        Arguments:
        element(Element)
    Returns:
        boolean"""
    can_host = element.get_Parameter(DB.BuiltInParameter.DPART_CAN_HOST_REBAR).AsInteger()
    if can_host == 1:
        return True
    else:
        message = "Operation failed!\n" + "One of the selected elements cannot host rebar."
        forms.alert(msg=message, ok=True, exitscript=True)
        return False


def get_element_dependent_rebars(element):
    """Finds all dependent rebars of the element:
    Arguments:
        element(Element)
    Returns:
        list[Rebar]"""
    filter = DB.ElementClassFilter(DB.Structure.Rebar)
    dependent_elements = element.GetDependentElements(filter)
    rebars = []
    for id in dependent_elements:
        # rebar = doc.GetElement(id)
        rebars.append(doc.GetElement(id))
    return rebars


def get_total_rebar_mass(rebars):
    """Calculates total mass of rebars
    Arguments:
        rebars(list[Rebar])
    Returns:
        mass(float) - mass in kg"""
    masses = []
    for rebar in rebars:
        # do stuff
        R_O = 7.85e-3  # kg/cm3
        FEET3_TO_CM3 = 28316.832082557
        volume = rebar.Volume * FEET3_TO_CM3  # basic value comes as feet^3
        mass = volume * R_O
        masses.append(mass)
    return sum(masses)


def calculate_ratio(element, rebars):
    """Calculates ratio
    Arguments:
        element(Element)
        rebars(list[Rebar])
    Returns:
        list[volume(float) in m3,total_rebar_mass(float) in kg, ratio(float) in kg/m3"""
    FEET3_TO_M3 = 0.02831683208256
    volume = (
        element.get_Parameter(DB.BuiltInParameter.HOST_VOLUME_COMPUTED).AsDouble() * FEET3_TO_M3
    )  # basic value comes as feet^3
    if volume == 0:
        raise ZeroDivisionError
    total_rebar_mass = get_total_rebar_mass(rebars)
    ratio = round(total_rebar_mass / volume, 2)
    return [volume, total_rebar_mass, ratio]


# Main logic
elements = get_objects(doc, uidoc)
if len(elements) > 1:
    volumes = []
    rebar_masses = []
    for element in elements:
        if can_host_rebar(element):
            rebars = get_element_dependent_rebars(element)
            volume, total_mass, _ = calculate_ratio(element, rebars)
            volumes.append(volume)
            rebar_masses.append(total_mass)
    total_volume = sum(volumes)
    total_rc_mass = sum(rebar_masses)
    total_ratio = round(total_rc_mass / total_volume, 2)
    print("Concrete volume: {} m3".format(total_volume))
    print("Total rebar mass: {} kg".format(total_rc_mass))
    print("Ratio: {} kg/m3".format(total_ratio))

elif len(elements) == 1:
    if can_host_rebar(elements[0]):
        rebars = get_element_dependent_rebars(elements[0])
        volume, total_rc_mass, ratio = calculate_ratio(elements[0], rebars)
        print("Concrete volume: {} m3".format(volume))
        print("Total rebar mass: {} kg".format(total_rc_mass))
        print("Ratio: {} kg/m3".format(ratio))
