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
# SPATIAL NORMALISATION
# -------------------------------------------------------
def normalise_title(text):
    t = text.upper()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"LEVEL\s+0?(\d)", r"LEVEL \1", t)
    return t


# -------------------------------------------------------
# SPATIAL KEYWORDS
# -------------------------------------------------------
SPATIAL_KEYWORDS = {

    "BN": ["BASEMENT"],
    "B1": ["BASEMENT LEVEL 1", "BASEMENT 1", "BASMENT 1ST"],
    "B2": ["BASEMENT LEVEL 2", "BASEMENT 2", "BASMENT 2ND"],

    "00": ["GROUND FLOOR", "GROUND", "LEVEL 0"],
    "GF": ["GROUND FLOOR", "GROUND"],

    "LG": ["LOWER GROUND", "LOWER GROUND FLOOR"],
    "LGF": ["LOWER GROUND", "LOWER GROUND FLOOR"],
    "UG": ["UPPER GROUND", "UPPER GROUND FLOOR"],
    "UGF": ["UPPER GROUND", "UPPER GROUND FLOOR"],

    "01": ["FIRST FLOOR", "1ST FLOOR", "LEVEL 1"],
    "02": ["SECOND FLOOR", "2ND FLOOR", "LEVEL 2"],
    "03": ["THIRD FLOOR", "3RD FLOOR", "LEVEL 3"],
    "04": ["FOURTH FLOOR", "LEVEL 4"],
    "05": ["FIFTH FLOOR", "LEVEL 5"],
    "06": ["SIXTH FLOOR", "LEVEL 6"],
    "07": ["SEVENTH FLOOR", "LEVEL 7"],
    "08": ["EIGHTH FLOOR", "LEVEL 8"],
    "09": ["NINTH FLOOR", "LEVEL 9"],
    "10": ["TENTH FLOOR", "LEVEL 10"],
    "11": ["ELEVENTH FLOOR", "11TH FLOOR", "LEVEL 11"],
    "12": ["TWELFTH FLOOR", "12TH FLOOR", "LEVEL 12"],
    "13": ["THIRTEENTH FLOOR", "13TH FLOOR", "LEVEL 13"],
    "14": ["FOURTEENTH FLOOR", "14TH FLOOR", "LEVEL 14"],
    "15": ["FIFTEENTH FLOOR", "15TH FLOOR", "LEVEL 15"],
    "16": ["SIXTEENTH FLOOR", "16TH FLOOR", "LEVEL 16"],
    "17": ["SEVENTEENTH FLOOR", "17TH FLOOR", "LEVEL 17"],
    "18": ["EIGHTEENTH FLOOR", "18TH FLOOR", "LEVEL 18"],
    "19": ["NINETEENTH FLOOR", "19TH FLOOR", "LEVEL 19"],
    "20": ["TWENTIETH FLOOR", "20TH FLOOR", "LEVEL 20"],
    "21": ["TWENTY FIRST FLOOR", "21ST FLOOR", "LEVEL 21"],
    "22": ["TWENTY SECOND FLOOR", "22ND FLOOR", "LEVEL 22"],
    "23": ["TWENTY THIRD FLOOR", "23RD FLOOR", "LEVEL 23"],
    "24": ["TWENTY FOURTH FLOOR", "24TH FLOOR", "LEVEL 24"],
    "25": ["TWENTY FIFTH FLOOR", "25TH FLOOR", "LEVEL 25"],
    "26": ["TWENTY SIXTH FLOOR", "26TH FLOOR", "LEVEL 26"],
    "27": ["TWENTY SEVENTH FLOOR", "27TH FLOOR", "LEVEL 27"],
    "28": ["TWENTY EIGHTH FLOOR", "28TH FLOOR", "LEVEL 28"],
    "29": ["TWENTY NINTH FLOOR", "29TH FLOOR", "LEVEL 29"],
    "30": ["THIRTIETH FLOOR", "30TH FLOOR", "LEVEL 30"],
    "31": ["THIRTY FIRST FLOOR", "31ST FLOOR", "LEVEL 31"],
    "32": ["THIRTY SECOND FLOOR", "32ND FLOOR", "LEVEL 32"],
    "33": ["THIRTY THIRD FLOOR", "33RD FLOOR", "LEVEL 33"],
    "34": ["THIRTY FOURTH FLOOR", "34TH FLOOR", "LEVEL 34"],
    "35": ["THIRTY FIFTH FLOOR", "35TH FLOOR", "LEVEL 35"],
    "36": ["THIRTY SIXTH FLOOR", "36TH FLOOR", "LEVEL 36"],
    "37": ["THIRTY SEVENTH FLOOR", "37TH FLOOR", "LEVEL 37"],
    "38": ["THIRTY EIGHTH FLOOR", "38TH FLOOR", "LEVEL 38"],
    "39": ["THIRTY NINTH FLOOR", "39TH FLOOR", "LEVEL 39"],
    "40": ["FORTIETH FLOOR", "40TH FLOOR", "LEVEL 40"],

    "RF": ["ROOF", "ROOF LEVEL", "PARAPET"],

    "FN": ["FOUNDATION", "PILE", "SUBSTRUCTURE"],
    "F1": ["FOUNDATION LEVEL 1", "PILE LEVEL 1"],
    "F2": ["FOUNDATION LEVEL 2", "PILE LEVEL 2"],
}


