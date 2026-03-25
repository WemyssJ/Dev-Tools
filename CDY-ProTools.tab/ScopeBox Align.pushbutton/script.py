# -*- coding: utf-8 -*-
__title__ = "Align Scope Box to Grid"
__author__ = "Dave Barron"

from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.UI.Selection import ObjectType
import math

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
active_view = doc.ActiveView

# --------------------------------------------------
# Validation & Setup
# --------------------------------------------------
if not isinstance(active_view, ViewPlan):
    error_dialog = TaskDialog("Invalid View")
    error_dialog.MainInstruction = "ERROR"
    error_dialog.MainContent = "This tool only works in Plan Views."
    error_dialog.Show()
    raise Exception("This tool only works in Plan Views.")

# --------------------------------------------------
# Helper: Check if element is a Scope Box
# --------------------------------------------------
def is_scope_box(element):
    """Check if element is a scope box by category."""
    try:
        category = element.Category
        return category and category.Name == "Scope Boxes"
    except:
        return False

# --------------------------------------------------
# Helper: Get element from selection
# --------------------------------------------------
def pick_element(prompt):
    """Pick an element from the viewport."""
    try:
        ref = uidoc.Selection.PickObject(ObjectType.Element, prompt)
        return doc.GetElement(ref.ElementId)
    except:
        return None

# --------------------------------------------------
# Get Scope Box and Grid
# --------------------------------------------------
print("Select a Scope Box...")
scope_box = pick_element("Pick a Scope Box")
if not scope_box or not is_scope_box(scope_box):
    error_dialog = TaskDialog("Invalid Selection")
    error_dialog.MainInstruction = "ERROR"
    error_dialog.MainContent = "First selection must be a Scope Box."
    error_dialog.Show()
    raise Exception("First selection must be a Scope Box.")

print("Select a Grid...")
grid = pick_element("Pick a Grid to align to")
if not grid or not isinstance(grid, Grid):
    error_dialog = TaskDialog("Invalid Selection")
    error_dialog.MainInstruction = "ERROR"
    error_dialog.MainContent = "Second selection must be a Grid."
    error_dialog.Show()
    raise Exception("Second selection must be a Grid.")

# --------------------------------------------------
# Get Grid Curve & Direction
# --------------------------------------------------
grid_curve = grid.Curve
grid_start = grid_curve.GetEndPoint(0)
grid_end = grid_curve.GetEndPoint(1)
grid_dir = (grid_end - grid_start).Normalize()

# --------------------------------------------------
# Extract Scope Box Geometry & Get Edge Direction
# --------------------------------------------------
geom_elem = scope_box.get_Geometry(Options())
if geom_elem is None:
    raise Exception("Could not extract geometry from Scope Box.")

# Find the first edge (line) in the geometry to get current orientation
horizontal_edges = []

for geom_item in geom_elem:
    if isinstance(geom_item, Line):
        # Get the first line's direction
        p1 = geom_item.GetEndPoint(0)
        p2 = geom_item.GetEndPoint(1)
        edge_vec = p2 - p1
        
        if edge_vec.GetLength() > 0.01:
            # Only consider horizontal edges (Z component is 0 or very small)
            if abs(edge_vec.Z) < 0.01:
                horizontal_edges.append((geom_item, edge_vec.Normalize(), edge_vec.GetLength()))

if not horizontal_edges:
    raise Exception("Could not find horizontal edges in Scope Box geometry.")

# Use the longest horizontal edge (most likely to be a perimeter edge)
edge_line, edge_direction, edge_length = max(horizontal_edges, key=lambda x: x[2])

if edge_direction is None:
    raise Exception("Could not find edges in Scope Box geometry.")

# Get bounding box for center point
bbox = scope_box.get_BoundingBox(active_view)
if bbox is None:
    bbox = scope_box.get_BoundingBox(None)

bbox_min = bbox.Min
bbox_max = bbox.Max
bbox_center = XYZ(
    (bbox_min.X + bbox_max.X) * 0.5,
    (bbox_min.Y + bbox_max.Y) * 0.5,
    (bbox_min.Z + bbox_max.Z) * 0.5
)

# --------------------------------------------------
# Calculate Required Rotation Angle
# --------------------------------------------------
# Project edge direction to horizontal plane (X-Y)
edge_2d = XYZ(edge_direction.X, edge_direction.Y, 0).Normalize()
grid_2d = XYZ(grid_dir.X, grid_dir.Y, 0).Normalize()

# Calculate angle
angle = edge_2d.AngleTo(grid_2d)

# Determine rotation direction using cross product
cross = edge_2d.CrossProduct(grid_2d)
if cross.Z < 0:
    angle = -angle

# --------------------------------------------------
# Apply Rotation
# --------------------------------------------------
t = Transaction(doc, "Align Scope Box to Grid")
t.Start()

# Rotation axis: vertical line through scope box center
rotation_axis = Line.CreateBound(bbox_center, bbox_center + XYZ.BasisZ)
ElementTransformUtils.RotateElement(doc, scope_box.Id, rotation_axis, angle)

t.Commit()

# Format the result message
rotation_degrees = math.degrees(angle)
result_message = "Scope Box has been successfully aligned to the Grid!\n\n"
result_message += "Rotation Applied: {:.2f}°".format(rotation_degrees)

# Show user-friendly dialog
dialog = TaskDialog("Scope Box Aligned")
dialog.MainInstruction = "SUCCESS"
dialog.MainContent = result_message
dialog.Show()

print("SUCCESS: Scope Box aligned to Grid!")
print("Rotation angle: {:.2f} degrees".format(rotation_degrees))