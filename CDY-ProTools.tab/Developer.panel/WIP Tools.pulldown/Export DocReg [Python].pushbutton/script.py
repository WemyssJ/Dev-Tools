import clr
import sys
import os
import tempfile
import datetime

# Revit API
clr.AddReference("RevitServices")
from RevitServices.Persistence import DocumentManager 

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *

# WPF
clr.AddReference('PresentationFramework')
clr.AddReference('PresentationCore')
clr.AddReference('WindowsBase')

from System.Windows.Markup import XamlReader
from System.IO import FileStream, FileMode, FileAccess
from System.Windows.Data import Binding
from System.Windows.Controls import DataGridTextColumn, DataGridLength
from System.Collections.ObjectModel import ObservableCollection
from System.Dynamic import ExpandoObject

clr.AddReference("System.Windows.Forms")
from System.Windows.Forms import Clipboard
from System.Windows import MessageBox
from System.Diagnostics import Process

# -------------------------
# Document acquisition
# -------------------------
try:
    doc = __revit__.ActiveUIDocument.Document
except Exception:
    MessageBox.Show("No active Revit document found. Open a project before running this script.", "Error")
    sys.exit()

proj_info = doc.ProjectInformation
project_number = ""
if proj_info:
    pn_param = proj_info.get_Parameter(BuiltInParameter.PROJECT_NUMBER)
    if pn_param:
        project_number = pn_param.AsString() or ""

# -------------------------
# Helper functions
# -------------------------
def _safe_lookup_param_as_string(elem, param_name):
    if elem is None:
        return None
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

def generate_craddys_filename(sheet):
    if sheet is None:
        return ""
    parts = [project_number]
    for p in ("Originator", "Functional Breakdown", "Spatial Breakdown", "Form", "Discipline", "Sheet Number"):
        val = _safe_lookup_param_as_string(sheet, p)
        parts.append(val)
    return "-".join(parts)

# -------------------------
# Collect sheets
# -------------------------
sheets = FilteredElementCollector(doc)\
    .OfCategory(BuiltInCategory.OST_Sheets)\
    .WhereElementIsNotElementType()\
    .ToElements()

if not sheets:
    MessageBox.Show("No sheets found in this document.", "Error")
    sys.exit()

# -------------------------
# Revisions setup
# -------------------------
revSeqs = FilteredElementCollector(doc).OfClass(RevisionNumberingSequence).ToElements()
revIds = Revision.GetAllRevisionIds(doc)
revs = [doc.GetElement(i) for i in revIds if i is not None]

AllDates, DeDupDates = [], []
for r in revs:
    if r is None: continue
    AllDates.append(r.RevisionDate)
    if r.RevisionDate not in DeDupDates:
        DeDupDates.append(r.RevisionDate)

NonUniqueDates = []
for i in range(1, len(revs)):
    if revs[i].RevisionDate == revs[i-1].RevisionDate:
        if revs[i].RevisionDate not in NonUniqueDates:
            NonUniqueDates.append(revs[i].RevisionDate)

revSeqNames, revCharSeqs = [], []
for r in revs:
    if r is None: continue
    rsId = r.RevisionNumberingSequenceId
    rs = doc.GetElement(rsId)
    if rs is None: continue
    revSeqNames.append(rs.Name)
    charSequence = []
    if rs.NumberType == RevisionNumberType.Numeric:
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

# -------------------------
# Build rowsOut
# -------------------------
def build_rows_out(param_choice):
    sep = "\t"
    rowsOut = []

    for s in sheets:
        if s is None: continue
        trackRevs = []
        sheetRevs = list(s.GetAllRevisionIds()) if s else []

        if param_choice == "Craddys Parameters":
            rowOut = generate_craddys_filename(s) + sep + s.Name + sep
        else:
            rowOut = s.SheetNumber + sep + s.Name + sep

        latestRevChar = ""
        for i in revIds:
            if i is None: continue
            DupeDateCounter = 0
            r = doc.GetElement(i)
            if r is None: continue
            rs = doc.GetElement(r.RevisionNumberingSequenceId)
            if rs is None: continue
            rsn, SeqNo, SeqDate = rs.Name, r.SequenceNumber, r.RevisionDate
            manual_override = is_manual_override_sequence(r, rs)

            if manual_override:
                d = sep if latestRevChar else "" + sep
            else:
                if i in sheetRevs:
                    i_sq = revSeqNames.index(rsn)
                    i_ch = trackRevs.count(rsn)
                    trackRevs.append(rsn)
                    base_char = revCharSeqs[i_sq][i_ch]
                    d = base_char + sep
                    latestRevChar = base_char
                else:
                    d = "" + sep

            if d != "":
                rowOut += d
        rowsOut.append(rowOut)

    header = "Document No." + sep + "Document Name" + sep + sep.join([str(d) for d in DeDupDates]) + sep
    rowsOut.insert(0, header)
    return rowsOut

# -------------------------
# Load external XAML
# -------------------------
xaml_path = os.path.join(os.path.dirname(__file__), "PreviewWindow.xaml")
with FileStream(xaml_path, FileMode.Open, FileAccess.Read) as fs:
    window = XamlReader.Load(fs)

# -------------------------
# WPF window class
# -------------------------
class NamingPreviewWindow(object):
    def __init__(self, window, protocols, preview_count=12):
        self.window = window
        self.combo = self.window.FindName("NamingProtocolCombo")
        self.grid = self.window.FindName("PreviewDataGrid")
        self.ok_btn = self.window.FindName("OkButton")
        self.cancel_btn = self.window.FindName("CancelButton")
        self.protocols = protocols
        self.preview_count = preview_count
        self.selected_protocol = None

        for p in protocols:
            self.combo.Items.Add(p)
        self.combo.SelectedIndex = 0
        self.combo.SelectionChanged += self.on_combo_changed
        self.ok_btn.Click += self.on_ok
        self.cancel_btn.Click += self.on_cancel
        self.update_preview(self.combo.SelectedItem)

    def show_dialog(self):
        self.window.ShowDialog()
        return self.selected_protocol

    def on_combo_changed(self, sender, e):
        self.update_preview(self.combo.SelectedItem)

    def update_preview(self, protocol):
        full = build_rows_out(protocol)
        if not full:
            self.grid.ItemsSource = None
            self.grid.Columns.Clear()
            return

        header_row = full[0].split("\t")
        preview_rows = [r.split("\t") for r in full[1:1+self.preview_count]]

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

    def on_ok(self, sender, e):
        self.selected_protocol = self.combo.SelectedItem
        self.window.Close()

    def on_cancel(self, sender, e):
        self.selected_protocol = None
        self.window.Close()

# -------------------------
# Show dialog
# -------------------------
protocols = ['Aldi Parameters', 'Craddys Parameters']
wnd = NamingPreviewWindow(window, protocols)
param_choice = wnd.show_dialog()
if not param_choice:
    sys.exit()

# -------------------------
# Export TSV & clipboard
# -------------------------
rowsOut = build_rows_out(param_choice)

try:
    Clipboard.SetText("\n".join(rowsOut))
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
        Process.Start(out_path)
    except:
        pass
    MessageBox.Show("Revision table copied to clipboard and exported to:\n{0}".format(out_path), "Success")
except Exception as ex:
    MessageBox.Show("Revision table copied to clipboard. Failed to write/open TSV file: {0}".format(str(ex)), "Export")
