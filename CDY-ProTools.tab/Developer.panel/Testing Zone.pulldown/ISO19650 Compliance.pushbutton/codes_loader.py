# -*- coding: utf-8 -*-
"""
codes_loader.py
---------------
Place this file in the same .pushbutton folder as script.py.

Loads approved ISO 19650 codes from `codes_config.json` located in the
same folder as the active Revit model (.rvt).

If no codes_config.json is found, the user is offered a choice:
  - Continue using Craddys internal naming defaults (no BEP)
  - Cancel and create the config first

If the file exists but is malformed or incomplete, the tool exits with
a clear diagnostic — no silent fallback.

Usage in script.py
------------------
    from codes_loader import load_codes
    CODES = load_codes(doc)

    SPATIAL_KEYWORDS     = CODES["spatial_codes"]
    FUNCTIONAL_CODES     = CODES["functional_codes"]
    FORM_CODES           = CODES["form_codes"]
    ROLE_CODES           = CODES["role_codes"]
    SHEET_NUM_PATTERN    = CODES["sheet_number_pattern"]
    ORIGINATORS          = CODES["originators"]
    USE_CLASSIFICATION   = CODES["use_classification"]
    CLASSIFICATION_CODES = CODES["classification_codes"]
    NAMING_FORMATS       = CODES["naming_formats"]
    USING_CDY_DEFAULTS   = CODES["using_cdy_defaults"]
"""

import os
import json

from pyrevit import forms, DB

# Increment this whenever the returned dict gains or loses keys.
# script.py checks this at startup to catch stale-loader deployments.
LOADER_VERSION = 3


# -------------------------------------------------------
# CRADDYS INTERNAL DEFAULTS
# Sourced from UG01 - 0100-CDY-XX-XX-T-X
# Naming: {proj}-CDY-{functional}-{spatial}-{form}-{role}-{number}-{revision}
# No classification segment in the Craddys internal format.
# -------------------------------------------------------
_CDY_DEFAULTS = {
    "project_number_format": "4digit",

    # Originator is always CDY — enforced as the only approved value
    "originators": {"CDY"},

    # Functional breakdown — XX = not applicable; projects use B1/B2 etc. for blocks.
    # XX is the only universally approved value in the Craddys protocol;
    # project-specific block codes (AA, BB, etc.) come from the BEP.
    "functional_codes": {"XX"},

    # Spatial breakdown per Craddys BEP doc
    "spatial_codes": {
        "B1":  ["BASEMENT LEVEL 01", "BASEMENT 1"],
        "B2":  ["BASEMENT LEVEL 02", "BASEMENT 2"],
        "FN":  ["FOUNDATION", "PILE", "GROUND BEAM", "SUBSTRUCTURE"],
        "F1":  ["FOUNDATION LEVEL 01"],
        "F2":  ["FOUNDATION LEVEL 02"],
        "LG":  ["LOWER GROUND FLOOR", "LG"],
        "GF":  ["GROUND FLOOR"],
        "00":  ["GROUND FLOOR"],
        "M0":  ["MEZZANINE"],
        "01":  ["FIRST FLOOR", "LEVEL 01"],
        "M1":  ["MEZZANINE"],
        "02":  ["SECOND FLOOR", "LEVEL 02"],
        "RF":  ["ROOF"],
        "ZZ":  ["SECTION", "SECTIONS", "ELEVATION", "ELEVATIONS"],
        "XX":  [],
    },

    # Form codes per Craddys BEP doc
    "form_codes": {"D", "G", "I", "L", "M", "M2", "M3", "T", "V"},

    # Role / discipline codes per Craddys BEP doc
    "role_codes": {
        "A", "B", "C", "D", "E", "F", "G", "H",
        "L", "M", "O", "P", "Q", "R", "S", "T",
        "W", "X", "Y", "Z"
    },

    # No classification segment in Craddys internal format
    "use_classification": False,
    "classification_codes": set(),

    # Sheet number: 4-digit, no classification prefix
    # Pattern: -{role}-{4digit number}
    "sheet_number_pattern": r"-[A-Z]-([0-9]{4})",

    # Craddys naming template (no classification)
    "naming_formats": {
        "Craddys Standard (No BEP)": (
            "{proj_number}-CDY-{sheet_param:Functional}-{sheet_param:Spatial}"
            "-{sheet_param:Form}-{sheet_param:Role}-{sheet_param:Number}-{rev_number}"
        )
    },

    # Flag so script.py can show a banner warning
    "using_cdy_defaults": True,
}


