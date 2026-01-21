#pylint: disable=E0401,C0103,C0111
from pyrevit import revit
from pyrevit import forms

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


revisions = forms.select_revisions(button_name='Create Sheet Set',
                                   multiple=True)
if revisions:
    if len(revisions) > 1:
        selected_switch = \
            forms.CommandSwitchWindow.show(['Matching ANY revision',
                                            'Matching ALL revisions'],
                                           message='Pick an option:')
    else:
        selected_switch = 'Matching ALL revisions'

    if selected_switch:
        match_any = (selected_switch == 'Matching ANY revision')
        with revit.Transaction('Create Revision Sheet Set'):
            rev_sheetset = \
                revit.create.create_revision_sheetset(revisions,
                                                      match_any=match_any)

        empty_sheets = []
        for sheet in rev_sheetset:
            if revit.query.is_sheet_empty(sheet):
                empty_sheets.append(sheet)

        if empty_sheets:
            print('These sheets do not have any model contents and seem to be '
                  'placeholders for other content:')
            for esheet in empty_sheets:
                revit.report.print_sheet(esheet)
