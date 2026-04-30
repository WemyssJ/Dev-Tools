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
# REVISION
# -------------------------------------------------------
def get_current_revision(sheet):
    try:
        p = sheet.get_Parameter(DB.BuiltInParameter.SHEET_CURRENT_REVISION)
        return p.AsString() if p else ""
    except:
        return ""


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
        name = name.replace("{rev_number}", get_current_revision(sheet) or "")

    return name


# -------------------------------------------------------
# FIELD EXTRACTION
# -------------------------------------------------------
def extract_fields(sheet, template):

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
        "number": safe(6),
        "revision": safe(7),
    }


# -------------------------------------------------------
# INTENT INFERENCE (TITLE → EXPECTED CODES)
# -------------------------------------------------------
def infer_expected_from_title(title):

    t = title.upper()

    expected = {
        "spatial": None,
        "functional_hint": None
    }

    if "FOUNDATION" in t or "PILE" in t or "SUBSTRUCTURE" in t:
        expected["spatial"] = {"FN", "F1", "F2"}

    elif "GROUND FLOOR" in t:
        expected["spatial"] = {"00", "GF"}

    elif "FIRST FLOOR" in t or "1ST FLOOR" in t:
        expected["spatial"] = {"01"}

    elif "SECOND FLOOR" in t or "2ND FLOOR" in t:
        expected["spatial"] = {"02"}

    elif "ROOF" in t:
        expected["spatial"] = {"RF"}

    return expected


# -------------------------------------------------------
# VALIDATION ENGINE
# -------------------------------------------------------
PROJECT_RE = r"^\d{4,6}(-[A-Z0-9]+)?$"
ORIGINATOR_RE = r"^[A-Z]{2,3}$"
NUMBER_RE = r"^\d{4,6}$"
REV_RE = r"^(P\d{2,3}(\.\d{2})?|C\d{2}(\.\d{2})?|FC\d{2})$"

FUNCTIONAL = {"AA","BB","CC","DD","A1","A2","V1","V2","V3","XX","ZZ"}

SPATIAL = {
    "B1","B2","FN","F1","F2","LG","GF","00","M0","M1","01","02","RF","ZZ","XX"
}

TYPE_RE = r"^[DGILMTV][23]?$"


def validate(f, title):

    issues = []
    review_flags = []

    def add(level, msg):
        issues.append((level, msg))

    # -----------------------
    # HARD RULES (ERROR)
    # -----------------------
    if not f["project"]:
        add("ERROR", "Missing project")

    if not f["originator"]:
        add("ERROR", "Missing originator")

    if not f["type"]:
        add("ERROR", "Missing type")

    if not f["role"]:
        add("ERROR", "Missing role")

    if not re.match(NUMBER_RE, f["number"]):
        add("ERROR", "Invalid sheet number")

    # Revision
    if not f["revision"]:
        add("WARNING", "Missing revision (expected P## / C## / FC##)")
    elif not re.match(REV_RE, f["revision"]):
        add("ERROR", "Invalid revision format (P## / C## / FC## / FC01)")

    # -----------------------
    # SEMANTIC RULES (REVIEW ONLY)
    # -----------------------
    expected = infer_expected_from_title(title)

    if expected["spatial"]:
        if f["spatial"] not in expected["spatial"]:
            review_flags.append(
                "Spatial mismatch: expected {} based on title".format(
                    ",".join(expected["spatial"])
                )
            )

    if "FOUNDATION" in title.upper():
        if f["functional"] not in {"FN", "F1", "F2", "XX"}:
            review_flags.append(
                "Functional likely should be FN/F1/F2 for foundation content"
            )

    # merge review flags into issues as WARNINGs (so everything shows in message box)
    for r in review_flags:
        issues.append(("WARNING", r))

    # -----------------------
    # STATUS DECISION (FIXED)
    # -----------------------

    has_error = any(i[0] == "ERROR" for i in issues)
    has_warning = any(i[0] == "WARNING" for i in issues)

    if has_error:
        status = "ERROR"
    elif has_warning:
        status = "REVIEW"
    else:
        status = "OK"

    # always ensure something is shown
    if not issues:
        issues = [("OK", "ISO compliant")]

    return status, issues


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
            fields = extract_fields(sh, fmt.template)
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