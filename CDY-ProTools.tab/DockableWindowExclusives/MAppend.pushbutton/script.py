# -*- coding: utf-8 -*-
# CDY Memory Selection - MAppend
# Add the current selection to an existing named slot (union, no duplicates).
#
# When launched from the dockable panel the startup.py MemoryHandler captures
# element IDs inside the ExternalEvent (while selection is guaranteed intact)
# and writes them to the params file before this script runs.
#
# When run as a standalone pyRevit toolbar button, no params file is present
# so the script falls back to reading the live selection and showing a picker.

import os
import os.path as op
import json
import re

from pyrevit import script, revit, forms
from pyrevit.compat import get_elementid_value_func

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
        logger.debug("MAppend load error: %s" % e)
    return {}

def _save(doc, store):
    if not op.exists(_MEM_DIR):
        os.makedirs(_MEM_DIR)
    with open(_store_path(doc), "w") as f:
        json.dump(store, f, indent=2)


# -- Read params file (written by MemoryHandler before calling this script) ----
slot        = None
element_ids = None  # pre-captured by the handler; None when run from toolbar

try:
    with open(_MEM_PARAM_FILE, "r") as f:
        params = json.load(f)
    os.remove(_MEM_PARAM_FILE)  # consume immediately - never reuse stale params
    if params.get("op") == "append":
        slot        = (params.get("slot") or "").strip()
        element_ids = params.get("element_ids")  # list of id strings, or None
except Exception:
    pass  # no params file - toolbar fallback below

doc   = revit.doc
store = _load(doc)

# -- Get element IDs - use pre-captured list if available ----------------------
if element_ids is None:
    # Toolbar path: read live selection now
    get_val     = get_elementid_value_func()
    selection   = revit.get_selection()
    element_ids = [str(get_val(e)) for e in selection.element_ids]
    if not element_ids:
        forms.alert("Nothing is selected. Select elements to append first.", exitscript=True)

# -- Resolve slot name (toolbar fallback) --------------------------------------
if not slot:
    if not store:
        forms.alert("No saved slots found. Use MWrite to create a slot first.", exitscript=True)
    slot = forms.SelectFromList.show(
        sorted(store.keys()),
        title="MAppend - Choose Slot to Append To",
        multiselect=False)
    if not slot:
        script.exit()

# -- Merge and save ------------------------------------------------------------
existing = set(store.get(slot, []))
new_ids  = set(element_ids)
merged   = list(existing | new_ids)
added    = len(merged) - len(existing)
store[slot] = merged
_save(doc, store)

print("MAppend: added {} new id(s) to slot '{}' ({} total).".format(
    added, slot, len(merged)))
