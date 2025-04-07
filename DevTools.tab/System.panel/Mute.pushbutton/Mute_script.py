# import libraries
from pyrevit import forms
from guRoo_msgUtils import *

# check if tools are muted
if msgUtils_muted():
	muteOn = forms.alert("Re-enable notifications?", title= "DevTools is muted", warn_icon = False)
	if muteOn:
		msgUtils_muteOff()
else:
	muteOff = forms.alert("Disable notifications?", title= "DevTools is not muted", warn_icon = False)
	if muteOff:
		msgUtils_muteOn()