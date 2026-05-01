# -*- coding: utf-8 -*-

import os
import re
import json
import ConfigParser

from pyrevit import revit, DB, forms, script
from System.Collections.ObjectModel import ObservableCollection
from System.Dynamic import ExpandoObject
from System.Windows import Clipboard

import codes_loader
from codes_loader import load_codes

# Guard against a stale codes_loader.py on disk.
_REQUIRED_LOADER_VERSION = 3
_actual_version = getattr(codes_loader, "LOADER_VERSION", 0)
if _actual_version < _REQUIRED_LOADER_VERSION:
    forms.alert(
        "codes_loader.py is out of date (version {} found, {} required)."
        "Please replace codes_loader.py in your pushbutton folder with the "
        "latest version and reload pyRevit.".format(
            _actual_version, _REQUIRED_LOADER_VERSION
        ),
        title="ISO Compliance — Stale Loader",
        exitscript=True
    )

logger = script.get_logger()
doc = revit.doc

if not doc:
    forms.alert("No active Revit document found.", exitscript=True)

proj_info = doc.ProjectInformation

# -------------------------------------------------------
# LOAD PER-PROJECT APPROVED CODES
# Reads codes_config.json from the Revit model folder.
# If missing, prompts user to continue with Craddys defaults.
# -------------------------------------------------------
CODES = load_codes(doc)

SPATIAL_KEYWORDS     = CODES["spatial_codes"]
FUNCTIONAL_CODES     = CODES["functional_codes"]
FORM_CODES           = CODES["form_codes"]
ROLE_CODES           = CODES["role_codes"]
SHEET_NUM_PATTERN    = CODES["sheet_number_pattern"]
ORIGINATORS          = CODES["originators"]
USE_CLASSIFICATION   = CODES["use_classification"]
CLASSIFICATION_CODES = CODES["classification_codes"]
_EXTRA_FORMATS       = CODES["naming_formats"]
USING_CDY_DEFAULTS   = CODES["using_cdy_defaults"]


# -------------------------------------------------------
# WARN IF RUNNING ON CRADDYS DEFAULTS (NO BEP CONFIG)
# -------------------------------------------------------
if USING_CDY_DEFAULTS:
    forms.alert(
        "Running with Craddys internal naming defaults (no codes_config.json found)."
        "Functional codes will not be fully validated — only XX is approved"
        "in the Craddys standard. Project-specific block codes (AA, BB, CC etc.)"
        "require a BEP config file."
        "To generate a codes_config.json, use the BEP prompt template.",
        title="ISO Compliance — Using Craddys Defaults",
        warn_icon=True
    )

# -------------------------------------------------------
# SAFE PARAMETER ACCESS
# -------------------------------------------------------
def _safe_lookup_param_as_string(elem, name):
    if elem is None:
        return ""
    try:
        p = elem.LookupParameter(name)
        if p:
            return p.AsString() or ""
    except:
        pass
    return ""


# -------------------------------------------------------
# PROJECT NUMBER
# -------------------------------------------------------
def get_project_number():
    try:
        p = proj_info.get_Parameter(DB.BuiltInParameter.PROJECT_NUMBER)
        return p.AsString().strip() if p else ""
    except:
        return ""


def get_project_naming_format_name():
    try:
        p = proj_info.LookupParameter("Naming Format")
        return p.AsString() if p else None
    except:
        return None


# -------------------------------------------------------
# REVISION
# -------------------------------------------------------
def get_current_revision(sheet):
    try:
        p = sheet.get_Parameter(DB.BuiltInParameter.SHEET_CURRENT_REVISION)
        return p.AsString() if p else ""
    except:
        return ""


# -------------------------------------------------------
# SHEET NUMBER — now uses SHEET_NUM_PATTERN from config
# -------------------------------------------------------
def extract_sheet_number(text):
    m = re.search(SHEET_NUM_PATTERN, text)  # ← was hardcoded regex
    return m.group(1) if m else ""


