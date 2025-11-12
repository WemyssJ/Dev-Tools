"""
Split Structural Framing at Reference Planes (Manual Method)
Splits selected structural framing elements at intersections with reference planes
"""

__title__ = "Split Framing\nat Ref Planes"
__author__ = "Your Name"

from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Structure import StructuralType
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
from Autodesk.Revit.UI import TaskDialog
from pyrevit import forms
import sys
import time

# Get current document
doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument

# Selection filter for structural framing
class StructuralFramingFilter(ISelectionFilter):
    def AllowElement(self, elem):
        return elem.Category.Id.IntegerValue == int(BuiltInCategory.OST_StructuralFraming)
    
    def AllowReference(self, ref, point):
        return False

# Selection filter for reference planes
class ReferencePlaneFilter(ISelectionFilter):
    def AllowElement(self, elem):
        return isinstance(elem, ReferencePlane)
    
    def AllowReference(self, ref, point):
        return False

def get_intersection_points(beam_curve, plane_data_list):
    """Get actual XYZ intersection points between beam and planes"""
    p0 = beam_curve.GetEndPoint(0)
    p1 = beam_curve.GetEndPoint(1)
    
    intersection_points = []
    
    for pdata in plane_data_list:
        d0 = pdata['normal'].DotProduct(p0 - pdata['origin'])
        d1 = pdata['normal'].DotProduct(p1 - pdata['origin'])
        
        # Check if beam crosses plane
        if d0 * d1 <= 0.001 and abs(d1 - d0) >= 0.0001:
            t = -d0 / (d1 - d0)
            
            if 0.01 < t < 0.99:
                # Get actual intersection point
                point = XYZ(
                    p0.X + t * (p1.X - p0.X),
                    p0.Y + t * (p1.Y - p0.Y),
                    p0.Z + t * (p1.Z - p0.Z)
                )
                
                # Verify distance to plane
                dist = abs(pdata['normal'].DotProduct(point - pdata['origin']))
                if dist < 0.01:
                    intersection_points.append(point)
    
    return intersection_points

def split_beam_manual(beam, split_points, doc):
    """Manually split beam by creating new segments and deleting original"""
    if not split_points:
        return 0
    
    try:
        # Get beam properties
        loc_curve = beam.Location
        beam_curve = loc_curve.Curve
        beam_type_id = beam.GetTypeId()
        level_id = beam.LevelId
        
        # Sort points along beam
        p0 = beam_curve.GetEndPoint(0)
        sorted_points = sorted(split_points, key=lambda pt: p0.DistanceTo(pt))
        
        # Create all segment points
        all_points = [p0] + sorted_points + [beam_curve.GetEndPoint(1)]
        
        # Collect parameters to copy
        params_to_copy = {}
        for param in beam.Parameters:
            if not param.IsReadOnly and param.HasValue:
                try:
                    params_to_copy[param.Definition.Name] = param
                except:
                    pass
        
        # Create new beam segments
        new_beams = []
        for i in range(len(all_points) - 1):
            start = all_points[i]
            end = all_points[i + 1]
            
            # Skip if too short
            if start.DistanceTo(end) < 0.01:
                continue
            
            # Create new curve
            new_curve = Line.CreateBound(start, end)
            
            # Create new beam - NewFamilyInstance expects (Curve, Symbol, Level, StructuralType)
            beam_symbol = doc.GetElement(beam_type_id)
            new_beam = doc.Create.NewFamilyInstance(
                new_curve,
                beam_symbol,
                doc.GetElement(level_id),
                StructuralType.Beam
            )
            
            # Copy parameters
            for param_name, orig_param in params_to_copy.items():
                try:
                    new_param = new_beam.LookupParameter(param_name)
                    if new_param and not new_param.IsReadOnly:
                        storage_type = orig_param.StorageType
                        if storage_type == StorageType.Double:
                            new_param.Set(orig_param.AsDouble())
                        elif storage_type == StorageType.Integer:
                            new_param.Set(orig_param.AsInteger())
                        elif storage_type == StorageType.String:
                            val = orig_param.AsString()
                            if val:
                                new_param.Set(val)
                        elif storage_type == StorageType.ElementId:
                            new_param.Set(orig_param.AsElementId())
                except:
                    pass
            
            new_beams.append(new_beam)
        
        # Delete original beam
        doc.Delete(beam.Id)
        
        return len(new_beams) - 1  # Return number of splits (not segments)
        
    except Exception as e:
        print("Error splitting beam {}: {}".format(beam.Id, str(e)))
        return 0