# -------------------------------------------------------
# REVERSE CHECK
# -------------------------------------------------------
def validate_spatial_reverse(spatial_code, title):

    if not spatial_code:
        return None

    expected_keywords = SPATIAL_KEYWORDS.get(spatial_code)
    if not expected_keywords:
        return None

    title_u = normalise_title(title)

    if any(kw in title_u for kw in expected_keywords):
        return None

    return "Spatial code '{}' does not match title content".format(spatial_code)


# -------------------------------------------------------
# CRADDYS FORM + ROLE (ADDED)
# -------------------------------------------------------
FORM_CODES = {"D", "DR","G", "I", "L", "M","M3", "T", "V"}

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
# FORMAT SOURCES
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
# FIELD EXTRACTION
# -------------------------------------------------------
def extract_fields(sheet, template, filename):

    raw = resolve_name(template, sheet)
    parts = raw.split("-")

    def safe(i):
        return parts[i] if len(parts) > i else ""

    return {
        "project": safe(0),
        "originator": safe(1),
        "functional": safe(2),
        "spatial": safe(3),
        "type": safe(4),
        "role": safe(5),
        "number": extract_sheet_number(filename),
        "revision": get_current_revision(sheet),
    }


# -------------------------------------------------------
# INTENT INFERENCE
# -------------------------------------------------------
def infer_expected_from_title(title):

    t = title.upper()
    expected = {"spatial": None}

    if "FOUNDATION" in t or "PILE" in t or "SUBSTRUCTURE" in t:
        expected["spatial"] = {"FN", "F1", "F2"}

    elif "GROUND FLOOR" in t:
        expected["spatial"] = {"00", "GF"}

    elif "FIRST FLOOR" in t:
        expected["spatial"] = {"01"}

    elif "SECOND FLOOR" in t:
        expected["spatial"] = {"02"}

    elif "ROOF" in t:
        expected["spatial"] = {"RF"}

    return expected


# -------------------------------------------------------
# VALIDATION
# -------------------------------------------------------
REV_RE = r"^(C\d{2}|P\d{2,3}(\.\d{2})?|FC\d{2})$"


def validate(f, title):

    issues = []
    review = []

    def add(level, msg):
        issues.append((level, msg))

    if not f["project"]:
        add("ERROR", "Missing project")

    if not f["originator"]:
        add("ERROR", "Missing originator")

    if not f["type"]:
        add("ERROR", "Missing form (Type)")
    elif f["type"] not in FORM_CODES:
        add("ERROR", "Invalid form '{}' (D/DR/G/I/L/M/T/V only)".format(f["type"]))

    if not f["role"]:
        add("ERROR", "Missing role")
    elif f["role"] not in ROLE_CODES:
        add("ERROR", "Invalid role '{}'".format(f["role"]))

    if not f["number"]:
        add("ERROR", "Invalid sheet number")

    if not f["revision"]:
        add("WARNING", "Sheet has no current revision set in Revit")
    elif not re.match(REV_RE, f["revision"]):
        add("ERROR", "Invalid revision format")

    expected = infer_expected_from_title(title)

    if expected["spatial"]:
        if f["spatial"] not in expected["spatial"]:
            review.append("Spatial mismatch")

    if f["spatial"]:
        reverse_issue = validate_spatial_reverse(f["spatial"], title)
        if reverse_issue:
            review.append(reverse_issue)

    if "FOUNDATION" in title.upper():
        if f["functional"] not in {"FN", "F1", "F2", "XX"}:
            review.append("Functional likely incorrect")

    if issues:
        return "ERROR", issues

    if review:
        for r in review:
            issues.append(("WARNING", r))
        return "REVIEW", issues

    return "OK", [("OK", "ISO compliant")]


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

        project_fmt = get_project_naming_format_name()
        selected = 0

        for i, f in enumerate(formats):
            self.combo.Items.Add(f.name)
            if project_fmt and f.name == project_fmt:
                selected = i

        self.combo.SelectedIndex = selected
        self.combo.SelectionChanged += self.run
        self.run(None, None)

    def run(self, s, e):

        fmt = self.formats[self.combo.SelectedIndex]

        sheets = DB.FilteredElementCollector(doc)\
            .OfCategory(DB.BuiltInCategory.OST_Sheets)\
            .WhereElementIsNotElementType()\
            .ToElements()

        rows = ObservableCollection[object]()

        for sh in sheets:

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
