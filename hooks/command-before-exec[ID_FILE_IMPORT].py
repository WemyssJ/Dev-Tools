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
    TaskDialog.Show('Big Brother is Watching!',
                    'Import CAD is not Allowed! Use Link CAD Instead.')

    #🔒 Ask user for Password
    from pyrevit.forms import ask_for_string
    password   = 'LearnRevitAPI.com'
    user_input = ask_for_string(prompt='Only users with a password can Import CAD.',
                                title='Import CAD Blocked')
    # ❌ Stop Execution
    if user_input != password:
        args.Cancel = True
else:
    TaskDialog.Show('Family CAD Import',
                    'Import CAD is Allowed in families!')