# -*- coding: utf-8 -*-
# CDY Memory Selection - MAppend
# Merges pre-captured element IDs into an existing slot (union, no duplicates).
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
    logger.error("MAppend: could not read params file: %s" % e)
    script.exit()

slot        = (params.get("slot") or "").strip()
store_path  = params.get("store_path")
element_ids = params.get("element_ids")

if not slot or not store_path:
    logger.error("MAppend: missing slot or store_path in params.")
    script.exit()

if not element_ids:
    logger.error("MAppend: no element_ids in params.")
    script.exit()

# -- Load store, merge, save --------------------------------------------------
store = {}
try:
    if op.exists(store_path):
        with open(store_path, "r") as f:
            store = json.load(f)
except Exception as e:
    logger.debug("MAppend: could not load existing store (will create): %s" % e)

existing = set(store.get(slot, []))
new_ids  = set(element_ids)
merged   = list(existing | new_ids)
added    = len(merged) - len(existing)
store[slot] = merged

try:
    if not op.exists(_MEM_DIR):
        os.makedirs(_MEM_DIR)
    with open(store_path, "w") as f:
        json.dump(store, f, indent=2)
except Exception as e:
    logger.error("MAppend: could not save store: %s" % e)
    script.exit()

print("MAppend: added {} new id(s) to slot '{}' ({} total).".format(
    added, slot, len(merged)))
