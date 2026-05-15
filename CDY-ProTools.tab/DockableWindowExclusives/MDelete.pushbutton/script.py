# -*- coding: utf-8 -*-
# CDY Memory Selection - MDelete
# Removes a named slot from the store.
# store_path is pre-resolved by MemoryHandler -- this script never uses doc.Title.

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
    os.remove(_MEM_PARAM_FILE)
except Exception as e:
    logger.error("MDelete: could not read params file: %s" % e)
    script.exit()

slot       = (params.get("slot") or "").strip()
store_path = params.get("store_path")

if not slot or not store_path:
    logger.error("MDelete: missing slot or store_path in params.")
    script.exit()

# -- Load store, delete slot, save --------------------------------------------
store = {}
try:
    if op.exists(store_path):
        with open(store_path, "r") as f:
            store = json.load(f)
except Exception as e:
    logger.error("MDelete: could not load store: %s" % e)
    script.exit()

if slot not in store:
    logger.error("MDelete: slot '{}' not found.".format(slot))
    script.exit()

del store[slot]

try:
    with open(store_path, "w") as f:
        json.dump(store, f, indent=2)
except Exception as e:
    logger.error("MDelete: could not save store: %s" % e)
    script.exit()

print("MDelete: removed slot '{}'.".format(slot))