# -------------------------------------------------------
# RESOLVE NAME
# -------------------------------------------------------
def resolve_name(template, sheet):

    name = template
    name = name.replace("{proj_number}", get_project_number())

    for m in re.findall(r"{sheet_param:([^}]+)}", name):
        name = name.replace(
            "{sheet_param:%s}" % m,
            _safe_lookup_param_as_string(sheet, m) or ""
        )

    if "{rev_number}" in name:
        rev = get_current_revision(sheet)
        name = name.replace("{rev_number}", rev or "")

    return name


# -------------------------------------------------------
# NORMALISE TITLE
# -------------------------------------------------------
def normalise_title(text):
    return re.sub(r"\s+", " ", text.upper())


# -------------------------------------------------------
# NAMING FORMAT MODEL
# -------------------------------------------------------
class NamingFormat:
    def __init__(self, name, template, builtin=True):
        self.name = name
        self.template = template
        self.builtin = builtin


# -------------------------------------------------------
# PRINT SHEETS CONFIG
# -------------------------------------------------------
def extract_naming_formats_from_print_sheets():

    out = []

    def find_tab(p):
        cur = os.path.abspath(p)
        while True:
            if cur.lower().endswith(".tab"):
                return cur
            parent = os.path.dirname(cur)
            if parent == cur:
                return None
            cur = parent

    def find_script(tab):
        for r, d, f in os.walk(tab):
            if r.lower().endswith("print sheets.pushbutton"):
                p = os.path.join(r, "script.py")
                if os.path.exists(p):
                    return p
        return None

    tab = find_tab(__file__)
    if not tab:
        return out

    script_path = find_script(tab)
    if not script_path:
        return out

    txt = open(script_path).read()

    matches = re.findall(
        r"name\s*=\s*['\"]([^'\"]+)['\"].*?template\s*=\s*['\"]([^'\"]+)['\"]",
        txt,
        re.DOTALL
    )

    for n, t in matches:
        out.append(NamingFormat(n, t, True))

    return out


# -------------------------------------------------------
# PYREVIT CONFIG FORMATS
# -------------------------------------------------------
def get_user_naming_formats_from_pyrevit_config():
    out = []
    path = os.path.join(os.environ.get("APPDATA", ""), "pyRevit", "pyRevit_config.ini")

    if not os.path.exists(path):
        return out

    cp = ConfigParser.ConfigParser()
    cp.read(path)

    if not cp.has_section("Print Sheets_config"):
        return out

    if not cp.has_option("Print Sheets_config", "namingformats"):
        return out

    try:
        raw = cp.get("Print Sheets_config", "namingformats")
        data = json.loads(raw)

        for k, v in data.items():
            if v:
                out.append(NamingFormat(k, v, False))
    except:
        pass

    return out


# -------------------------------------------------------
# FIELD EXTRACTION
# -------------------------------------------------------
def extract_fields(sheet, template, filename):
    """
    Parse the resolved filename into its ISO 19650 field components.

    Handles both naming conventions:
      With classification:    {proj}-{orig}-{func}-{spatial}-{form}-{role}-{class}-{num}
      Without classification: {proj}-{orig}-{func}-{spatial}-{form}-{role}-{num}

    The presence/absence of the classification segment is controlled by
    USE_CLASSIFICATION from codes_config.json.
    """

    raw = resolve_name(template, sheet)
    parts = raw.split("-")

    project = ""
    start_index = 0

    project_match = re.match(r"^(\d+-[A-Z]\d+)", raw)

    if project_match:
        project = project_match.group(1)
        start_index = len(project.split("-"))
    else:
        project = parts[0]
        start_index = 1

    def safe(i):
        idx = start_index + i
        return parts[idx] if len(parts) > idx else ""

    # Extract classification: sits after role (index 4), before sheet number.
    # Only consumed when USE_CLASSIFICATION is True.
    classification = ""
    if USE_CLASSIFICATION:
        classification = safe(5)

    return {
        "project":        project,
        "originator":     safe(0),
        "functional":     safe(1),
        "spatial":        safe(2),
        "type":           safe(3),
        "role":           safe(4),
        "classification": classification,
        "number":         extract_sheet_number(filename),
        "revision":       get_current_revision(sheet),
    }


