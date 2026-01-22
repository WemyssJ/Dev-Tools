import sys
import os
import tempfile
import datetime
import re
import json
import ConfigParser

# pyRevit imports
from pyrevit import forms
from pyrevit import revit, DB
from pyrevit import script

# system imports
from System.Windows.Data import Binding
from System.Windows.Controls import DataGridTextColumn, DataGridLength
from System.Collections.ObjectModel import ObservableCollection
from System.Dynamic import ExpandoObject
from System.Windows import Clipboard

##############################################################################################
# TELEMETRY IMPORTS #
##############################################################################################
# Only works IF specified TELEMETRY_JSON path exists within %AppData%\pyRevit\Extensions\BIMTools.extension\lib\telemetry_auto.py"
# Records tool usage by date & revit version
import os, sys

# Add lib folder for telemetry_auto
lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'lib'))
if lib_path not in sys.path:
    sys.path.append(lib_path)

import telemetry_auto

tool_name = os.path.basename(os.path.dirname(__file__)) 
TOOL_NAME = tool_name.replace(".pushbutton", "")
telemetry_auto.log_tool_usage(TOOL_NAME)
##############################################################################################

logger = script.get_logger()

# -------------------------
# Document acquisition
# -------------------------
doc = revit.doc
if not doc:
    forms.alert("No active Revit document found. Open a project before running this script.", exitscript=True)

proj_info = doc.ProjectInformation
project_number = ""
if proj_info:
    pn_param = proj_info.get_Parameter(DB.BuiltInParameter.PROJECT_NUMBER)
    if pn_param:
        project_number = pn_param.AsString() or ""

# -------------------------
# Helper functions
# -------------------------
def _safe_lookup_param_as_string(elem, param_name):
    if elem is None:
        return ""
    try:
        p = elem.LookupParameter(param_name)
        if p:
            return p.AsString() or ""
    except:
        return ""
    return ""

def _gather_text_candidates_from_element(elem):
    if elem is None:
        return []
    candidates = []
    for attr in ("Name", "SequenceName", "Description"):
        val = getattr(elem, attr, None)
        if val:
            candidates.append(str(val))
    for pn in ("Description", "Sequence Description", "SequenceDescription", "Notes", "Comments"):
        v = _safe_lookup_param_as_string(elem, pn)
        if v:
            candidates.append(str(v))
    return candidates

def is_manual_override_sequence(revision_elem, seq_elem):
    needle = "MANUAL OVERRIDE"
    seq_texts = _gather_text_candidates_from_element(seq_elem)
    rev_texts = _gather_text_candidates_from_element(revision_elem)
    for t in seq_texts + rev_texts:
        if t and needle in t.upper():
            return True
    return False

# -------------------------
# Naming protocol library
# -------------------------
class NamingFormat:
    def __init__(self, name, template, builtin=True):
        self.name = name
        self.template = template
        self.builtin = builtin

def get_user_naming_formats_from_pyrevit_config():
    user_formats = []
    config_path = os.path.join(os.environ.get("APPDATA", ""), "pyRevit", "pyRevit_config.ini")
    if not os.path.exists(config_path):
        return user_formats

    cp = ConfigParser.ConfigParser()
    try:
        cp.read(config_path)
    except:
        return user_formats

    if not cp.has_section("Print Sheets_config"):
        return user_formats
    if not cp.has_option("Print Sheets_config", "namingformats"):
        return user_formats

    raw = cp.get("Print Sheets_config", "namingformats")
    if not raw:
        return user_formats

    try:
        data = json.loads(raw)
    except Exception:
        logger.warning("Failed to parse namingformats JSON")
        return user_formats

    for name, template in data.items():
        if template:
            user_formats.append(NamingFormat(name="{}".format(name), template=template, builtin=False))

    return user_formats

# -------------------------
# Dynamic .tab discovery & Print Sheets extraction
# -------------------------
def find_tab_root(start_path):
    cur = os.path.abspath(start_path)
    while True:
        if cur.lower().endswith(".tab"):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent

def find_print_sheets_script(tab_root):
    if not tab_root or not os.path.exists(tab_root):
        return None
    for root, dirs, files in os.walk(tab_root):
        if root.lower().endswith("print sheets.pushbutton"):
            script_path = os.path.join(root, "script.py")
            if os.path.exists(script_path):
                return script_path
    return None

