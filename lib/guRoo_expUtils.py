# Prepare for utilities
from pyrevit import revit,DB,forms,script
from pyrevit.framework import clr
from System.Collections.Generic import List
import os, datetime

doc = revit.doc
uidoc = revit.uidoc

# get print directory
def expUtils_getDir():
	dp = os.path.expanduser("\\guRoo Exports")
	return dp

# make subfolder extension
def expUtils_getFolder(task = "_PDF"):
	dateStamp = datetime.datetime.today().strftime("%y%m%d")
	timeStamp = datetime.datetime.today().strftime("%H%M%S")
	return dateStamp + "_" + timeStamp + task

# make directory if it doesn't exist
def expUtils_ensureDir(dp):
	if not os.path.exists(dp):
		os.makedirs(dp)
	return dp

# open the directory
def expUtils_openDir(dp):
	try:
		os.startfile(dp)
	except:
		pass
	return dp

# function for checking version
def expUtils_canPrint():
	app = __revit__.Application
	rvt_year = int(app.VersionNumber)
	# Check that version is 2022 or higher
	if rvt_year < 2022:
		forms.alert("Only available in Revit 2022 or later.", title= "Script cancelled")
		script.exit()
	else:
		return True

# make sheet name for print
def expUtils_nameSheet(s, namingProtocol):
	# Get revision number
	#region 2021 Naming Standard
	##PROJECT NUMBER##
	try:
		ProjNum = doc.get_Parameter(BuiltInParameter.PROJECT_NUMBER).AsString()
		if ProjNum is None:
			ProjNum = "ParameterNotFound"
	except:
		ProjNum = "ParameterNotFound"
	##ORIGINATOR##
	try:
		Originator = s.LookupParameter("Originator").AsString()
		if Originator is None:
			Originator = "ParameterNotFound"
	except:
		Originator = "ParameterNotFound"
	##FUNCTIONAL BREAKDOWN##
	try:
		FunctionalBreakdown = s.LookupParameter("Functional Breakdown").AsString()
		if FunctionalBreakdown is None:
			FunctionalBreakdown = "ParameterNotFound"
	except:
		FunctionalBreakdown = "ParameterNotFound"
	##SPATIAL BREAKDOWN##
	try:
		SpatialBreakdown = s.LookupParameter("Spatial Breakdown").AsString()
		if SpatialBreakdown is None:
			SpatialBreakdown = "ParameterNotFound"
	except:
		SpatialBreakdown = "ParameterNotFound"
	##FORM##
	try:
		Form = s.LookupParameter("Form").AsString()
		if Form is None:
			Form = "ParameterNotFound"
	except:
		Form = "ParameterNotFound"
	##DISCIPLINE##
	try:
		Discipline = s.LookupParameter("Discipline").AsString()
		if Discipline is None:
			Discipline = "ParameterNotFound"
	except:
		Discipline = "ParameterNotFound"
	##DRAWING NUMBER##
	#N/A
	##CURRENT REVISION##
	try:
		curRev = s.GetCurrentRevision()
		curNum = s.GetRevisionNumberOnSheet(curRev)
	except:
		curNum = "-"
	##DRAWING NAME##
	#N/A
	##DRAWING TITLE 2##
	try:
		DrawingTitle2 = s.LookupParameter("Drawing Title 2").AsString()
		DrawingTitle2 = " " + DrawingTitle2
	except:
		DrawingTitle2 = ""
	##DRAWING TITLE 2##
	try:
		DrawingTitle3 = s.LookupParameter("Drawing Title 3").AsString()
		DrawingTitle3 = " " + DrawingTitle3
	except:
		DrawingTitle3 = ""
	#endregion
	#region 2018 Naming Standard
	##VOLUME OR SYSTEM##
	try:
		VolumeOrSystem = s.LookupParameter("Volume or System").AsString()
		if VolumeOrSystem is None:
			VolumeOrSystem = "ParameterNotFound"
	except:
		VolumeOrSystem = "ParameterNotFound"
	##LEVELS AND LOCATION##
	try:
		LevelsAndLocation = s.LookupParameter("Levels and Location").AsString()
		if LevelsAndLocation is None:
			LevelsAndLocation = "ParameterNotFound"
	except:
		LevelsAndLocation = "ParameterNotFound"
	##Type##
	try:
		Type = s.LookupParameter("Type").AsString()
		if Type is None:
			Type = "ParameterNotFound"
	except:
		Type = "ParameterNotFound"
	##ROLE##
	try:
		Role = s.LookupParameter("Role").AsString()
		if Role is None:
			Role = "ParameterNotFound"
	except:
		Role = "ParameterNotFound"
	#endregion
	#region Aldi Template
	##PM.Sheet.Title.Creator.Originator##
	try:
		AldiOriginator = s.LookupParameter("PM.Sheet.Title.Creator.Originator").AsString()
		if AldiOriginator is None:
			AldiOriginator = "ParameterNotFound"
	except:
		AldiOriginator = "ParameterNotFound"
	##PM.Sheet.Title.Creator.Originator##
	try:
		AldiZone = s.LookupParameter("PM.Sheet.Title.View.Zone").AsString()
		if AldiZone is None:
			AldiZone = "ParameterNotFound"
	except:
		AldiZone = "ParameterNotFound"
	##PM.Sheet.Title.View.Level##
	try:
		AldiLevel = s.LookupParameter("PM.Sheet.Title.View.Level").AsString()
		if AldiLevel is None:
			AldiLevel = "ParameterNotFound"
	except:
		AldiLevel = "ParameterNotFound"
	##PM.Sheet.Title.View.Type##
	try:
		AldiType = s.LookupParameter("PM.Sheet.Title.View.Type").AsString()
		if AldiType is None:
			AldiType = "ParameterNotFound"
	except:
		AldiType = "ParameterNotFound"
	##PM.Sheet.Title.Creator.Role##
	try:
		AldiRole = s.LookupParameter("PM.Sheet.Title.Creator.Role").AsString()
		if AldiRole is None:
			AldiRole = "ParameterNotFound"
	except:
		AldiRole = "ParameterNotFound"
	##Classification##
	try:
		Classification = s.LookupParameter("Classification").AsString()
		if Classification is None:
			Classification = "ParameterNotFound"
	except:
		Classification = "ParameterNotFound"
	##PM.Sheet.Title.Sheet.Suitability##
	try:
		AldiSuitability = s.LookupParameter("PM.Sheet.Title.Sheet.Suitability").AsString()
		if AldiSuitability is None:
			AldiSuitability = "ParameterNotFound"
	except:
		AldiSuitability = "ParameterNotFound"

	#endregion

	# get string utility
	from guRoo_strUtils import *
	# make sheet name

	if namingProtocol == ('Craddys: BS EN ISO 19650-2-2018 (+A1 2021)'):
		preName =  ProjNum + "-" + Originator + "-" + FunctionalBreakdown + "-" + SpatialBreakdown + "-" + Form + "-" + Discipline + "-" + s.SheetNumber + "-" + curNum + " " + s.Name
	elif namingProtocol == ('Craddys: BS EN ISO 19650-2-2018'):
		preName =  ProjNum + "-" + Originator + "-" + VolumeOrSystem + "-" + LevelsAndLocation + "-" + Type + "-" + Role + "-" + s.SheetNumber + "-" + curNum + " " + s.Name
	elif namingProtocol == ('Aldi BEP & Parameters'):
		preName =  ProjNum + "-" + AldiOriginator + "-" + AldiZone + "-" + AldiLevel + "-" + AldiType + "-" + AldiRole + "-" + Classification + "-" + s.SheetNumber + "-" + AldiSuitability + "-" + curNum + " " + s.Name + DrawingTitle2 + DrawingTitle3
	elif namingProtocol == ('Morgan Sindall: BS EN ISO 19650-2-2018 (+A1 2021)'):
		preName =  ProjNum + "-" + Originator + "-" + FunctionalBreakdown + "-" + SpatialBreakdown + "-" + Form + "-" + Discipline + "-" + s.SheetNumber + "-" + curNum + " " + s.Name + DrawingTitle2 + DrawingTitle3
	else:
		##default to latset ISO Standards
		preName =  ProjNum + "-" + Originator + "-" + FunctionalBreakdown + "-" + SpatialBreakdown + "-" + Form + "-" + Discipline + "-" + s.SheetNumber + "_" + s.Name + DrawingTitle2 + DrawingTitle3 + "_" + curNum
	shtName = strUtils_legalize(preName)
	return shtName

