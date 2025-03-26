# import pyrevit libraries
from pyrevit import forms,revit,DB,script
# print utility library
from guRoo_expUtils import *

# make sure you can print, construct print path and make directory
expUtils_canPrint()
dirPath = expUtils_getDir() + "\\" + expUtils_getFolder("_PDF")
expUtils_ensureDir(dirPath)

# get document
doc = revit.doc
uidoc = revit.uidoc

# ask user for sheets
sheets = forms.select_sheets(title='Select Sheets', include_placeholder = False, use_selection = True)

# ask user for Naming Protocol
namingProtocols = ['Craddys: BS EN ISO 19650-2-2018 (+A1 2021)','Craddys: BS EN ISO 19650-2-2018','Aldi BEP & Parameters', 'Morgan Sindall: BS EN ISO 19650-2-2018 (+A1 2021)']
namingProtocol = forms.SelectFromList.show(namingProtocols, button_name='Select Naming Protocol')

# display primary UI if sheets found
if sheets:
	# open the directory
	expUtils_openDir(dirPath)
	# export the sheets
	with forms.ProgressBar(step=1, title='Exporting sheets... ' + '{value} of {max_value}', cancellable=True) as pb1:
		pbTotal1 = len(sheets)
		pbCount1 = 1
		# Make print options
		opts = expUtils_pdfOpts()
		# Export each sheet selected by user
		for s in sheets:
			if pb1.cancelled:
				break
			else:
				# Export sheet to PDF
				expUtils_exportSheetPdf(dirPath,s,opts,doc,uidoc)
				# Update progress bar
				pb1.update_progress(pbCount1, pbTotal1)
				pbCount1 += 1
	# Cancel check
	if pb1.cancelled:
		forms.alert("Export process cancelled.", title= "Script cancelled")
	else:
		forms.alert("Export process complete.", title= "Script finished", warn_icon=False)
