# -------------------------
# Imports
# -------------------------
import clr
import sys

clr.AddReference("RevitServices")
from RevitServices.Persistence import DocumentManager 

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *

from pyrevit import forms
clr.AddReference("System.Windows.Forms")
from System.Windows.Forms import Clipboard

# -------------------------
# Document
# -------------------------
doc = DocumentManager.Instance.CurrentDBDocument
if doc is None:
    forms.alert("No active Revit document found. Please open a project before running this script.", title="Error")
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
            v = p.AsString()
            if v:
                return v
    except Exception:
        pass
    return None

def _gather_text_candidates_from_element(elem):
    if elem is None:
        return []
    candidates = []
    for attr in ("Name", "SequenceName", "Description"):
        try:
            val = getattr(elem, attr, None)
            if val:
                candidates.append(str(val))
        except Exception:
            pass
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
        try:
            if t and needle in t.upper():
                return True
        except Exception:
            pass
    return False

def generate_craddys_filename(sheet):
    if sheet is None:
        return ""
    parts = [project_number]  # Prepend project number
    for p in ("Originator", "Functional Breakdown", "Spatial Breakdown", "Form", "Discipline", "Sheet Number"):
        val = _safe_lookup_param_as_string(sheet, p) or ""
        parts.append(val)
    return "-".join(parts)

# -------------------------
# Collect sheets (keep Revit order)
# -------------------------
sheets = FilteredElementCollector(doc)\
    .OfCategory(BuiltInCategory.OST_Sheets)\
    .WhereElementIsNotElementType()\
    .ToElements()

if not sheets:
    forms.alert("No sheets found in this document.", title="Error")
    sys.exit()

# -------------------------
# Revisions setup
# -------------------------
revSeqs = FilteredElementCollector(doc).OfClass(RevisionNumberingSequence).ToElements()
revIds  = Revision.GetAllRevisionIds(doc)
revs    = [doc.GetElement(i) for i in revIds if i is not None]

AllDates, DeDupDates = [], []
for r in revs:
    if r is None: continue
    AllDates.append(r.RevisionDate)
    if r.RevisionDate not in DeDupDates:
        DeDupDates.append(r.RevisionDate)

NonUniqueDates = []
indexx = 0
for r in revs:
    if indexx == 0:
        indexx += 1
        continue
    if r.RevisionDate == revs[indexx -1].RevisionDate:
        if r.RevisionDate not in NonUniqueDates:
            NonUniqueDates.append(r.RevisionDate)
    indexx += 1

revSeqNames, revCharSeqs = [],[]
for r in revs:
    if r is None: continue
    rsId = r.RevisionNumberingSequenceId
    rs   = doc.GetElement(rsId)
    if rs is None: continue
    revSeqNames.append(rs.Name)
    charSequence = []
    if rs.NumberType == RevisionNumberType.Numeric:
        settings  = rs.GetNumericRevisionSettings()
        minDigits = settings.MinimumDigits
        prefix    = settings.Prefix
        suffix    = settings.Suffix
        for n in range(settings.StartNumber, 99):
            char_str = str(n)
            pad_str  = char_str.rjust(minDigits, "0")
            charSequence.append(prefix + pad_str + suffix)
    else:
        settings = rs.GetAlphanumericRevisionSettings()
        prefix    = settings.Prefix
        suffix    = settings.Suffix
        for a in settings.GetSequence():
            charSequence.append(prefix + a + suffix)
    revCharSeqs.append(charSequence)

# -------------------------
# Parameter set choice
# -------------------------
param_choice = forms.SelectFromList.show(
    ['Aldi Parameters', 'Craddys Parameters'],
    title='Select Parameter Set',
    multiselect=False
)
if not param_choice:
    forms.alert("No parameter set selected. Exiting.", title="Cancelled")
    sys.exit()

# -------------------------
# Build revision table
# -------------------------
rowsOut = []
sep = "\t"

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
        d = ""
        r    = doc.GetElement(i)
        if r is None: continue
        rsId = r.RevisionNumberingSequenceId
        rs   = doc.GetElement(rsId)
        if rs is None: continue
        rsn  = rs.Name
        SeqNo = r.SequenceNumber
        SeqDate = r.RevisionDate

        manual_override = is_manual_override_sequence(r, rs)

        if manual_override:
            d = sep if latestRevChar else "" + sep
        else:
            if i in sheetRevs:
                i_sq = revSeqNames.index(rsn)
                i_ch = trackRevs.count(rsn)
                trackRevs.append(rsn)
                base_char = revCharSeqs[i_sq][i_ch]

                if SeqDate in NonUniqueDates:
                    ArtificialLocation = DeDupDates.index(SeqDate) + 1
                    LastDupDateLocation = len(AllDates) - AllDates[::-1].index(SeqDate)
                    if ArtificialLocation == SeqNo - DupeDateCounter:
                        d = base_char
                        DupeDateCounter += 1
                    else:
                        d += ""
                    if LastDupDateLocation == SeqNo - DupeDateCounter:
                        d = base_char + sep
                        DupeDateCounter += 1
                    else:
                        d = base_char
                        DupeDateCounter += 1
                else:
                    d = base_char + sep
                latestRevChar = base_char
            else:
                if SeqDate in NonUniqueDates:
                    ArtificialLocation = DeDupDates.index(SeqDate) + 1
                    LastDupDateLocation = len(AllDates) - AllDates[::-1].index(SeqDate)
                    if ArtificialLocation == SeqNo - DupeDateCounter:
                        d = ""
                        DupeDateCounter += 1
                    else:
                        d = ""
                    if LastDupDateLocation == SeqNo - DupeDateCounter:
                        d = "" + sep
                        DupeDateCounter += 1
                    else:
                        d = ""
                        DupeDateCounter += 1
                else:
                    d = "" + sep

        if d != "":
            rowOut += d

    rowsOut.append(rowOut)

# -------------------------
# Header
# -------------------------
header = "Document No." + sep + "Document Name" + sep + sep.join([str(d) for d in DeDupDates]) + sep
rowsOut.insert(0, header)

# -------------------------
# Copy to clipboard
# -------------------------
clipboard_text = "\n".join(rowsOut)
Clipboard.SetText(clipboard_text)
forms.alert("Revision table copied to clipboard!", title="Success")
