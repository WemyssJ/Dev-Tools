# -*- coding: utf-8 -*-
__title__ = "Align Scope Box to Grid"
__author__ = "Dave Barron"

from Autodesk.Revit.DB import *
from Autodesk.Revit.UI.Selection import ObjectType
import math

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
active_view = doc.ActiveView

# --------------------------------------------------
# Validation & Setup
# --------------------------------------------------
if not isinstance(active_view, ViewPlan):
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
    raise Exception("First selection must be a Scope Box.")

print("Select a Grid...")
grid = pick_element("Pick a Grid to align to")
if not grid or not isinstance(grid, Grid):
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
edge_found = False
edge_direction = None
bbox_center = None
edge_line = None
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
                print("DEBUG - Found horizontal edge: {} to {}".format(p1, p2))
                print("DEBUG - Edge direction: {}".format(edge_vec.Normalize()))

if not horizontal_edges:
    raise Exception("Could not find horizontal edges in Scope Box geometry.")

# Use the longest horizontal edge (most likely to be a perimeter edge)
edge_line, edge_direction, edge_length = max(horizontal_edges, key=lambda x: x[2])
print("DEBUG - Using longest horizontal edge with length: {}".format(edge_length))

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
# DEBUG: Draw the extracted edge as a model line
# --------------------------------------------------
t_debug = Transaction(doc, "Debug - Draw Scope Box Edge")
t_debug.Start()

if edge_line:
    p1 = edge_line.GetEndPoint(0)
    p2 = edge_line.GetEndPoint(1)
    try:
        # Get the active view's sketch plane
        sketch_plane = doc.ActiveView.SketchPlane
        model_line = doc.Create.NewModelCurve(
            Line.CreateBound(p1, p2),
            sketch_plane
        )
        print("DEBUG - Model line created from {} to {}".format(p1, p2))
    except Exception as e:
        print("DEBUG - Could not create model line: {}".format(str(e)))
        # Try alternate method - create as detail line instead
        try:
            detail_line = doc.ActiveView.Sketch.NewModelCurve(
                Line.CreateBound(p1, p2),
                None
            )
            print("DEBUG - Detail line created as fallback")
        except:
            print("DEBUG - Could not create detail line either")

t_debug.Commit()

# --------------------------------------------------
# Calculate Required Rotation Angle
# --------------------------------------------------
# Project edge direction to horizontal plane (X-Y)
edge_2d = XYZ(edge_direction.X, edge_direction.Y, 0).Normalize()
grid_2d = XYZ(grid_dir.X, grid_dir.Y, 0).Normalize()

print("DEBUG - Edge 2D direction: {}".format(edge_2d))
print("DEBUG - Grid 2D direction: {}".format(grid_2d))

# Calculate angle
angle = edge_2d.AngleTo(grid_2d)
print("DEBUG - Angle between edge and grid: {:.4f} radians = {:.2f} degrees".format(angle, math.degrees(angle)))

# Determine rotation direction using cross product
cross = edge_2d.CrossProduct(grid_2d)
print("DEBUG - Cross product Z: {}".format(cross.Z))
if cross.Z < 0:
    angle = -angle
    print("DEBUG - Cross product negative, angle adjusted to: {:.2f} degrees".format(math.degrees(angle)))

# --------------------------------------------------
# Apply Rotation
# --------------------------------------------------
t = Transaction(doc, "Align Scope Box to Grid")
t.Start()

# Rotation axis: vertical line through scope box center
rotation_axis = Line.CreateBound(bbox_center, bbox_center + XYZ.BasisZ)
ElementTransformUtils.RotateElement(doc, scope_box.Id, rotation_axis, angle)

t.Commit()

print("SUCCESS: Scope Box aligned to Grid!")
print("Rotation applied: {:.2f} degrees".format(math.degrees(angle)))