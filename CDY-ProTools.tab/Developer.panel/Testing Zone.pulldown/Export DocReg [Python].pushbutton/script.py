import sys
import os
import tempfile
import datetime
import re

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

def get_default_naming_formats():
    return [
        NamingFormat(
            name='Craddys: BS EN ISO 19650-2-2018 (+A1 2021)',
            template='{proj_number}-{sheet_param:Originator}-{sheet_param:Functional Breakdown}-{sheet_param:Spatial Breakdown}-{sheet_param:Form}-{sheet_param:Discipline}-{sheet_param:Sheet Number}-{rev_number}-{sheet_param:Sheet Name}{sheet_param:Drawing Title 2}{sheet_param:Drawing Title 3}.pdf'
        ),
        NamingFormat(
            name='Craddys: BS EN ISO 19650-2-2018',
            template='{proj_number}-{sheet_param:Originator}-{sheet_param:Volume or System}-{sheet_param:Levels and Location}-{sheet_param:Type}-{sheet_param:Role}-{sheet_param:Sheet Number}-{rev_number}-{sheet_param:Sheet Name}{sheet_param:Drawing Title 2}{sheet_param:Drawing Title 3}.pdf'
        ),
        NamingFormat(
            name='Aldi: BS1192:2007+A2:2016 (Old Template)',
            template='{proj_number}-{sheet_param:PM.Sheet.Title.Creator.Originator}-{sheet_param:PM.Sheet.Title.View.Zone}-{sheet_param:PM.Sheet.Title.View.Level}-{sheet_param:PM.Sheet.Title.View.Type}-{sheet_param:PM.Sheet.Title.Creator.Role}-{sheet_param:Sheet Number}-{rev_number}-{sheet_param:Sheet Name}{sheet_param:Drawing Title 2}{sheet_param:Drawing Title 3}.pdf'
        ),
        NamingFormat(
            name='Aldi: BS1192:2007+A2:2016 (New Template)',
            template='{proj_param:PM.Sheet.Title.Number.Project}-{sheet_param:PM.Sheet.Title.Creator.Originator}-{sheet_param:PM.Sheet.Title.View.Zone}-{sheet_param:PM.Sheet.Title.View.Level}-{sheet_param:PM.Sheet.Title.View.Type}-{sheet_param:PM.Sheet.Title.Creator.Role}-{sheet_param:Sheet Number}-{rev_number}-{sheet_param:Sheet Name}{sheet_param:Drawing Title 2}{sheet_param:Drawing Title 3}.pdf'
        ),
        NamingFormat(
            name='Morgan Sindall: BS EN ISO 19650-2-2018 (+A1 2021)',
            template='{proj_number}-{sheet_param:Originator}-{sheet_param:Functional Breakdown}-{sheet_param:Spatial Breakdown}-{sheet_param:Form}-{sheet_param:Discipline}-{sheet_param:Sheet Number}_{sheet_param:Sheet Name}{sheet_param:Drawing Title 2}{sheet_param:Drawing Title 3}_{rev_number}.pdf'
        ),
        NamingFormat(
            name='Superseded Naming Protocol',
            template='{proj_number}-{sheet_param:Sheet Number}-{rev_number}-{sheet_param:Sheet Name}{sheet_param:Drawing Title 2}{sheet_param:Drawing Title 3}.pdf'
        ),
    ]

# -------------------------
# Document class for combo
# -------------------------
class AvailableDoc(object):
    def __init__(self, name, hash_val, linked, doc_ref):
        self.Name = name
        self.Hash = hash_val
        self.Linked = linked
        self.DocRef = doc_ref  # store actual DB.Document

def get_documents_list():
    docs = [AvailableDoc(name=doc.Title, hash_val=doc.GetHashCode(), linked=False, doc_ref=doc)]
    linked_docs = DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkInstance).ToElements()
    for ld in linked_docs:
        link_doc = ld.GetLinkDocument()
        if link_doc:
            docs.append(AvailableDoc(name=link_doc.Title, hash_val=link_doc.GetHashCode(), linked=True, doc_ref=link_doc))
    return docs

