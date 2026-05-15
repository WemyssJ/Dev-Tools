# -*- coding: utf-8 -*-
# CDY Memory Selection - MRead
# Restores a saved selection slot to the active selection.
# store_path is pre-resolved by MemoryHandler -- this script never uses doc.Title.

import os
import os.path as op
import json

from pyrevit import script
from pyrevit.compat import get_elementid_from_value_func
from Autodesk.Revit.DB import ElementId
from System.Collections.Generic import List as DotNetList

logger  = script.get_logger()
_MEM_DIR        = op.join(os.getenv("APPDATA"), "pyRevit", "CDY-Mem")
_MEM_PARAM_FILE = op.join(_MEM_DIR, "_params.json")

# -- Read params --------------------------------------------------------------
try:
    with open(_MEM_PARAM_FILE, "r") as f:
        params = json.load(f)
    os.remove(_MEM_PARAM_FILE)
except Exception as e:
    logger.error("MRead: could not read params file: %s" % e)
    script.exit()

slot       = (params.get("slot") or "").strip()
store_path = params.get("store_path")

if not slot or not store_path:
    logger.error("MRead: missing slot or store_path in params.")
    script.exit()

# -- Load store ---------------------------------------------------------------
store = {}
try:
    if op.exists(store_path):
        with open(store_path, "r") as f:
            store = json.load(f)
except Exception as e:
    logger.error("MRead: could not load store: %s" % e)
    script.exit()

if slot not in store:
    logger.error("MRead: slot '{}' not found.".format(slot))
    script.exit()

# -- Restore selection --------------------------------------------------------
get_id  = get_elementid_from_value_func()
uidoc   = __uidoc__  # injected by _exec_script
ids     = []
missing = 0
doc     = uidoc.Document if uidoc else None

for v in store[slot]:
    try:
        eid = get_id(v)
        if doc and doc.GetElement(eid) is not None:
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
