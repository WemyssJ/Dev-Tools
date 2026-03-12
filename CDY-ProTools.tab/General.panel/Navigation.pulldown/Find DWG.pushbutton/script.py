# import pyrevit libraries
from pyrevit import script,revit,DB

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

# Get active revit document
doc = revit.doc

# Get output for later linkifying
output = script.get_output()

# Get all images and their views
coll_cad = DB.FilteredElementCollector(doc).OfClass(DB.ImportInstance).ToElements()
typ_names = []

# Get CAD Type names
for c in coll_cad:
	typ = doc.GetElement(c.GetTypeId())
	n = DB.Element.Name.__get__(typ)
	typ_names.append(n)

set_name = list(set(typ_names))

# Group CAD by their names
lstId,lstLink,lstView = [],[],[]

for n in set_name:
	slstId   = []
	slstLink = []
	slstView = []
	for i,na in zip(coll_cad,typ_names):
		if na == n:
			slstId.append(i.Id)
			if i.IsLinked:
				slstLink.append("Linked instance: ")
			else:
				slstLink.append("Import instance: ")
			if i.ViewSpecific:
				slstView.append(i.OwnerViewId)
			else:
				slstView.append("")
	lstId.append(slstId)
	lstLink.append(slstLink)
	lstView.append(slstView)

# Report header
output.print_md("REPORT OF CAD INSTANCES")
print('\n' + str(len(set_name)) + ' Total CAD types found in model.')
print('Click on the Id to select an object in Revit.' + '\n\n')

# Report contents
for t,ids,links,views in zip(set_name,lstId, lstLink, lstView):
	print('\n' + t + ':')
	for i,l,v in zip(ids,links,views):
		if v == "":
			print(l + 'id {}'.format(output.linkify(i)) + " (not view specific).")
		else:
			print(l + 'id {}'.format(output.linkify(i)) + " specific to view " + 'id {}'.format(output.linkify(v)))
	print('\n')