#This script uses python and Revit API to find the CAD file of the selected element
# Using pyrevit libraries
import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitServices')
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB import FilteredElementCollector, ImportInstance
# import pyrevit forms
from pyrevit import script
from pyrevit import forms
from pyrevit import revit
from pyrevit import DB
from pyrevit import HOST_APP

# get the current document
doc = __revit__.ActiveUIDocument.Document
output = script.get_output()

# collect all the CAD links in the document
cad_links = FilteredElementCollector(doc).OfClass(ImportInstance).ToElementIds()

modelbased = []
modelbasednames = []
detailbaesd = []
detailbasednames = []
nonlinked = []
nonlinkednames = []

for cad_link in cad_links:
    cadlinkelement = doc.GetElement(cad_link)
    if cadlinkelement.IsLinked == False:
        nonlinked.append(cadlinkelement)
        # get the catrgory name if the link is not linked
        nonlinkednames.append(cadlinkelement.get_Parameter(BuiltInParameter.IMPORT_SYMBOL_NAME).AsString())
        pass
    else:
        #determine if OwnerViewId is a valid view
        owner_view = doc.GetElement(cadlinkelement.OwnerViewId)
        if owner_view == None:
            modelbased.append(cadlinkelement)
            modelbasednames.append(cadlinkelement.get_Parameter(BuiltInParameter.IMPORT_SYMBOL_NAME).AsString())
        else:
            detailbaesd.append(cadlinkelement)
            detailbasednames.append(cadlinkelement.get_Parameter(BuiltInParameter.IMPORT_SYMBOL_NAME).AsString())

#define HTML style for header text
output.add_style('header {font-size: 20px; color: #000000;}')

#display the results
output.print_md('### Linked Model CADs')

for modelbased_link in modelbased:
    modelbased_linkId = modelbased_link.Id
    print(output.linkify(modelbased_linkId) + modelbased_link.get_Parameter(BuiltInParameter.IMPORT_SYMBOL_NAME).AsString())

# add some space and a separator
output.print_md('---')
output.print_md('### Linked Detail CADs')
for detailbased_link in detailbaesd:
    detailbased_linkId = detailbased_link.Id
    print(output.linkify(detailbased_linkId) + detailbased_link.get_Parameter(BuiltInParameter.IMPORT_SYMBOL_NAME).AsString())
# add some space and a separator
output.print_md('---')

output.print_md('### Non-Linked CADs')
for nonlinked_link in nonlinked:
    nonlinked_linkId = nonlinked_link.Id
    print(output.linkify(nonlinked_linkId) + nonlinked_link.get_Parameter(BuiltInParameter.IMPORT_SYMBOL_NAME).AsString())