# make view name for print
def expUtils_nameView(v):
	# get string utility
	from guRoo_strUtils import *
	# make sheet name
	preName = str(v.ViewType) + '_' + v.Name
	viewName = strUtils_legalize(preName)
	return viewName

# open a view/sheet
def expUtils_viewFocus(v,myDoc,myUiDoc):
	myUiDoc.RequestViewChange(v)
	curView  = myDoc.ActiveView
	allViews = myUiDoc.GetOpenUIViews()
	for v in allViews:
		if v.ViewId != curView.Id:
			try:
				v.Close()
			except:
				pass

# make pdf options
def expUtils_pdfOpts(hcb=False,hsb=True,hrp=True,hvt=True,mcl=True):
	opts = DB.PDFExportOptions()
	# Settings default
	opts.HideCropBoundaries = hcb
	opts.HideScopeBoxes = hsb
	opts.HideReferencePlane = hrp
	opts.HideUnreferencedViewTags = hvt
	opts.MaskCoincidentLines = mcl
	# Paper format
	opts.PaperFormat = DB.ExportPaperFormat.Default
	return opts

# make dwg options
def expUtils_dwgOpts(sc=False,mv=True):
	opts = DB.DWGExportOptions()
	# Settings default
	opts.SharedCoords = sc
	opts.MergedViews = mv
	return opts

