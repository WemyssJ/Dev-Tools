# -*- coding: utf-8 -*-
"""Strip model except selected views and sheets and purge it .

NOTE:
"""
__author__ = "Joe Wemyss"
__title__ = "Strip\n Model"

# Import 
from pyrevit import revit, DB
from pyrevit import script
from pyrevit import forms

import clr
import System
clr.AddReference("System")
from System.Collections.Generic import List

# Store current document into variable
doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument

def checkCentral():
    """
    Return:
     0 - allow script to run
     1 - blocked because model is workshared and not detached
     2 - blocked because model is non-workshared but NOT saved on C:
    """
    try:
        is_workshared = doc.IsWorkshared
    except:
        is_workshared = False
    
    is_detached = getattr(doc, "IsDetached", False)
    file_path = doc.PathName
    
    if is_workshared and not is_detached:
        # Workshared but NOT detached -> block and message 1
        return 1
    
    if not is_workshared and not file_path.startswith("C:"):
        # Non workshared but NOT on C: drive -> block and message 2
        return 2
    
    # Otherwise allow
    return 0

# Function to round to ten
def roundNumber(number, multiple):
    remainder = number % multiple
    if remainder != 0:
        addNumber = multiple - remainder
        updatedNumber = addNumber + number 
        return updatedNumber
    else:
        return number

# Function to purge file
def purge():
    purgeGuid = 'e8c63650-70b7-435a-9010-ec97660c1bda'
    purgableElementIds = []
    performanceAdviser = DB.PerformanceAdviser.GetPerformanceAdviser()
    guid = System.Guid(purgeGuid)
    ruleId = None
    allRuleIds = performanceAdviser.GetAllRuleIds()
    for rule in allRuleIds:
        if str(rule.Guid) == purgeGuid:
            ruleId = rule
    ruleIds = List[DB.PerformanceAdviserRuleId]([ruleId])
    for i in range(3):
        failureMessages = performanceAdviser.ExecuteRules(doc, ruleIds)
        if failureMessages.Count > 0:
            purgableElementIds = failureMessages[0].GetFailingElements()
    try:
        doc.Delete(purgableElementIds)
    except:
        for e in purgableElementIds:
            try:
                doc.Delete(e)
            except:
                pass

def refresh_all_title_blocks():
    sheetsCollector = DB.FilteredElementCollector(doc).OfClass(DB.ViewSheet).ToElements()
    if not sheetsCollector:
        script.get_logger().warning("No sheets found in document.")
        return

    for sheet in sheetsCollector:
        # Find title blocks on this sheet
        title_blocks = DB.FilteredElementCollector(doc, sheet.Id).OfCategory(DB.BuiltInCategory.OST_TitleBlocks).WhereElementIsNotElementType().ToElements()

        for tb in title_blocks:
            loc = tb.Location
            if isinstance(loc, DB.LocationPoint):
                point = loc.Point
            elif isinstance(loc, DB.LocationCurve):
                point = loc.Curve.GetEndPoint(0)
            else:
                point = DB.XYZ(0, 0, 0)

            symbol = tb.Symbol

            # Store all writable instance parameter values from the old title block
            param_values = {}
            for param in tb.Parameters:
                if param.IsReadOnly:
                    continue
                try:
                    if param.StorageType == DB.StorageType.Integer:
                        param_values[param.Definition.Name] = param.AsInteger()
                    elif param.StorageType == DB.StorageType.Double:
                        param_values[param.Definition.Name] = param.AsDouble()
                    elif param.StorageType == DB.StorageType.String:
                        param_values[param.Definition.Name] = param.AsString()
                    elif param.StorageType == DB.StorageType.ElementId:
                        param_values[param.Definition.Name] = param.AsElementId()
                except:
                    # Ignore parameters that fail to read
                    pass

            # Delete old title block instance
            try:
                doc.Delete(tb.Id)
            except:
                # ignore failures deleting title block
                pass

            # Place a new instance on the sheet
            try:
                new_tb = doc.Create.NewFamilyInstance(point, symbol, sheet)

                # Restore all stored parameter values to new instance
                for pname, pvalue in param_values.items():
                    param = new_tb.LookupParameter(pname)
                    if param and not param.IsReadOnly:
                        try:
                            if param.StorageType == DB.StorageType.Integer and isinstance(pvalue, int):
                                param.Set(pvalue)
                            elif param.StorageType == DB.StorageType.Double and isinstance(pvalue, float):
                                param.Set(pvalue)
                            elif param.StorageType == DB.StorageType.String and isinstance(pvalue, str):
                                param.Set(pvalue)
                            elif param.StorageType == DB.StorageType.ElementId and isinstance(pvalue, DB.ElementId):
                                param.Set(pvalue)
                        except:
                            # Ignore if unable to set
                            pass
            except:
                pass


