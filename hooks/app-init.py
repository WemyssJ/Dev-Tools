# import pyrevit libraries
import clr
from pyrevit import forms,script
from guRoo_msgUtils import *

# check if notifications are disabled
if msgUtils_muted():
	script.exit()

# Get icon file (doesn't work)
# curPath = script.get_script_path()
# remPath = curPath.split('CDY-ProTools.tab')[0]
# icoFile = remPath + r'bin\Graphics\ico256_CDY.ico'

# Display the message to the user
forms.toast("Toolbar has been loaded!","CDY-ProTools for Revit",appid="BIMTools",actions={"Respository":"https://github.com/WemyssJ/"})
