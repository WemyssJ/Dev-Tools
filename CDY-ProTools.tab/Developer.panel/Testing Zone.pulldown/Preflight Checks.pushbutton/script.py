"""Run perflight checks on current model"""
# pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
from pyrevit import preflight
from pyrevit import forms
from pyrevit import script
from pyrevit import revit

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


logger = script.get_logger()
output = script.get_output()


def ask_for_preflight_checks():
    """Ask user for preflight tests and run one by one"""
    # ask user for test case
    selected_check = forms.SelectFromList.show(
        preflight.get_all_preflight_checks(),
        title="Select Preflight Check",
        button_name="Run Check",
        multiselect=False,
        info_panel=True,
        checked_only=True,
        height=400,
        width=750,
        item_template=forms.utils.load_ctrl_template(
            script.get_bundle_file("PreflightCheckTemplate.xaml")
        ),
    )

    if selected_check:
        logger.debug("Running: {}".format(selected_check))
        preflight.run_preflight_check(
            selected_check, doc=revit.doc, output=output
        )


if __name__ == "__main__":
    ask_for_preflight_checks()