# -------------------------------------------------------
# INTENT INFERENCE
# -------------------------------------------------------
def infer_expected_from_title(title):

    t = normalise_title(title)

    if re.search(r"\bSECTION|SECTIONS\b", t):
        return {"spatial": {"ZZ"}}

    if re.search(r"\bELEVATION|ELEVATIONS\b", t):
        return {"spatial": {"ZZ"}}

    if re.search(r"\bUPPER GROUND FLOOR|UG\b", t):
        return {"spatial": {"UG"}}

    if re.search(r"\bLOWER GROUND FLOOR|LG\b", t):
        return {"spatial": {"LG"}}

    if re.search(r"\b(FIRST FLOOR|LEVEL\s*01|01)\b", t):
        return {"spatial": {"01"}}

    if re.search(r"\b(SECOND FLOOR|LEVEL\s*02|02)\b", t):
        return {"spatial": {"02"}}

    if "GROUND FLOOR" in t:
        return {"spatial": {"00"}}

    if "ROOF" in t:
        return {"spatial": {"RF"}}

    if any(x in t for x in ["FOUNDATION", "PILE", "GROUND BEAM", "SUBSTRUCTURE"]):
        return {"spatial": {"FN"}}

    return {"spatial": None}


# -------------------------------------------------------
# REVERSE CHECK
# -------------------------------------------------------
def validate_spatial_reverse(spatial_code, title):

    if not spatial_code:
        return None

    title_u = normalise_title(title)

    if spatial_code == "GS":
        if "SECTION" in title_u or "SECTIONS" in title_u:
            return None
        return "Spatial code 'GS' may not match title content"

    expected_keywords = SPATIAL_KEYWORDS.get(spatial_code)
    if not expected_keywords:
        return None

    if any(kw in title_u for kw in expected_keywords):
        return None

    return "Spatial code '{}' may not match title content".format(spatial_code)


# -------------------------------------------------------
# VALIDATION — now checks ORIGINATORS from config
# -------------------------------------------------------
def validate(f, title):

    issues = []
    review = []

    def add(level, msg):
        issues.append((level, msg))

    # Originator
    if not f["originator"]:
        add("ERROR", "Missing originator")
    elif ORIGINATORS and f["originator"] not in ORIGINATORS:  # ← NEW
        add("ERROR", "Originator '{}' not in approved list: {}".format(
            f["originator"], ", ".join(sorted(ORIGINATORS))
        ))

    # Functional
    if not f["functional"]:
        add("ERROR", "Missing functional breakdown")
    elif f["functional"] not in FUNCTIONAL_CODES:
        review.append("Unknown functional code '{}' (review required)".format(f["functional"]))

    # Form / type
    if not f["type"]:
        add("ERROR", "Missing form (Type)")
    elif f["type"] not in FORM_CODES:
        add("ERROR", "Invalid form '{}'".format(f["type"]))

    # Role
    if not f["role"]:
        add("ERROR", "Missing role")
    elif f["role"] not in ROLE_CODES:                         # ← NEW
        add("ERROR", "Invalid role '{}'".format(f["role"]))

    # Classification (only when enabled in config)
    if USE_CLASSIFICATION:
        cls = f["classification"]
        if not cls:
            add("ERROR", "Missing classification code")
        elif not re.match(r"^\d{2,3}$", cls):
            # Must be 2-3 digits regardless of whether an approved list exists
            add("ERROR", "Classification '{}' is not a valid 2-3 digit code".format(cls))
        elif CLASSIFICATION_CODES and cls not in CLASSIFICATION_CODES:
            # Approved list is defined in codes_config.json — enforce it
            add("ERROR", "Classification '{}' not in approved list: {}".format(
                cls, ", ".join(sorted(CLASSIFICATION_CODES))
            ))

    # Sheet number
    if not f["number"]:
        add("ERROR", "Invalid sheet number")

    # Spatial intent check
    expected = infer_expected_from_title(title)
    if expected.get("spatial"):
        if f["spatial"] not in expected["spatial"]:
            review.append(
                "Spatial mismatch (expected: {})".format("/".join(expected["spatial"]))
            )

    # Spatial reverse check
    reverse_issue = validate_spatial_reverse(f["spatial"], title)
    if reverse_issue:
        review.append(reverse_issue)

    if issues:
        return "ERROR", issues

    if review:
        for r in review:
            issues.append(("WARNING", r))
        return "REVIEW", issues

    return "OK", [("OK", "ISO19650 compliant")]


