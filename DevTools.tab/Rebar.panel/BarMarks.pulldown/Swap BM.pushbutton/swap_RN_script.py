__doc__ = "Select all rebars with the same partition as the selected rebar(s) and move them to a TEMP partition, then restore them by Rebar Number."
__title__ = "Swap BM"
__author__ = "Joe Wemyss"

import Autodesk
from Autodesk.Revit import DB
from Autodesk.Revit.UI import *
from Autodesk.Revit.DB import *
from rebar_selector import RebarSelector
from System.Collections.Generic import List

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
view = doc.ActiveView

rs = RebarSelector(doc, uidoc)
rebar_collector = rs.get_rebars()

# Step 1: Get all unique partitions from selected rebars
def get_selected_partitions(rebar_collector):
    selected_partitions = set()
    for rebar in rebar_collector:
        partition = rebar.LookupParameter("Partition").AsString()
        if partition:
            selected_partitions.add(partition)
    return selected_partitions

# Step 2: WPF popup to get new rebar number (placeholder function)
def get_new_rebarNumber():
    newRebarNumber = "5"
    return newRebarNumber

# Step 3: Find all rebars with the same partition(s), regardless of Rebar Number
def get_rebars_with_same_partitions(selected_partitions):
    all_rebars = rs.get_all_model_rebars()
    matching_rebars = []

    for rebar in all_rebars:
        partition = rebar.LookupParameter("Partition").AsString()
        if partition in selected_partitions:
            matching_rebars.append(rebar)

    return matching_rebars

# Step 4: Swap their partition to a temporary one
def swap_rebar_temp_partition(rebars):
    t = Transaction(doc, "Swap to TEMP partition")
    t.Start()
    for rebar in rebars:
        current_partition = rebar.LookupParameter("Partition").AsString()
        new_partition = current_partition + "_TEMP"
        param = rebar.get_Parameter(BuiltInParameter.NUMBER_PARTITION_PARAM)
        if param and not param.IsReadOnly:
            param.Set(new_partition)
    t.Commit()

# Step 5: check to see if any rebar in Rebars has the Rebar Number = newRebarNumber
def check_for_rebar_number(rebars, target_rebar_number):
    for rebar in rebars:
        rebar_number = rebar.LookupParameter("Rebar Number").AsString()
        if rebar_number == target_rebar_number:
            return True
    return False

# Step 6: Add rebars back to original partition 1 by 1 in sequential Rebar Number order
def restore_rebars_to_original_partition(rebars):
    # Sort by Rebar Number (assumed numeric, fallback to string if necessary)
    def get_rebar_number(rebar):
        number = rebar.LookupParameter("Rebar Number").AsString()
        try:
            return int(number)
        except:
            return number  # fallback to string comparison

    sorted_rebars = sorted(rebars, key=get_rebar_number)

    t = Transaction(doc, "Restore Original Partition")
    t.Start()
    for rebar in sorted_rebars:
        # Get the TEMP partition name
        temp_partition = rebar.LookupParameter("Partition").AsString()
        if temp_partition and temp_partition.endswith("_TEMP"):
            original_partition = temp_partition.replace("_TEMP", "")
            param = rebar.get_Parameter(BuiltInParameter.NUMBER_PARTITION_PARAM)
            if param and not param.IsReadOnly:
                param.Set(original_partition)
    t.Commit()


# Run the process
selected_partitions = get_selected_partitions(rebar_collector)
matching_rebars = get_rebars_with_same_partitions(selected_partitions)
swap_rebar_temp_partition(matching_rebars)
#new_rebar_number = get_new_rebarNumber()
#restore_rebars_to_original_partition(matching_rebars)

# to do:
# 1. add WPF interface for new BM
# 2. add bars back in order (swapping positions where required)
# 3. Limit step 1 to a single bar to be selected



