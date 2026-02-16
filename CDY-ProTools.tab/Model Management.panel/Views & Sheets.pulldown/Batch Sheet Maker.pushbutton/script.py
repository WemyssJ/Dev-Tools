# -*- coding: utf-8 -*-
import os
import sys
import re
import clr
from pyrevit import coreutils, revit, DB, forms, script

##############################################################################################
# TELEMETRY IMPORTS
##############################################################################################
lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'lib'))
if lib_path not in sys.path:
    sys.path.append(lib_path)
import telemetry_auto

tool_name = os.path.basename(os.path.dirname(__file__))
TOOL_NAME = tool_name.replace(".pushbutton", "")
telemetry_auto.log_tool_usage(TOOL_NAME)
##############################################################################################

logger = script.get_logger()


# ----------------- DRAWING NUMBER PARSER -----------------
def parse_drawing_number(drawing_number):
    """
    Example drawing number: 13914-CDY-AA-FN-DR-S-101010
    Returns dictionary mapping to Revit sheet parameters.
    """
    parts = drawing_number.split('-')
    if len(parts) < 7:
        raise ValueError('Invalid drawing number format: {0}'.format(drawing_number))

    return {
        "Project Number": parts[0],
        "Originator": parts[1],
        "Functional Breakdown": parts[2],
        "Spatial Breakdown": parts[3],
        "Form": parts[4],
        "Discipline": parts[5],
        "Sheet Number": parts[6]
    }


# ----------------- MAIN WINDOW CLASS -----------------
class BatchSheetMakerWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)
        self._sheet_dict = {}  # {sheet_num: sheet_name}
        self._titleblock_id = None
        self._namingProtocol = False
        self.sheets_tb.Focus()

    # ----------------- PROCESS PASTED DATA -----------------
    def _process_sheet_code(self):
        for sheet_code in str(self.sheets_tb.Text).split('\n'):
            if coreutils.is_blank(sheet_code):
                continue

            if '\t' not in sheet_code:
                logger.Warning('Sheet name must be separated from sheet number by a single tab: {0}'.format(sheet_code))
                return False

            sheet_code = re.sub('\t+', '\t', sheet_code)
            sheet_code = sheet_code.replace('\n', '').replace('\r', '')
            num, name = sheet_code.split('\t')
            try:
                for range_num in coreutils.extract_range(num):
                    self._sheet_dict[range_num] = name
            except Exception, range_err:
                logger.Error(str(range_err))
                return False
        return True

    # ----------------- TITLEBLOCK SELECTION -----------------
    def _ask_for_titleblock(self):
        tblock = forms.select_titleblocks(doc=revit.doc)
        if tblock is not None:
            self._titleblock_id = tblock
            return True
        return False

    # ----------------- CREATE SHEET -----------------
    def _create_sheet(self, sheet_num, sheet_name):
        t = DB.Transaction(revit.doc, 'Create Sheet')
        try:
            t.Start()
            new_sheet = DB.ViewSheet.Create(revit.doc, self._titleblock_id)
            new_sheet.Name = sheet_name
            new_sheet.SheetNumber = sheet_num

            # Only set parameters if real sheet and checkbox is checked
            if self._namingProtocol:
                try:
                    param_values = parse_drawing_number(sheet_num)
                    for param_name in param_values:
                        value = param_values[param_name]
                        param = new_sheet.LookupParameter(param_name)
                        if param and not param.IsReadOnly:
                            param.Set(value)
                except Exception, e:
                    logger.Warning('Could not set parameters for {0}: {1}'.format(sheet_num, e))

            t.Commit()
        except Exception, create_err:
            t.RollBack()
            logger.Error('Error creating sheet {0}:{1} | {2}'.format(sheet_num, sheet_name, create_err))

    # ----------------- CREATE SHEETS ENTRY POINT -----------------
    def create_sheets(self, sender, args):
        self.Close()

        # Checkbox now controls whether to parse drawing numbers
        self._namingProtocol = bool(self.NamingProtocol_cb.IsChecked)

        # Process pasted data
        if not self._process_sheet_code():
            logger.Error("Aborted: invalid TextBox input")
            script.exit()

        # Ask for titleblock if creating sheets
        if self.sheet_cb.IsChecked:
            if not self._ask_for_titleblock():
                script.exit()
            create_func = self._create_sheet
            transaction_msg = 'Batch Create Sheets'

        # Batch creation
        tg = DB.TransactionGroup(revit.doc, transaction_msg)
        tg.Start()
        for sheet_num in self._sheet_dict:
            sheet_name = self._sheet_dict[sheet_num]
            logger.debug('Creating Sheet: {0}:{1}'.format(sheet_num, sheet_name))
            create_func(sheet_num, sheet_name)
        tg.Assimilate()


# ----------------- RUN -----------------
BatchSheetMakerWindow('BatchSheetMakerWindow.xaml').ShowDialog()