# Main script
try:
    start_time = time.time()
    
    # Ask user which method to use
    method = forms.CommandSwitchWindow.show(
        ['Use Split() API (Slower, More Reliable)',
         'Create New Beams (Faster, May Lose Some Properties)'],
        message='Choose splitting method:'
    )
    
    if not method:
        sys.exit()
    
    use_split_api = (method == 'Use Split() API (Slower, More Reliable)')
    
    # Step 1: Select structural framing elements
    TaskDialog.Show("Select Framing", "Please select structural framing elements to split.")
    
    framing_refs = uidoc.Selection.PickObjects(
        ObjectType.Element,
        StructuralFramingFilter(),
        "Select structural framing elements"
    )
    
    if not framing_refs:
        TaskDialog.Show("Error", "No structural framing elements selected.")
        sys.exit()
    
    framing_elements = [doc.GetElement(ref.ElementId) for ref in framing_refs]
    
    # Step 2: Select reference planes
    TaskDialog.Show("Select Reference Planes", "Please select reference planes to use as split locations.")
    
    plane_refs = uidoc.Selection.PickObjects(
        ObjectType.Element,
        ReferencePlaneFilter(),
        "Select reference planes"
    )
    
    if not plane_refs:
        TaskDialog.Show("Error", "No reference planes selected.")
        sys.exit()
    
    ref_planes = [doc.GetElement(ref.ElementId) for ref in plane_refs]
    
    print("=" * 60)
    print("Processing {} beams with {} reference planes".format(
        len(framing_elements), len(ref_planes)))
    print("Method: {}".format("Split() API" if use_split_api else "Manual Creation"))
    
    # Pre-cache all plane data
    plane_data = []
    for ref_plane in ref_planes:
        plane = ref_plane.GetPlane()
        plane_data.append({
            'normal': plane.Normal,
            'origin': plane.Origin
        })
    
    # Pre-calculate ALL intersections
    beam_split_data = []
    beams_with_no_intersections = 0
    
    for beam in framing_elements:
        loc_curve = beam.Location
        if not isinstance(loc_curve, LocationCurve):
            continue
        
        beam_curve = loc_curve.Curve
        
        if use_split_api:
            # Calculate parameters for Split() API
            p0 = beam_curve.GetEndPoint(0)
            p1 = beam_curve.GetEndPoint(1)
            
            intersection_params = []
            
            for pdata in plane_data:
                d0 = pdata['normal'].DotProduct(p0 - pdata['origin'])
                d1 = pdata['normal'].DotProduct(p1 - pdata['origin'])
                
                if d0 * d1 <= 0.001 and abs(d1 - d0) >= 0.0001:
                    t = -d0 / (d1 - d0)
                    if 0.01 < t < 0.99:
                        test_point = beam_curve.Evaluate(t, True)
                        dist_to_plane = abs(pdata['normal'].DotProduct(test_point - pdata['origin']))
                        if dist_to_plane < 0.01:
                            intersection_params.append(t)
            
            if intersection_params:
                unique_params = []
                sorted_params = sorted(intersection_params)
                for p in sorted_params:
                    if not unique_params or abs(p - unique_params[-1]) > 0.001:
                        unique_params.append(p)
                
                beam_split_data.append({
                    'beam': beam,
                    'data': sorted(unique_params, reverse=True)
                })
            else:
                beams_with_no_intersections += 1
        else:
            # Get actual intersection points for manual method
            intersection_points = get_intersection_points(beam_curve, plane_data)
            
            if intersection_points:
                beam_split_data.append({
                    'beam': beam,
                    'data': intersection_points
                })
            else:
                beams_with_no_intersections += 1
    
    print("Found {} beams to split".format(len(beam_split_data)))
    
    if not beam_split_data:
        TaskDialog.Show("No Splits", "No beams intersect the selected reference planes.")
        sys.exit()
    
    # Start transaction
    t = Transaction(doc, "Split Structural Framing at Reference Planes")
    t.Start()
    
    total_splits_made = 0
    failed_splits = 0
    
    try:
        # Use pyRevit progress bar
        with forms.ProgressBar(title='Splitting Beams ({value} of {max_value})',
                               cancellable=True,
                               step=1) as pb:
            
            for idx, split_info in enumerate(beam_split_data):
                if pb.cancelled:
                    print("Operation cancelled by user")
                    t.RollBack()
                    TaskDialog.Show("Cancelled", "Operation cancelled by user.")
                    sys.exit()
                
                beam = split_info['beam']
                data = split_info['data']
                
                pb.update_progress(idx + 1, len(beam_split_data))
                
                if use_split_api:
                    # Use Split() API method
                    st = SubTransaction(doc)
                    st.Start()
                    
                    try:
                        for param in data:
                            try:
                                new_beam_id = beam.Split(param)
                                if new_beam_id and new_beam_id != ElementId.InvalidElementId:
                                    total_splits_made += 1
                                else:
                                    failed_splits += 1
                            except Exception as e:
                                failed_splits += 1
                        st.Commit()
                    except:
                        st.RollBack()
                else:
                    # Use manual creation method
                    splits = split_beam_manual(beam, data, doc)
                    if splits > 0:
                        total_splits_made += splits
        
        t.Commit()
        total_time = time.time() - start_time
        
        print("=" * 60)
        print("Complete: {} splits in {:.1f} seconds".format(total_splits_made, total_time))
        
        # Show results
        message = "Split operation complete!\n\n"
        message += "Beams processed: {}\n".format(len(beam_split_data))
        message += "Splits successful: {}\n".format(total_splits_made)
        if use_split_api:
            message += "Splits failed: {}\n".format(failed_splits)
        message += "Beams with no intersections: {}\n\n".format(beams_with_no_intersections)
        message += "Total time: {:.1f}s".format(total_time)
        
        TaskDialog.Show("Complete", message)
        
    except Exception as e:
        t.RollBack()
        TaskDialog.Show("Error", "An error occurred: " + str(e))
        import traceback
        print(traceback.format_exc())
        
except Exception as e:
    TaskDialog.Show("Error", "Script error: " + str(e))
    import traceback
    print(traceback.format_exc())