# export a single sheet to pdf
def expUtils_exportSheetPdf(d,s,opt,myDoc,myUidoc,namingProtocol):
	docName = expUtils_nameSheet(s,namingProtocol)
	expUtils_viewFocus(s,myDoc,myUidoc)
	opt.FileName = docName
	# Prepare an Id list
	exportSheet = List[DB.ElementId]()
	exportSheet.Add(s.Id)
	# Export the sheet to PDF
	myDoc.Export(d, exportSheet, opt)
	return 1

# export a single sheet to dwg
def expUtils_exportSheetDwg(d,s,opt,myDoc,myUidoc,namingProtocol):
	docName = expUtils_nameSheet(s,namingProtocol)
	expUtils_viewFocus(s,myDoc,myUidoc)
	# Prepare an Id list
	exportSheet = List[DB.ElementId]()
	exportSheet.Add(s.Id)
	# Export the sheet to DWG
	myDoc.Export(d, docName, exportSheet, opt)
	return 1

# export a single view to dwg
def expUtils_exportViewDwg(d,v,opt,myDoc,myUidoc):
	docName = expUtils_nameView(v)
	expUtils_viewFocus(v,myDoc,myUidoc)
	# Prepare an Id list
	exportView = List[DB.ElementId]()
	exportView.Add(v.Id)
	# Export the sheet to DWG
	myDoc.Export(d, docName, exportView, opt)
	return 1

# export a single sheet to pdf and dwg
def expUtils_exportSheetPdfDwg(d,s,optPdf,optDwg,myDoc,myUidoc,namingProtocol):
	docName = expUtils_nameSheet(s, namingProtocol)
	expUtils_viewFocus(s,myDoc,myUidoc)
	optPdf.FileName = docName
	# Prepare an Id list
	exportSheet = List[DB.ElementId]()
	exportSheet.Add(s.Id)
	# Export the sheet to PDF
	myDoc.Export(d, exportSheet, optPdf)
	# Export the sheet to DWG
	myDoc.Export(d, docName, exportSheet, optDwg)
	return 1
