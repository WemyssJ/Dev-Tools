from Autodesk.Revit import DB
import math
from System import Type
from System.Collections.Generic import List
import clr


def visualize_point(doc, center, diameter):
    """Creates a sphere in 3D space to visualize given point
    Arguments:
        doc: Document
        center: DB.XYZ
        diameter: float, units in feet (conversion *1/304.8)"""

    radius = diameter / 2
    profile_00 = center
    profile_plus = center + DB.XYZ(0, radius, 0)
    profile_minus = center - DB.XYZ(0, radius, 0)
    profile = []
    profile.append(DB.Line.CreateBound(profile_plus, profile_minus))
    profile.append(DB.Arc.Create(profile_minus, profile_plus, center + DB.XYZ(radius, 0, 0)))
    curve_loop = DB.CurveLoop.Create(profile)
    options = DB.SolidOptions(DB.ElementId.InvalidElementId, DB.ElementId.InvalidElementId)
    frame = DB.Frame(center, DB.XYZ.BasisX, -1 * DB.XYZ.BasisZ, DB.XYZ.BasisY)

    curve_ilist = List[DB.CurveLoop]()
    curve_ilist.Add(curve_loop)
    sphere = DB.GeometryCreationUtilities.CreateRevolvedGeometry(frame, curve_ilist, 0, 2 * math.pi, options)

    shape_ilist = List[DB.GeometryObject]()
    shape_ilist.Add(sphere)

    t = DB.Transaction(doc, "Create sphere")

    t.Start()

    ds = DB.DirectShape.CreateElement(doc, DB.ElementId(DB.BuiltInCategory.OST_GenericModel))
    ds.SetShape(shape_ilist)

    t.Commit()
