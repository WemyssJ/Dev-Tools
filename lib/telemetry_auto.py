# -*- coding: utf-8 -*-
"""
telemetry_auto.py
Logs usage counts per tool per day along with Revit version.
Silently fails if telemetry file/folder is inaccessible.
"""

import os
import json
from datetime import datetime

# pyRevit import to get Revit version
try:
    from pyrevit import HOST_APP
    revit_version = HOST_APP.version 
except:
    revit_version = "Unknown"

# Network path for telemetry JSON
TELEMETRY_JSON = r"P:\Joe Wemyss\CDY-ProTools Telemetry\telemetry.json"

def log_tool_usage(tool_name):
    """
    Logs usage per tool per day with Revit version.
    Key format: "Tool Name | YYYY-MM-DD | RevitVersion"
    Silently fails if the network path is unavailable.
    """

    # Current date
    today = datetime.now().strftime("%Y-%m-%d")

    # Use classic formatting for IronPython 2.7
    key = "%s | %s | R%s" % (tool_name, today, revit_version)

    folder = os.path.dirname(TELEMETRY_JSON)
    if not os.path.exists(folder):
        # Folder doesn't exist; silently skip logging
        return

    # Load existing data
    data = {}
    try:
        if os.path.exists(TELEMETRY_JSON):
            with open(TELEMETRY_JSON, "r") as f:
                data = json.load(f)
    except:
        pass  # Fail silently if reading fails

    # Increment usage count
    data[key] = data.get(key, 0) + 1

    # Write back
    try:
        with open(TELEMETRY_JSON, "w") as f:
            json.dump(data, f, indent=2, sort_keys=True)
    except:
        pass  # Fail silently if writing fails
