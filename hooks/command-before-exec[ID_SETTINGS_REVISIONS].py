# -*- coding: utf-8 -*-
#⬇️ Imports
from pyrevit import revit, EXEC_PARAMS
from Autodesk.Revit.UI import TaskDialog


#📦 Variables
sender = __eventsender__ # UIApplication
args   = __eventargs__   # Autodesk.Revit.UI.Events.BeforeExecutedEventArgs
# args   = EXEC_PARAMS.event_args

doc = revit.doc
# doc = args.GetDocument()
# doc = args.Document

#🎯 MAIN
if not doc.IsFamilyDocument:
    #⚠️ Show Warning
    TaskDialog.Show('Reminder!',
                    'Run Pile E+N in BIMTools if piles have been moved.')