# -------------------------------------------------------
# EXPORT
# -------------------------------------------------------
def export(rows):
    out = ["Sheet\tFilename\tStatus\tMessage"]

    for r in rows:
        out.append("{}\t{}\t{}\t{}".format(
            r.Sheet, r.Name, r.Status, r.Message
        ))

    Clipboard.SetText("\n".join(out))


# -------------------------------------------------------
# UI
# -------------------------------------------------------
class Window(forms.WPFWindow):

    def __init__(self, xaml, formats):
        forms.WPFWindow.__init__(self, xaml)

        self.formats = formats
        self.combo = self.FindName("NamingCombo")
        self.grid = self.FindName("ResultsGrid")
        self.hide_no_rev = self.FindName("HideNoRevisionCheck")

        for f in formats:
            self.combo.Items.Add(f.name)

        # Auto-select the format that matches the project "Naming Format" parameter.
        # Falls back to index 0 if the parameter is unset or no name matches.
        self.combo.SelectedIndex = self._resolve_default_format_index()

        self.combo.SelectionChanged += self.run
        self.hide_no_rev.Checked += self.run
        self.hide_no_rev.Unchecked += self.run

        self.run(None, None)

    def _resolve_default_format_index(self):
        """
        Read the project-level 'Naming Format' parameter and return the index
        of the first format whose name matches (case-insensitive).
        Returns 0 if the parameter is blank or no format name matches.
        """
        proj_fmt_name = get_project_naming_format_name()
        if proj_fmt_name:
            proj_fmt_name_lower = proj_fmt_name.strip().lower()
            for i, f in enumerate(self.formats):
                if f.name.strip().lower() == proj_fmt_name_lower:
                    return i
            # Parameter is set but no exact match — try partial/contains match
            for i, f in enumerate(self.formats):
                if proj_fmt_name_lower in f.name.strip().lower():
                    return i
        return 0

    def run(self, s, e):

        fmt = self.formats[self.combo.SelectedIndex]

        sheets = DB.FilteredElementCollector(doc)\
            .OfCategory(DB.BuiltInCategory.OST_Sheets)\
            .WhereElementIsNotElementType()\
            .ToElements()

        rows = ObservableCollection[object]()

        hide_no_rev = self.hide_no_rev.IsChecked if self.hide_no_rev else False

        for sh in sheets:

            if hide_no_rev and not get_current_revision(sh):
                continue

            name = resolve_name(fmt.template, sh)
            fields = extract_fields(sh, fmt.template, name)

            status, issues = validate(fields, sh.Name)

            obj = ExpandoObject()
            setattr(obj, "Sheet", sh.SheetNumber)
            setattr(obj, "Name", name)
            setattr(obj, "Status", status)
            setattr(obj, "Message", "\n".join([i[1] for i in issues]))

            rows.Add(obj)

        self.grid.ItemsSource = rows
        export(rows)


# -------------------------------------------------------
# RUN
# -------------------------------------------------------
formats = []
formats.extend(extract_naming_formats_from_print_sheets())
formats.extend(get_user_naming_formats_from_pyrevit_config())

# Merge naming formats from codes_config.json (project-specific)  ← NEW
for _name, _tmpl in _EXTRA_FORMATS.items():
    formats.append(NamingFormat(_name, _tmpl, builtin=False))

if not formats:
    forms.alert("No naming formats found.", exitscript=True)

Window(
    os.path.join(os.path.dirname(__file__), "ISOCompliance.xaml"),
    formats
).ShowDialog()