def extract_naming_formats_from_print_sheets():
    extracted = []
    this_script = __file__
    tab_root = find_tab_root(this_script)
    if not tab_root:
        logger.warning("No .tab root found above {}".format(this_script))
        return extracted

    script_path = find_print_sheets_script(tab_root)
    if not script_path:
        logger.warning("Print Sheets script not found under {}".format(tab_root))
        return extracted

    try:
        with open(script_path, "r") as fh:
            text = fh.read()
    except Exception as ex:
        logger.warning("Failed reading Print Sheets script: {}".format(ex))
        return extracted

    m = re.search(
        r"@staticmethod\s*\n\s*def\s+get_default_naming_formats\s*\(\s*\)\s*:\s*return\s*\[(.*?)\]\s*",
        text,
        re.DOTALL
    )
    if not m:
        logger.warning("get_default_naming_formats() not found in Print Sheets script")
        return extracted

    block = m.group(1)
    pairs = re.findall(
        r"name\s*=\s*['\"]([^'\"]+)['\"].*?"
        r"template\s*=\s*['\"]([^'\"]+)['\"]",
        block,
        re.DOTALL
    )
    for name, template in pairs:
        extracted.append(NamingFormat(name=name, template=template, builtin=True))

    return extracted

# -------------------------
# Document class for combo
# -------------------------
class AvailableDoc(object):
    def __init__(self, name, hash_val, linked, doc_ref):
        self.Name = name
        self.Hash = hash_val
        self.Linked = linked
        self.DocRef = doc_ref

def get_documents_list():
    docs = [AvailableDoc(name=doc.Title, hash_val=doc.GetHashCode(), linked=False, doc_ref=doc)]
    linked_docs = DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkInstance).ToElements()
    for ld in linked_docs:
        link_doc = ld.GetLinkDocument()
        if link_doc:
            docs.append(AvailableDoc(name=link_doc.Title, hash_val=link_doc.GetHashCode(), linked=True, doc_ref=link_doc))
    return docs

# -------------------------
# Collect sheets and revisions
# -------------------------
def collect_sheets_and_revisions(doc_obj):
    doc = doc_obj.DocRef
    if not doc:
        return [], [], []

    sheets = DB.FilteredElementCollector(doc)\
        .OfCategory(DB.BuiltInCategory.OST_Sheets)\
        .WhereElementIsNotElementType()\
        .ToElements()

    revSeqs = DB.FilteredElementCollector(doc).OfClass(DB.RevisionNumberingSequence).ToElements()
    revIds = DB.Revision.GetAllRevisionIds(doc)
    revs = [doc.GetElement(i) for i in revIds if i is not None]

    return sheets, revs, revSeqs

