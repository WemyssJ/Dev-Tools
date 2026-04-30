# -*- coding: utf-8 -*-

import os
import re
import json
import ConfigParser

from pyrevit import revit, DB, forms, script
from System.Collections.ObjectModel import ObservableCollection
from System.Dynamic import ExpandoObject
from System.Windows import Clipboard

logger = script.get_logger()
doc = revit.doc

if not doc:
    forms.alert("No active Revit document found.", exitscript=True)

proj_info = doc.ProjectInformation


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
# SHEET NUMBER
# -------------------------------------------------------
def extract_sheet_number(text):
    m = re.search(r"-S-(?:\d{3}-)?(\d{4,6})", text)
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
# SPATIAL KEYWORDS
# -------------------------------------------------------
SPATIAL_KEYWORDS = {
    "00": ["GROUND FLOOR"],
    "LG": ["LOWER GROUND FLOOR", "LG"],
    "UG": ["UPPER GROUND FLOOR", "UG"],
    "01": ["FIRST FLOOR", "LEVEL 01", "01"],
    "02": ["SECOND FLOOR", "LEVEL 02", "02"],
    "RF": ["ROOF"],
    "FN": ["FOUNDATION", "PILE", "GROUND BEAM"],
    "GS": ["SECTION", "SECTIONS"],   # ✅ FIX: GS is now real and valid
    "ZZ": ["ELEVATION", "ELEVATIONS"]  # keep ZZ purely elevations/abstract
}


# -------------------------------------------------------
# FUNCTIONAL CODES
# -------------------------------------------------------
FUNCTIONAL_CODES = {
    "AA", "BB", "CC",
    "V1", "V2", "V3", "EW", "ZZ", "XX"
}


# -------------------------------------------------------
# FORM + ROLE
# -------------------------------------------------------
FORM_CODES = {"D", "DR", "G", "I", "L", "M", "M3", "T", "V"}

ROLE_CODES = {
    "A","B","C","D","E","F","G","H","L","M",
    "O","P","Q","R","S","T","W","X","Y","Z"
}


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

    return {
        "project": project,
        "originator": safe(0),
        "functional": safe(1),
        "spatial": safe(2),
        "type": safe(3),
        "role": safe(4),
        "number": extract_sheet_number(filename),
        "revision": get_current_revision(sheet),
    }


# -------------------------------------------------------
# INTENT INFERENCE (FIXED GS + ZZ RULES)
# -------------------------------------------------------
def infer_expected_from_title(title):

    t = normalise_title(title)

    # Sections = GS ONLY (FIXED)
    if re.search(r"\bSECTION|SECTIONS\b", t):
        return {"spatial": {"GS"}}

    # Elevations = ZZ
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

    if any(x in t for x in ["FOUNDATION", "PILE", "GROUND BEAM"]):
        return {"spatial": {"FN"}}

    return {"spatial": None}


# -------------------------------------------------------
# REVERSE CHECK (UPDATED FOR GS)
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
# VALIDATION
# -------------------------------------------------------
def validate(f, title):

    issues = []
    review = []

    def add(level, msg):
        issues.append((level, msg))

    if not f["originator"]:
        add("ERROR", "Missing originator")

    if not f["functional"]:
        add("ERROR", "Missing functional breakdown")
    elif f["functional"] not in FUNCTIONAL_CODES:
        review.append("Unknown functional code '{}' (review required)".format(f["functional"]))

    if not f["type"]:
        add("ERROR", "Missing form (Type)")
    elif f["type"] not in FORM_CODES:
        add("ERROR", "Invalid form '{}'".format(f["type"]))

    if not f["role"]:
        add("ERROR", "Missing role")

    if not f["number"]:
        add("ERROR", "Invalid sheet number")

    expected = infer_expected_from_title(title)

    if expected.get("spatial"):
        if f["spatial"] not in expected["spatial"]:
            review.append(
                "Spatial mismatch (expected: {})".format("/".join(expected["spatial"]))
            )

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

        self.combo.SelectedIndex = 0

        self.combo.SelectionChanged += self.run
        self.hide_no_rev.Checked += self.run
        self.hide_no_rev.Unchecked += self.run

        self.run(None, None)

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

if not formats:
    forms.alert("No naming formats found.", exitscript=True)

Window(
    os.path.join(os.path.dirname(__file__), "ISOCompliance.xaml"),
    formats
).ShowDialog()
