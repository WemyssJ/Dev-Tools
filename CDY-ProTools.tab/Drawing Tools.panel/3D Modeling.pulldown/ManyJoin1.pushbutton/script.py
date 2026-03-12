# -*- coding: utf-8 -*-
__title__ = "Join Intersecting\nSelection"
__author__ = "Craddys Tools"

from Autodesk.Revit.DB import *
from Autodesk.Revit.UI.Selection import ObjectType
from Autodesk.Revit.Exceptions import OperationCanceledException
from pyrevit import revit, script


doc = revit.doc
uidoc = revit.uidoc


# -----------------------------------------------------------
# Bounding box intersection test
# -----------------------------------------------------------
def bboxes_intersect(bb1, bb2):

    if not bb1 or not bb2:
        return False

    return (bb1.Min.X <= bb2.Max.X and bb1.Max.X >= bb2.Min.X and
            bb1.Min.Y <= bb2.Max.Y and bb1.Max.Y >= bb2.Min.Y and
            bb1.Min.Z <= bb2.Max.Z and bb1.Max.Z >= bb2.Min.Z)


# -----------------------------------------------------------
# Range selection (window / multi select)
# -----------------------------------------------------------
try:

    refs = uidoc.Selection.PickObjects(
        ObjectType.Element,
        "Window select elements or groups. Click Finish when done."
    )

except OperationCanceledException:
    script.exit()


elements = []

for ref in refs:

    el = doc.GetElement(ref.ElementId)

    if isinstance(el, Group):

        for id in el.GetMemberIds():
            member = doc.GetElement(id)
            if member:
                elements.append(member)

    else:
        elements.append(el)


# remove duplicates
elements = list(set(elements))

if len(elements) < 2:
    script.exit()


# -----------------------------------------------------------
# Join geometry
# -----------------------------------------------------------
joined = 0

t = Transaction(doc, "Join Intersecting Elements")
t.Start()

for i in range(len(elements)):

    e1 = elements[i]
    bb1 = e1.get_BoundingBox(None)

    for j in range(i + 1, len(elements)):

        e2 = elements[j]
        bb2 = e2.get_BoundingBox(None)

        if not bboxes_intersect(bb1, bb2):
            continue

        try:

            if not JoinGeometryUtils.AreElementsJoined(doc, e1, e2):

                JoinGeometryUtils.JoinGeometry(doc, e1, e2)
                joined += 1

        except:
            pass


t.Commit()

print("{} joins created.".format(joined))