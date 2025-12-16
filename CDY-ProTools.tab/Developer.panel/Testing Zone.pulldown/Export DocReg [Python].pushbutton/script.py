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

    config_path = os.path.join(
        os.environ.get("APPDATA", ""),
        "pyRevit",
        "pyRevit_config.ini"
    )

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
            user_formats.append(
                NamingFormat(
                    name="{}".format(name),
                    template=template,
                    builtin=False
                )
            )

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

    #logger.info(
    #    "Imported {} naming formats from Print Sheets ({})".format(len(extracted), os.path.basename(tab_root))
    #)
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
def build_rows_out(template, doc_obj):
    sep = "\t"
    rowsOut = []

    def remove_non_ascii(s):
        if not s:
            return ""
        return s.encode('ascii', errors='ignore').decode('ascii')

    sheets, revs, revSeqs = collect_sheets_and_revisions(doc_obj)
    if not sheets:
        return []

    # Collect unique revision dates for header
    DeDupDates = []
    for r in revs:
        if r is None:
            continue
        if r.RevisionDate not in DeDupDates:
            DeDupDates.append(r.RevisionDate)

    # Build sequence names and their character sequences
    revSeqNames, revCharSeqs = [], []
    for r in revs:
        if r is None:
            continue
        rsId = r.RevisionNumberingSequenceId
        rs = doc_obj.DocRef.GetElement(rsId)
        if rs is None or rs.Name in revSeqNames:
            continue

        revSeqNames.append(rs.Name)
        charSequence = []
        if rs.NumberType == DB.RevisionNumberType.Numeric:
            settings = rs.GetNumericRevisionSettings()
            minDigits, prefix, suffix = settings.MinimumDigits, settings.Prefix, settings.Suffix
            for n in range(settings.StartNumber, 99):
                charSequence.append(prefix + str(n).rjust(minDigits, "0") + suffix)
        else:
            settings = rs.GetAlphanumericRevisionSettings()
            prefix, suffix = settings.Prefix, settings.Suffix
            for a in settings.GetSequence():
                charSequence.append(prefix + a + suffix)
        revCharSeqs.append(charSequence)

    # Build header row
    header = ["Document No.", "Document Name"] + [str(d) for d in DeDupDates]
    header = [remove_non_ascii(h) for h in header]
    rowsOut.append(sep.join(header))

    # Split template into doc no. and doc name parts
    if "{sheet_param:Sheet Name}" in template:
        split_idx = template.index("{sheet_param:Sheet Name}")
        doc_no_template = template[:split_idx]
        doc_name_template = template[split_idx:]
    else:
        doc_no_template = template
        doc_name_template = ""

    def safe_sheet_number(s):
        try:
            return s.SheetNumber
        except:
            return ""

    sorted_sheets = sorted(sheets, key=safe_sheet_number)

    for s in sorted_sheets:
        if s is None:
            continue

        # Build document number
        doc_no = doc_no_template.replace("{proj_number}", project_number)
        for match in re.findall(r"{sheet_param:([^}]+)}", doc_no):
            val = _safe_lookup_param_as_string(s, match)
            doc_no = doc_no.replace("{sheet_param:%s}" % match, val)
        for match in re.findall(r"{proj_param:([^}]+)}", doc_no):
            val = _safe_lookup_param_as_string(proj_info, match)
            doc_no = doc_no.replace("{proj_param:%s}" % match, val)
        doc_no = re.sub(r"[-_]*\{rev_number\}", "", doc_no)
        doc_no = re.sub(r"\.pdf$", "", doc_no, flags=re.IGNORECASE)
        doc_no = doc_no.rstrip("-_ ")
        doc_no = remove_non_ascii(doc_no)

        # Build document name
        doc_name = doc_name_template
        for match in re.findall(r"{sheet_param:([^}]+)}", doc_name):
            val = _safe_lookup_param_as_string(s, match)
            doc_name = doc_name.replace("{sheet_param:%s}" % match, val)
        for match in re.findall(r"{proj_param:([^}]+)}", doc_name):
            val = _safe_lookup_param_as_string(proj_info, match)
            doc_name = doc_name.replace("{proj_param:%s}" % match, val)
        doc_name = re.sub(r"[-_]*\{rev_number\}", "", doc_name)
        doc_name = re.sub(r"\.pdf$", "", doc_name, flags=re.IGNORECASE)
        doc_name = doc_name.rstrip("-_ ")
        doc_name = remove_non_ascii(doc_name)

        # Build revision values aligned by date
        sheetRevIds = set(s.GetAllRevisionIds()) if s else set()
        rev_values = []

        # Map date to revisions for this sheet
        date_to_revs = {d: [] for d in DeDupDates}
        for r in revs:
            if r is None or r.Id not in sheetRevIds:
                continue
            rs = doc_obj.DocRef.GetElement(r.RevisionNumberingSequenceId)
            if rs is None:
                continue
            if is_manual_override_sequence(r, rs):
                continue
            rev_date = r.RevisionDate
            if rev_date in date_to_revs:
                date_to_revs[rev_date].append(r)

        # Track sequence counts for correct numbering
        seq_counters = {name: 0 for name in revSeqNames}

        for d in DeDupDates:
            revs_on_date = date_to_revs.get(d, [])
            if not revs_on_date:
                rev_values.append("")
                continue

            r = revs_on_date[0]
            rs = doc_obj.DocRef.GetElement(r.RevisionNumberingSequenceId)
            i_sq = revSeqNames.index(rs.Name)
            i_ch = seq_counters[rs.Name]
            rev_value = revCharSeqs[i_sq][i_ch] if i_ch < len(revCharSeqs[i_sq]) else ""
            rev_values.append(remove_non_ascii(rev_value))
            seq_counters[rs.Name] += 1

        # Append row
        rowsOut.append(sep.join([doc_no, doc_name] + rev_values))

    return rowsOut