# -------------------------
# Collect sheets and revisions (host or linked)
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

    sheets, revs, revSeqs = collect_sheets_and_revisions(doc_obj)
    if not sheets:
        return []

    DeDupDates = []
    for r in revs:
        if r is None: continue
        if r.RevisionDate not in DeDupDates:
            DeDupDates.append(r.RevisionDate)

    revSeqNames, revCharSeqs = [], []
    for r in revs:
        if r is None: continue
        rsId = r.RevisionNumberingSequenceId
        rs = doc_obj.DocRef.GetElement(rsId)
        if rs is None: continue
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

    header = ["Document No.", "Document Name"] + [str(d) for d in DeDupDates]
    rowsOut.append(sep.join(header))

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
        if s is None: continue

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

        sheetRevIds = list(s.GetAllRevisionIds()) if s else []
        rev_values = []
        trackRevs = []
        for r in revs:
            if r is None:
                rev_values.append("")
                continue
            rs = doc_obj.DocRef.GetElement(r.RevisionNumberingSequenceId)
            if rs is None:
                rev_values.append("")
                continue
            manual_override = is_manual_override_sequence(r, rs)
            if manual_override:
                rev_values.append("")
            elif r.Id in sheetRevIds:
                i_sq = revSeqNames.index(rs.Name)
                i_ch = trackRevs.count(rs.Name)
                trackRevs.append(rs.Name)
                rev_values.append(revCharSeqs[i_sq][i_ch])
            else:
                rev_values.append("")

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

        for d in self.docs:
            self.documents_combo.Items.Add(d.Name)
        self.documents_combo.SelectedIndex = 0
        self.documents_combo.SelectionChanged += self.on_document_changed

        for p in self.protocols:
            self.naming_combo.Items.Add(p.name)
        self.naming_combo.SelectedIndex = 0
        self.naming_combo.SelectionChanged += self.on_protocol_changed

        self.export_btn.Click += self.on_export
        self.update_preview(self.protocols[0], self.current_doc_obj)

    def on_document_changed(self, sender, e):
        idx = self.documents_combo.SelectedIndex
        self.current_doc_obj = self.docs[idx]
        self.update_preview(self.protocols[self.naming_combo.SelectedIndex], self.current_doc_obj)

    def on_protocol_changed(self, sender, e):
        idx = self.naming_combo.SelectedIndex
        self.update_preview(self.protocols[idx], self.current_doc_obj)

    def update_preview(self, protocol, doc_obj):
        from System.Windows.Data import Binding
        from System.Windows.Controls import DataGridTextColumn, DataGridLength
        from System.Collections.ObjectModel import ObservableCollection
        from System.Dynamic import ExpandoObject

        rows = build_rows_out(protocol.template, doc_obj)
        if not rows:
            self.grid.ItemsSource = None
            self.grid.Columns.Clear()
            return

        header_row = rows[0].split("\t")
        preview_rows = [r.split("\t") for r in rows[1:1+self.preview_count]]

        self.grid.Columns.Clear()
        for idx, head in enumerate(header_row):
            col = DataGridTextColumn()
            col.Header = head
            col.Binding = Binding("Col{0}".format(idx))
            col.Width = DataGridLength.Auto
            self.grid.Columns.Add(col)

        data = ObservableCollection[object]()
        for prow in preview_rows:
            obj = ExpandoObject()
            for i, v in enumerate(prow):
                setattr(obj, "Col{0}".format(i), v or "")
            data.Add(obj)
        self.grid.ItemsSource = data
        self.grid.UpdateLayout()

    def on_export(self, sender, e):
        idx = self.naming_combo.SelectedIndex
        self.selected_template = self.protocols[idx].template
        self.Close()

# -------------------------
# Run window
# -------------------------
protocols = get_default_naming_formats()
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
