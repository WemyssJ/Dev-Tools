
from pyrevit import forms
import core

# Toast notify for new updates
try:
    if core.update_needed() == True:
        forms.toaster.send_toast("New update for DevTools extension available: {}".format(core.get_git_version()))
    else:
        pass
except Exception:
    pass