# -------------------------
# WPF window class
# -------------------------
class RevisionPreviewWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name, protocols, preview_count=100):
        forms.WPFWindow.__init__(self, xaml_file_name)
        self.protocols = protocols
        self.preview_count = preview_count
        self.selected_template = None
        self.docs = get_documents_list()
        self.current_doc_obj = self.docs[0]

        self.documents_combo = self.FindName("DocumentsCombo")
        self.naming_combo = self.FindName("NamingProtocolCombo")
        self.grid = self.FindName("PreviewDataGrid")
        self.export_btn = self.FindName("ExportButton")
        self.naming_format_text = self.FindName("NamingFormatText")  # NEW

        # Populate document combo
        for d in self.docs:
            self.documents_combo.Items.Add(d.Name)
        self.documents_combo.SelectedIndex = 0
        self.documents_combo.SelectionChanged += self.on_document_changed

        # Populate naming protocols combo
        for p in self.protocols:
            self.naming_combo.Items.Add(p.name)
        self.naming_combo.SelectionChanged += self.on_protocol_changed

        # Set default naming format based on Project Information parameter
        self._apply_projectinfo_naming_format_default()

        # Connect export button
        self.export_btn.Click += self.on_export

        self.update_preview(self.protocols[0], self.current_doc_obj)

    def on_document_changed(self, sender, e):
        idx = self.documents_combo.SelectedIndex
        self.current_doc_obj = self.docs[idx]
        self.update_preview(self.protocols[self.naming_combo.SelectedIndex], self.current_doc_obj)

    def on_protocol_changed(self, sender, e):
        idx = self.naming_combo.SelectedIndex
        self.update_preview(self.protocols[idx], self.current_doc_obj)

    def _apply_projectinfo_naming_format_default(self):
        # Get the Project Information element of the current document
        pi = self.current_doc_obj.DocRef.ProjectInformation if self.current_doc_obj else None
        param = pi.LookupParameter("Naming Format") if pi else None
        param_value = param.AsString() if param else None

        # Look for a protocol with a matching name
        selected_idx = next(
            (i for i, nf in enumerate(self.protocols) if nf.name == param_value),
            0  # fallback to index 0 if no match
        )

        # Set the combo selection by index
        self.naming_combo.SelectedIndex = selected_idx

        # Update preview
        self.update_preview(self.protocols[selected_idx], self.current_doc_obj)


    def update_preview(self, protocol, doc_obj):
        from System.Windows.Data import Binding
        from System.Windows.Controls import DataGridTextColumn, DataGridLength
        from System.Collections.ObjectModel import ObservableCollection
        from System.Dynamic import ExpandoObject

        rows = build_rows_out(protocol.template, doc_obj)
        if not rows:
            self.grid.ItemsSource = None
            self.grid.Columns.Clear()
        else:
            header_row = rows[0].split("\t")
            preview_rows = [r.split("\t") for r in rows[1:1+self.preview_count]]

            self.grid.Columns.Clear()
            for idx, head in enumerate(header_row):
                col = DataGridTextColumn()
                col.Header = head
                col.Binding = Binding("Col{0}".format(idx))
                col.Width = DataGridLength.Auto
                col.IsReadOnly = True
                self.grid.Columns.Add(col)

            data = ObservableCollection[object]()
            for prow in preview_rows:
                obj = ExpandoObject()
                for i, v in enumerate(prow):
                    setattr(obj, "Col{0}".format(i), v or "")
                data.Add(obj)
            self.grid.ItemsSource = data
            self.grid.UpdateLayout()

        # -------------------------
        # Trim naming format text up to {sheet_param:Sheet Number}
        # -------------------------
        marker = "{sheet_param:Sheet Number}"  # remove spaces inside braces
        idx = protocol.template.find(marker)
        if idx >= 0:
            trimmed_template = protocol.template[:idx + len(marker)]
        else:
            trimmed_template = protocol.template
        self.naming_format_text.Text = trimmed_template


    def on_export(self, sender, e):
        idx = self.naming_combo.SelectedIndex
        self.selected_template = self.protocols[idx].template
        self.Close()

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

rowsOut = build_rows_out(window.selected_template, window.current_doc_obj)

try:
    script.clipboard_copy("\n".join(rowsOut))
except:
    pass

try:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_dir = tempfile.gettempdir()
    out_name = "revisions_{0}.tsv".format(ts)
    out_path = os.path.join(temp_dir, out_name)
    with open(out_path, "w") as fh:
        for r in rowsOut:
            fh.write(r + "\n")
    try:
        os.startfile(out_path)
    except:
        pass
    forms.alert("Revision table copied to clipboard and exported to:\n{0}".format(out_path), title="Success")
except Exception as ex:
    forms.alert("Revision table copied to clipboard. Failed to write/open TSV file: {0}".format(str(ex)), title="Export")
