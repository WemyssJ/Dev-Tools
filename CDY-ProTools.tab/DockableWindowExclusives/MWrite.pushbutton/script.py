# -*- coding: utf-8 -*-
# CDY Memory Selection - MWrite
# Saves pre-captured element IDs to a named slot.
#
# When called from the dockable panel the MemoryHandler (inside the ExternalEvent)
# has already:
#   1. Captured element IDs from the live selection
#   2. Resolved the store path from doc.Title (where doc is guaranteed valid)
#   3. Written both to _params.json
#
# This script simply reads that file and writes the JSON store.
# It never calls revit.doc or doc.Title itself -- those are None in _exec_script.

import os
import os.path as op
import json

from pyrevit import script

logger  = script.get_logger()
_MEM_DIR        = op.join(os.getenv("APPDATA"), "pyRevit", "CDY-Mem")
_MEM_PARAM_FILE = op.join(_MEM_DIR, "_params.json")

# -- Read params --------------------------------------------------------------
try:
    with open(_MEM_PARAM_FILE, "r") as f:
        params = json.load(f)
    os.remove(_MEM_PARAM_FILE)  # consume immediately
except Exception as e:
    logger.error("MWrite: could not read params file: %s" % e)
    script.exit()

slot        = (params.get("slot") or "").strip()
store_path  = params.get("store_path")
element_ids = params.get("element_ids")

if not slot:
    logger.error("MWrite: no slot name in params.")
    script.exit()

if not store_path:
    logger.error("MWrite: no store_path in params.")
    script.exit()

if not element_ids:
    logger.error("MWrite: no element_ids in params.")
    script.exit()

# -- Load existing store, update slot, save -----------------------------------
store = {}
try:
    if op.exists(store_path):
        with open(store_path, "r") as f:
            store = json.load(f)
except Exception as e:
    logger.debug("MWrite: could not load existing store (will create): %s" % e)

store[slot] = element_ids

try:
    if not op.exists(_MEM_DIR):
        os.makedirs(_MEM_DIR)
    with open(store_path, "w") as f:
        json.dump(store, f, indent=2)
except Exception as e:
    logger.error("MWrite: could not save store: %s" % e)
    script.exit()

print("MWrite: saved {} element(s) to slot '{}'".format(len(element_ids), slot))
