__doc__ = "WIP - swap BM (rebar number) of selected rebar"
__title__ = "Swap BM"
__author__ = "Joe Wemyss"

import uuid
import re
from Autodesk.Revit.DB import *
from rebar_selector import RebarSelector
from System.Collections.Generic import List

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
view = doc.ActiveView

rs = RebarSelector(doc, uidoc)
selected_rebars = rs.get_rebars()

def get_selected_partitions(rebars):
    partitions = set()
    for rebar in rebars:
        partition = rebar.LookupParameter("Partition").AsString()
        if partition:
            partitions.add(partition)
    return partitions

def get_rebars_with_same_partitions(partitions):
    all_rebars = rs.get_all_model_rebars()
    return [
        rebar for rebar in all_rebars
        if rebar.LookupParameter("Partition").AsString() in partitions
    ]

def create_temp_partition_map(partitions):
    unique_suffix = "_TEMP_" + str(uuid.uuid4())[:8]
    return {p: p + unique_suffix for p in partitions}

def swap_to_temp_partition(rebars, partition_map):
    t = Transaction(doc, "Move to TEMP partition")
    t.Start()
    for rebar in rebars:
        partition = rebar.LookupParameter("Partition").AsString()
        temp_partition = partition_map.get(partition)
        param = rebar.get_Parameter(BuiltInParameter.NUMBER_PARTITION_PARAM)
        if param and not param.IsReadOnly:
            param.Set(temp_partition)

    print("Rebars moved to temporary Partition.")
    t.Commit()

def sort_rebars_by_number(rebars):
    def get_sort_key(rebar):
        value = rebar.LookupParameter("Rebar Number").AsString() or ""
        match = re.match(r"(\d+)", value)
        return int(match.group(1)) if match else value
    return sorted(rebars, key=get_sort_key)


def restore_to_original_partition(rebars, partition_map):
    t = Transaction(doc, "Restore Original Partition for Rebar")
    t.Start()
    for rebar in sort_rebars_by_number(rebars):
        current_partition = rebar.LookupParameter("Partition").AsString()
        for orig, temp in partition_map.items():
            if current_partition == temp:
                param = rebar.get_Parameter(BuiltInParameter.NUMBER_PARTITION_PARAM)
                if param and not param.IsReadOnly:
                    
                    param.Set(orig)
                    
    print("Rebars restored to original partition.")
    t.Commit()

def main():
    selected_partitions = get_selected_partitions(selected_rebars)
    if not selected_partitions:
        print("No valid partitions found in selected rebars.")
        return

    all_rebars = get_rebars_with_same_partitions(selected_partitions)
    if not all_rebars:
        print("No matching rebars found.")
        return


    partition_map = create_temp_partition_map(selected_partitions)
    swap_to_temp_partition(all_rebars, partition_map)
    restore_to_original_partition(all_rebars, partition_map)

    

main()

# to do:
# 1. add WPF interface for new BM
# 2. add bars back in order (swapping positions where required and allowing for gaps)
# 3. Limit step 1 to a single bar to be selected