# -------------------------
# Build revision rows
# -------------------------
def build_rows_out(template, doc_obj, split_p_c=False, hide_unused_revisions=True, ga_override=False, show_illegible_dates=True):
    import datetime
    sep = "\t"
    rowsOut = []

    sheets, revs, revSeqs = collect_sheets_and_revisions(doc_obj)
    if not sheets:
        return []

    # Collect used revision IDs if hiding unused
    used_revision_ids = set()
    if hide_unused_revisions:
        for s in sheets:
            try:
                for rid in s.GetAllRevisionIds():
                    used_revision_ids.add(rid)
            except:
                pass

    if "{sheet_param:Sheet Name}" in template:
        split_idx = template.index("{sheet_param:Sheet Name}")
        doc_no_template = template[:split_idx]
        doc_name_template = template[split_idx:]
    else:
        doc_no_template = template
        doc_name_template = ""

    def normalize_rev_date(r):
        rev_date = r.RevisionDate
        if isinstance(rev_date, datetime.datetime):
            return rev_date.date()
        elif isinstance(rev_date, datetime.date):
            return rev_date
        else:
            try:
                return datetime.datetime.strptime(str(rev_date), "%d.%m.%y").date()
            except:
                return str(rev_date)  # keep illegible date as string

    # Build unique revision columns
    date_type_list = []
    for r in revs:
        if r is None:
            continue

        # Skip unused revisions if toggle enabled
        if hide_unused_revisions and r.Id not in used_revision_ids:
            continue

        rs = doc_obj.DocRef.GetElement(r.RevisionNumberingSequenceId)
        if rs is None or is_manual_override_sequence(r, rs):
            continue

        rev_date = normalize_rev_date(r)

        # Skip illegible dates only if the toggle is set to hide them
        if not isinstance(rev_date, datetime.date) and not show_illegible_dates:
            continue

        name_upper = rs.Name.upper() if rs.Name else ""
        if name_upper.startswith("P"):
            rev_type = "P"
        elif name_upper.startswith("C"):
            rev_type = "C"
        else:
            rev_type = "X"

        key = (rev_date, rev_type) if split_p_c else (rev_date, "All")
        if key not in date_type_list:
            date_type_list.append(key)

    # Sort revisions: date, then P before C
    def sort_key(x):
        dt, typ = x
        # make illegible dates go last
        dt_sort = dt if isinstance(dt, datetime.date) else datetime.date.max
        return (dt_sort, 0 if typ == "P" else (1 if typ == "C" else 2))

    date_type_list.sort(key=sort_key)

    # Header
    header = ["Document No.", "Document Name"] + [
        d[0].strftime("%d.%m.%y") if isinstance(d[0], datetime.date) else str(d[0])
        for d in date_type_list
    ]
    rowsOut.append(sep.join(header))

    def safe_sheet_number(s):
        try:
            return s.SheetNumber
        except:
            return ""

    sorted_sheets = sorted(sheets, key=safe_sheet_number)

    # Build sheet rows
    for s in sorted_sheets:
        if s is None:
            continue

        # Document No.
        doc_no = doc_no_template.replace("{proj_number}", project_number)
        for match in re.findall(r"{sheet_param:([^}]+)}", doc_no):
            doc_no = doc_no.replace("{sheet_param:%s}" % match, _safe_lookup_param_as_string(s, match))
        for match in re.findall(r"{proj_param:([^}]+)}", doc_no):
            doc_no = doc_no.replace("{proj_param:%s}" % match, _safe_lookup_param_as_string(proj_info, match))
        doc_no = re.sub(r"[-_]*\{rev_number\}", "", doc_no)
        doc_no = re.sub(r"\.pdf$", "", doc_no, flags=re.IGNORECASE)
        doc_no = doc_no.rstrip("-_ ")

        # Document Name
        doc_name = doc_name_template
        for match in re.findall(r"{sheet_param:([^}]+)}", doc_name):
            doc_name = doc_name.replace("{sheet_param:%s}" % match, _safe_lookup_param_as_string(s, match))
        for match in re.findall(r"{proj_param:([^}]+)}", doc_name):
            doc_name = doc_name.replace("{proj_param:%s}" % match, _safe_lookup_param_as_string(proj_info, match))
        doc_name = re.sub(r"[-_]*\{rev_number\}", "", doc_name)
        doc_name = re.sub(r"\.pdf$", "", doc_name, flags=re.IGNORECASE)
        doc_name = doc_name.rstrip("-_ ")

        # GA override
        if ga_override:
            doc_name = re.sub(r"\bGENERAL\s+ARRANGEMENT\b", "GA", doc_name, flags=re.IGNORECASE)

        # Map revisions on this sheet
        sheetRevIds = set(s.GetAllRevisionIds())
        rev_map = {}
        seq_counters = {}

        for r in revs:
            if r is None or r.Id not in sheetRevIds:
                continue

            rs = doc_obj.DocRef.GetElement(r.RevisionNumberingSequenceId)
            if rs is None or is_manual_override_sequence(r, rs):
                continue

            rev_date = normalize_rev_date(r)
            if not isinstance(rev_date, datetime.date) and not show_illegible_dates:
                continue

            name_upper = rs.Name.upper() if rs.Name else ""
            rev_type = "P" if name_upper.startswith("P") else ("C" if name_upper.startswith("C") else "X")
            key = (rev_date, rev_type) if split_p_c else (rev_date, "All")
            rev_map.setdefault(key, []).append(r)
            seq_counters.setdefault(rs.Name, 0)

        # Emit revision values
        rev_values = []
        for dt_key in date_type_list:
            revs_on_key = rev_map.get(dt_key, [])
            if not revs_on_key:
                rev_values.append("")
                continue

            # For each revision on this sheet/date/type, build its label
            rev_labels = []
            for r in revs_on_key:
                rs = doc_obj.DocRef.GetElement(r.RevisionNumberingSequenceId)
                idx = seq_counters.get(rs.Name, 0)

                char_seq = []
                if rs.NumberType == DB.RevisionNumberType.Numeric:
                    settings = rs.GetNumericRevisionSettings()
                    for n in range(settings.StartNumber, 99):
                        char_seq.append(settings.Prefix + str(n).rjust(settings.MinimumDigits, "0") + settings.Suffix)
                else:
                    settings = rs.GetAlphanumericRevisionSettings()
                    for a in settings.GetSequence():
                        char_seq.append(settings.Prefix + a + settings.Suffix)

                # Grab the correct revision value or blank if out of sequence
                rev_labels.append(char_seq[idx] if idx < len(char_seq) else "")
                seq_counters[rs.Name] = idx + 1  # increment counter

            # Join multiple revisions with pipe |
            rev_values.append("|".join(rev_labels))


        rowsOut.append(sep.join([doc_no, doc_name] + rev_values))

    return rowsOut