count = 1
finalCount = 0

# --- PROMPT USER TO SELECT VIEWS TO KEEP BEFORE ANY TRANSACTIONS ---
viewsRetained = forms.select_views(button_name='Views to Keep', multiple=True)
retainedIds = set(x.Id for x in viewsRetained)

check = checkCentral()
if check == 1:
    forms.alert("Please detach model from central and try again.", ok=True, exitscript=True)
elif check == 2:
    forms.alert("This is a non work shared model, please save to your C: drive and try again.", ok=True, exitscript=True)

# --- Set active view first (no transaction) ---
sheet_to_keep = None
for v in viewsRetained:
    if isinstance(v, DB.ViewSheet):
        sheet_to_keep = v
        break
if not sheet_to_keep and viewsRetained:
    sheet_to_keep = viewsRetained[0]

if sheet_to_keep:
    uidoc.ActiveView = sheet_to_keep  # <-- NO TRANSACTION allowed here!

# --- Now open transaction to close other views ---
with DB.Transaction(doc, "Close Other Views") as tx:
    tx.Start()

    # Close all other open UI views except the one kept
    open_ui_views = list(uidoc.GetOpenUIViews())
    for ui_view in open_ui_views:
        if ui_view.ViewId != sheet_to_keep.Id:
            try:
                ui_view.Close()
            except:
                pass

    tx.Commit()


# --- NOW START THE TRANSACTION GROUP FOR STRIPPING ---
with forms.ProgressBar(step=10) as pb:
    tg = DB.TransactionGroup(doc, "Delete elements in document")
    tg.Start()

    # Collect all views and sheets
    viewsCollector = DB.FilteredElementCollector(doc).OfClass(DB.View).ToElements()
    sheetsCollector = DB.FilteredElementCollector(doc).OfClass(DB.ViewSheet).ToElements()
    linksCollector = DB.FilteredElementCollector(doc).OfClass(DB.ImportInstance)
    revitLinkCollector = DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkType)
    imagesCollector = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_RasterImages)

    viewsIdDelete = [x.Id for x in viewsCollector if x.Id not in retainedIds]

    importedInstancesId = [x.Id for x in linksCollector]
    revitLinksId = [x.Id for x in revitLinkCollector]
    imagesId = [x.Id for x in imagesCollector]

    delAnnotations = forms.alert("Delete annotation elements", title="Delete annotations?", yes=True, no=True)

    annoElements = []

    if delAnnotations:
        categories = doc.Settings.Categories
        catDel = ("Dimensions", "Railing Tags", "Furniture Tags", "Spot Slopes", "Spot Elevations", "Floor Tags", "Door Tags", "Window Tags", "Specialty Equipment Tags", "Material Tags", "Property Line Segment Tags", "Wall Tags", "Parking Tags", "Color Fill Legends", "Spot Elevation Symbols", "Structural Column Tags", "Room Tags", "Generic Model Tags", "Text Notes", "Callout Heads", "Structural Foundation Tags", "Lighting Device Tags", "Curtain Panel Tags", "Ceiling Tags",  "Plumbing Fixture Tags", "Roof Tags", "Casework Tags", "Revision Clouds", "Electrical Fixture Tags")
        for cat in categories:
            if cat.CategoryType == DB.CategoryType.Annotation:
                collector = DB.FilteredElementCollector(doc).OfCategoryId(cat.Id)
                elemIds = [x.Id for x in collector if x.Category.Name in catDel]
                annoElements = annoElements + elemIds
    
    delElements = annoElements + viewsIdDelete + importedInstancesId + revitLinksId + imagesId
    finalCount = len(delElements)

    t = DB.Transaction(doc, "Delete elements")
    t.Start()

    for e in delElements:
        try:
            doc.Delete(e)
        except:
            pass
        pb.update_progress(count, roundNumber(finalCount, 10))
        count += 1

    purge()

    t.Commit()
    tg.Commit()

# Run the refresh of title blocks in its own transaction after committing deletions
with DB.Transaction(doc, "Refresh Title Blocks on All Sheets") as tx:
    tx.Start()
    refresh_all_title_blocks()
    tx.Commit()


# --- OPEN PURGE UNUSED DIALOG ---
from Autodesk.Revit.UI import RevitCommandId

uiapp = __revit__.ActiveUIDocument.Application
cmdId = RevitCommandId.LookupCommandId("ID_PURGE_UNUSED")
if cmdId:
    uiapp.PostCommand(cmdId)
else:
    print("Could not find command id for Purge Unused")
