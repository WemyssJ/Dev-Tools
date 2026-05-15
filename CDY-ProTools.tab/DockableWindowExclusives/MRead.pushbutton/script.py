# -*- coding: utf-8 -*-
# CDY Memory Selection - MRead
# Restore a saved selection slot to the active selection.
#
# When launched from the dockable panel the slot name comes from the params file.
# When run as a standalone toolbar button, falls back to a slot picker dialog.

import os
import os.path as op
import json
import re

from pyrevit import script, revit, forms
from pyrevit.compat import get_elementid_from_value_func
from Autodesk.Revit.DB import ElementId
from System.Collections.Generic import List as DotNetList

logger = script.get_logger()

_MEM_DIR        = op.join(os.getenv("APPDATA"), "pyRevit", "CDY-Mem")
_MEM_PARAM_FILE = op.join(_MEM_DIR, "_params.json")


def _doc_key(doc):
    return re.sub(r'[^\w\-]', '_', doc.Title or "unknown")

def _store_path(doc):
    return op.join(_MEM_DIR, _doc_key(doc) + ".json")

def _load(doc):
    try:
        path = _store_path(doc)
        if op.exists(path):
            with open(path, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.debug("MRead load error: %s" % e)
    return {}


# -- Read params file ----------------------------------------------------------
slot = None

try:
    with open(_MEM_PARAM_FILE, "r") as f:
        params = json.load(f)
    os.remove(_MEM_PARAM_FILE)  # consume immediately
    if params.get("op") == "read":
        slot = (params.get("slot") or "").strip()
except Exception:
    pass

doc   = revit.doc
store = _load(doc)

if not store:
    forms.alert("No saved selection slots found for this document.", exitscript=True)

# -- Toolbar fallback: show picker ---------------------------------------------
if not slot:
    slot = forms.SelectFromList.show(
        sorted(store.keys()),
        title="MRead - Choose Slot",
        multiselect=False)
    if not slot:
        script.exit()

if slot not in store:
    forms.alert("Slot '{}' not found.".format(slot), exitscript=True)

# -- Restore selection ---------------------------------------------------------
get_id  = get_elementid_from_value_func()
uidoc   = revit.uidoc
ids     = []
missing = 0

for v in store[slot]:
    try:
        eid = get_id(v)
        if doc.GetElement(eid) is not None:
            ids.append(eid)
        else:
            missing += 1
    except Exception:
        missing += 1

uidoc.Selection.SetElementIds(DotNetList[ElementId](ids))

msg = "MRead: selected {} element(s) from slot '{}'.".format(len(ids), slot)
if missing:
    msg += " ({} id(s) no longer in model.)".format(missing)
print(msg)