# -------------------------
# WPF window with checkboxes
# -------------------------
class RevisionPreviewWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name, protocols, preview_count=100):
        forms.WPFWindow.__init__(self, xaml_file_name)
        self.protocols = protocols
        self.preview_count = preview_count
        self.selected_template = None
        self.docs = get_documents_list()
        self.current_doc_obj = self.docs[0]

        # Link Buttons
        self.documents_combo = self.FindName("DocumentsCombo")
        self.naming_combo = self.FindName("NamingProtocolCombo")
        self.grid = self.FindName("PreviewDataGrid")
        self.export_btn = self.FindName("ExportButton")
        self.naming_format_text = self.FindName("NamingFormatText")
        self.split_pc_checkbox = self.FindName("SplitPCCheckBox")
        self.hide_no_revisions_checkbox = self.FindName("HideNoRevisionsCheckBox")
        self.hide_unused_revisions_checkbox = self.FindName("HideUnusedRevisionsCheckBox")
        self.ga_override_checkbox = self.FindName("GAOverrideCheckBox")
        self.hide_illegible_dates_checkbox = self.FindName("HideIllegibleDatesCheckBox")

        # Default values
        self.hide_illegible_dates_checkbox.IsChecked = False
        self.ga_override_checkbox.IsChecked = False
        self.hide_unused_revisions_checkbox.IsChecked = True
        self.split_pc_checkbox.IsChecked = True
        self.hide_no_revisions_checkbox.IsChecked = True

        # Populate document combo
        for d in self.docs:
            self.documents_combo.Items.Add(d.Name)
        self.documents_combo.SelectedIndex = 0
        self.documents_combo.SelectionChanged += self.on_document_changed

        # Populate naming protocols combo
        for p in self.protocols:
            self.naming_combo.Items.Add(p.name)
        self.naming_combo.SelectionChanged += self.on_protocol_changed

        # Checkboxes events
        self.hide_illegible_dates_checkbox.Checked += self.on_filter_changed
        self.hide_illegible_dates_checkbox.Unchecked += self.on_filter_changed
        self.split_pc_checkbox.Checked += self.on_filter_changed
        self.split_pc_checkbox.Unchecked += self.on_filter_changed
        self.hide_no_revisions_checkbox.Checked += self.on_filter_changed
        self.hide_no_revisions_checkbox.Unchecked += self.on_filter_changed
        self.hide_unused_revisions_checkbox.Checked += self.on_filter_changed
        self.hide_unused_revisions_checkbox.Unchecked += self.on_filter_changed
        self.ga_override_checkbox.Checked += self.on_filter_changed
        self.ga_override_checkbox.Unchecked += self.on_filter_changed

        # Apply default naming format
        self._apply_projectinfo_naming_format_default()
        self.export_btn.Click += self.on_export

    def _apply_projectinfo_naming_format_default(self):
        pi = self.current_doc_obj.DocRef.ProjectInformation if self.current_doc_obj else None
        param = pi.LookupParameter("Naming Format") if pi else None
        param_value = param.AsString() if param else None

        selected_idx = next((i for i, nf in enumerate(self.protocols) if nf.name == param_value), 0)
        self.naming_combo.SelectedIndex = selected_idx
        self.update_preview(self.protocols[selected_idx], self.current_doc_obj, self.split_pc_checkbox.IsChecked)

    def on_document_changed(self, sender, e):
        idx = self.documents_combo.SelectedIndex
        self.current_doc_obj = self.docs[idx]
        self.update_preview(self.protocols[self.naming_combo.SelectedIndex], self.current_doc_obj, self.split_pc_checkbox.IsChecked)

    def on_protocol_changed(self, sender, e):
        idx = self.naming_combo.SelectedIndex
        self.update_preview(self.protocols[idx], self.current_doc_obj, self.split_pc_checkbox.IsChecked)

    def on_filter_changed(self, sender, e):
        idx = self.naming_combo.SelectedIndex
        self.update_preview(self.protocols[idx], self.current_doc_obj, self.split_pc_checkbox.IsChecked)

    def on_export(self, sender, e):
        idx = self.naming_combo.SelectedIndex
        if idx < 0:
            return
        self.selected_template = self.protocols[idx].template
        self.Close()

    def update_preview(self, protocol, doc_obj, split_p_c=False):
        show_illegible = not self.hide_illegible_dates_checkbox.IsChecked

        rows = build_rows_out(
            protocol.template,
            doc_obj,
            split_p_c=split_p_c,
            hide_unused_revisions=self.hide_unused_revisions_checkbox.IsChecked,
            ga_override=self.ga_override_checkbox.IsChecked,
            show_illegible_dates=show_illegible
        )

        # Hide sheets with no revisions (row-level filter)
        if self.hide_no_revisions_checkbox.IsChecked and rows:
            filtered = [rows[0]]  # keep header
            for r in rows[1:]:
                if any(c.strip() for c in r.split("\t")[2:]):
                    filtered.append(r)
            rows = filtered

        if not rows:
            self.grid.ItemsSource = None
            self.grid.Columns.Clear()
            return

        header_row = rows[0].split("\t")
        preview_rows = [r.split("\t") for r in rows[1:1+self.preview_count]]

        # Build DataGrid columns
        self.grid.Columns.Clear()
        for i, h in enumerate(header_row):
            col = DataGridTextColumn()
            col.Header = h
            col.Binding = Binding("Col{}".format(i))
            col.Width = DataGridLength.Auto
            col.IsReadOnly = True
            self.grid.Columns.Add(col)

        # Build DataGrid items
        data = ObservableCollection[object]()
        for prow in preview_rows:
            obj = ExpandoObject()
            for i, v in enumerate(prow):
                setattr(obj, "Col{}".format(i), v or "")
            data.Add(obj)

        self.grid.ItemsSource = data
        self.grid.UpdateLayout()

        # Update naming format text display
        marker = "{sheet_param:Sheet Number}"
        idx = protocol.template.find(marker)
        trimmed = protocol.template[:idx + len(marker)] if idx >= 0 else protocol.template
        self.naming_format_text.Text = trimmed
        
# -------------------------
# Run window
# -------------------------
protocols = []
protocols.extend(extract_naming_formats_from_print_sheets())
protocols.extend(get_user_naming_formats_from_pyrevit_config())

xaml_file = script.get_bundle_file('PreviewWindow.xaml')
window = RevisionPreviewWindow(xaml_file, protocols)
window.ShowDialog()

if not window.selected_template:
    script.exit()

rowsOut = build_rows_out(
    window.selected_template,
    window.current_doc_obj,
    split_p_c=window.split_pc_checkbox.IsChecked,
    hide_unused_revisions=window.hide_unused_revisions_checkbox.IsChecked,
    ga_override=window.ga_override_checkbox.IsChecked
)

# Apply hide no revisions filter to exported clipboard
if window.hide_no_revisions_checkbox.IsChecked:
    header = rowsOut[0].split("\t")
    filtered_rows = [rowsOut[0]]  # keep header
    for row in rowsOut[1:]:
        if any(cell.strip() for cell in row.split("\t")[2:]):
            filtered_rows.append(row)
    rowsOut = filtered_rows

Clipboard.SetText("\n".join(rowsOut))
forms.alert("Preview copied to clipboard.")