# -------------------------------------------------------
# PUBLIC API
# -------------------------------------------------------
def load_codes(doc, filename="codes_config.json"):
    """
    Load and return the project codes config.

    Behaviour:
    - If codes_config.json is found: load it. Exit loudly on any error.
    - If codes_config.json is missing: prompt the user to continue with
      Craddys internal defaults or cancel. Never silently fall back.
    - If the file exists but is broken: always exit with a clear error.

    Returns
    -------
    dict with keys:
        project_number_format  : str
        functional_codes       : set
        form_codes             : set
        role_codes             : set
        spatial_codes          : dict  { code: [keyword, ...] }
        sheet_number_pattern   : str   (Python regex)
        originators            : set   (empty set = no originator check)
        use_classification     : bool
        classification_codes   : set   (empty set = any numeric value accepted)
        naming_formats         : dict  { display_name: template_string }
        using_cdy_defaults     : bool  (True = no project BEP config was found)
    """

    # 1. Resolve model folder — exit loudly if we can't
    model_folder = _resolve_model_folder(doc)

    # 2. Build expected config path
    config_path = os.path.join(model_folder, filename)

    # 3. If file is missing — offer Craddys defaults, don't silently fall back
    if not os.path.isfile(config_path):
        result = forms.alert(
            "No codes_config.json found for this project.\n\n"
            "Expected location:\n{}\n\n"
            "OPTIONS:\n"
            "  [Yes]  Continue using Craddys internal naming defaults\n"
            "         (suitable for projects with no BEP).\n\n"
            "  [No]   Cancel — I will create the config file first\n"
            "         (use the BEP prompt template to generate it).".format(config_path),
            title="ISO Compliance — No Project Config Found",
            yes=True,
            no=True,
            exitscript=False
        )
        if result:
            # User chose to continue with Craddys defaults
            return dict(_CDY_DEFAULTS)
        else:
            # User chose to cancel
            forms.alert(
                "Tool cancelled.\n\n"
                "Place codes_config.json here and re-run:\n{}".format(config_path),
                title="ISO Compliance — Cancelled",
                exitscript=True
            )

    # 4. File exists — parse it. Exit loudly if malformed.
    try:
        with open(config_path, "r") as fh:
            raw = json.load(fh)
    except ValueError as exc:
        forms.alert(
            "codes_config.json could not be parsed.\n\n"
            "File: {}\n\n"
            "JSON error: {}\n\n"
            "Fix the file and re-run.".format(config_path, exc),
            title="ISO Compliance — Invalid Config",
            exitscript=True
        )

    # 5. Validate required keys — exit loudly if any are missing
    required = [
        "functional_codes",
        "form_codes",
        "role_codes",
        "spatial_codes",
        "sheet_number_pattern",
    ]
    missing = [k for k in required if k not in raw]
    if missing:
        forms.alert(
            "codes_config.json is incomplete.\n\n"
            "File: {}\n\n"
            "Missing required keys:\n{}".format(
                config_path,
                "\n".join("  - " + k for k in missing)
            ),
            title="ISO Compliance — Incomplete Config",
            exitscript=True
        )

    # 6. Build and return the project config
    return {
        "project_number_format": raw.get("project_number_format", "4digit"),
        "functional_codes":      set(raw["functional_codes"]),
        "form_codes":            set(raw["form_codes"]),
        "role_codes":            set(raw["role_codes"]),
        "spatial_codes":         raw["spatial_codes"],
        "sheet_number_pattern":  raw["sheet_number_pattern"],
        "originators":           set(raw.get("originators", [])),
        "use_classification":    bool(raw.get("use_classification", False)),
        "classification_codes":  set(str(c) for c in raw.get("classification_codes", [])),
        "naming_formats":        raw.get("naming_formats", {}),
        "using_cdy_defaults":    False,
    }


# -------------------------------------------------------
# PATH RESOLUTION
# -------------------------------------------------------
def _resolve_model_folder(doc):
    """
    Return the folder that contains the active Revit model.
    Tries four strategies in order. Exits with a diagnostic alert if all fail.
    """

    attempted = []

    # Strategy 1: workshared central path via ModelPathUtils
    try:
        if doc.IsWorkshared:
            mp = doc.GetWorksharingCentralModelPath()
            path = DB.ModelPathUtils.ConvertModelPathToUserVisiblePath(mp)
            if path and os.path.isabs(path):
                folder = os.path.dirname(path)
                if os.path.isdir(folder):
                    return folder
                attempted.append("Workshared central (folder not found on disk): " + folder)
            else:
                attempted.append("Workshared central: path not absolute or empty — got: " + repr(path))
    except Exception as exc:
        attempted.append("Workshared central: exception — " + str(exc))

    # Strategy 2: doc.PathName (local / detached / non-workshared)
    try:
        path = doc.PathName
        if path and os.path.isabs(path):
            folder = os.path.dirname(path)
            if os.path.isdir(folder):
                return folder
            attempted.append("doc.PathName (folder not found on disk): " + folder)
        else:
            attempted.append("doc.PathName: not absolute or empty — got: " + repr(path))
    except Exception as exc:
        attempted.append("doc.PathName: exception — " + str(exc))

    # Strategy 3: cloud / BIM 360 — surface as diagnostic
    try:
        path = doc.PathName
        if path and not os.path.isabs(path):
            attempted.append(
                "doc.PathName looks like a cloud/BIM360 path (not a local path): " + repr(path) +
                "\nFor cloud models, place codes_config.json in the local cache folder "
                "or ask your BIM Manager to update the loader."
            )
    except Exception as exc:
        attempted.append("Cloud path check: exception — " + str(exc))

    # Strategy 4: unsaved document
    try:
        if not doc.PathName:
            attempted.append("doc.PathName is empty — model has not been saved yet.")
    except Exception as exc:
        attempted.append("Unsaved check: exception — " + str(exc))

    # All strategies failed
    forms.alert(
        "Could not resolve the Revit model folder.\n\n"
        "The codes_config.json cannot be located without knowing where "
        "the model is saved.\n\n"
        "Diagnostics (checked in order):\n{}\n\n"
        "Possible fixes:\n"
        "  1. Save / sync the model to a local or network path.\n"
        "  2. For cloud models, ask your BIM Manager to adapt the loader.\n"
        "  3. Open the pyRevit output window for further detail.".format(
            "\n".join("  • " + a for a in attempted)
        ),
        title="ISO Compliance — Cannot Resolve Model Path",
        exitscript=True
    )


# -------------------------------------------------------
# UTILITY
# -------------------------------------------------------
def get_config_path(doc, filename="codes_config.json"):
    """Return the expected full path without exiting on failure (for diagnostics)."""
    try:
        folder = _resolve_model_folder(doc)
        return os.path.join(folder, filename)
    except SystemExit:
        return None