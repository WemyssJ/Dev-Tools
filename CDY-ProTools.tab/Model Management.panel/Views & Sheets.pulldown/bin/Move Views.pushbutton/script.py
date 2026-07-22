from pyrevit import HOST_APP
from pyrevit import revit, DB, UI
from pyrevit import forms
from pyrevit import script

##############################################################################################
# TELEMETRY IMPORTS #
##############################################################################################
# Only works IF specified TELEMETRY_JSON path exists within %AppData%\pyRevit\Extensions\BIMTools.extension\lib\telemetry_auto.py"
# Records tool usage by date & revit version
import os, sys

# Add lib folder for telemetry_auto
lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'lib'))
if lib_path not in sys.path:
    sys.path.append(lib_path)

import telemetry_auto

tool_name = os.path.basename(os.path.dirname(__file__)) 
TOOL_NAME = tool_name.replace(".pushbutton", "")
telemetry_auto.log_tool_usage(TOOL_NAME)
##############################################################################################

cursheet = revit.active_view
forms.check_viewtype(cursheet, DB.ViewType.DrawingSheet, exitscript=True)

dest_sheet = forms.select_sheets(title='Select Target Sheets',
                                 button_name='Select Sheets',
                                 multiple=False,
                                 include_placeholder=False,
                                 use_selection=True)

selected_vports = []
if dest_sheet:
    sel = revit.pick_elements()
    for el in sel:
        selected_vports.append(el)

    results = []

    if len(selected_vports) > 0:
        with revit.Transaction('Move Viewports'):
            # Collect existing detail numbers on destination sheet
            existing_detail_numbers = set()
            dest_vports = DB.FilteredElementCollector(revit.doc, dest_sheet.Id)\
                            .OfClass(DB.Viewport)\
                            .ToElements()
            for v in dest_vports:
                num = v.get_Parameter(DB.BuiltInParameter.VIEWPORT_DETAIL_NUMBER).AsString()
                if num:
                    existing_detail_numbers.add(num)

            for vp in selected_vports:
                if isinstance(vp, DB.Viewport):
                    viewId = vp.ViewId
                    vpCenter = vp.GetBoxCenter()
                    vpTypeId = vp.GetTypeId()
                    view = revit.doc.GetElement(viewId)
                    viewname = view.Name

                    original_detail_number = vp.get_Parameter(DB.BuiltInParameter.VIEWPORT_DETAIL_NUMBER).AsString()

                    # Delete the original viewport
                    cursheet.DeleteViewport(vp)

                    # Create new viewport
                    nvp = DB.Viewport.Create(revit.doc, dest_sheet.Id, viewId, vpCenter)
                    nvp.ChangeTypeId(vpTypeId)

                    # Try to assign the same detail number
                    param = nvp.get_Parameter(DB.BuiltInParameter.VIEWPORT_DETAIL_NUMBER)
                    assigned_number = ""
                    if param and not param.IsReadOnly:
                        if original_detail_number not in existing_detail_numbers:
                            param.Set(original_detail_number)
                            assigned_number = original_detail_number
                            existing_detail_numbers.add(original_detail_number)
                            results.append("Detail: " + original_detail_number + " / View Name:" + viewname + " moved from sheet " + cursheet.SheetNumber + " to " + dest_sheet.SheetNumber + " and detail number preserved.")
                        else:
                            # Let Revit auto-assign a new detail number
                            assigned_number = param.AsString()
                            results.append("Detail: " + original_detail_number + " / View Name:" + viewname + " moved from sheet " + cursheet.SheetNumber + " to " + dest_sheet.SheetNumber + " with new detail number " + assigned_number + " (original '" + original_detail_number + "' already in use).")
                    else:
                        results.append("Detail: '" + viewname + "' moved but detail number could not be set.")

                elif isinstance(vp, DB.ScheduleSheetInstance):
                    nvp = DB.ScheduleSheetInstance.Create(revit.doc, dest_sheet.Id, vp.ScheduleId, vp.Point)
                    revit.doc.Delete(vp.Id)
                    results.append("Schedule '" + vp.Name + "' moved from sheet " + cursheet.SheetNumber + " to " + dest_sheet.SheetNumber + ".")

        # Print output summary
        output = script.get_output()
        output.print_md("### Move Viewport Results:")
        for line in results:
            output.print_md("- " + line)

    else:
        forms.alert('At least one viewport must be selected.')
else:
    forms.alert('You must select at least one sheet to add the selected viewports to.')
