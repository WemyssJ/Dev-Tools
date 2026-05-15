# -*- coding: utf-8 -*-
# CDY Memory Selection - MDelete
# Delete a named selection slot from the store for the current document.
#
# When launched from the dockable panel the slot name comes from the params file.
# When run as a standalone toolbar button, falls back to a slot picker dialog.

import os
import os.path as op
import json
import re

from pyrevit import script, revit, forms

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
        logger.debug("MDelete load error: %s" % e)
    return {}

def _save(doc, store):
    if not op.exists(_MEM_DIR):
        os.makedirs(_MEM_DIR)
    with open(_store_path(doc), "w") as f:
        json.dump(store, f, indent=2)


# -- Read params file ----------------------------------------------------------
slot = None

try:
    with open(_MEM_PARAM_FILE, "r") as f:
        params = json.load(f)
    os.remove(_MEM_PARAM_FILE)  # consume immediately
    if params.get("op") == "delete":
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
        title="MDelete - Choose Slot to Delete",
        multiselect=False)
    if not slot:
        script.exit()

if slot not in store:
    forms.alert("Slot '{}' not found.".format(slot), exitscript=True)

# -- Confirm when run from toolbar (panel already confirmed via UI) -------------
# Only show confirm dialog when run interactively (no params file was present)
count = len(store[slot])
confirmed = forms.alert(
    "Delete slot '{}' ({} elements)?".format(slot, count),
    title="MDelete", yes=True, no=True)
if not confirmed:
    script.exit()

# -- Delete and save -----------------------------------------------------------
del store[slot]
_save(doc, store)
print("MDelete: removed slot '{}'.".format(slot))
