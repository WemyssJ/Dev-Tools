# -*- coding: utf-8 -*-
import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')

from Autodesk.Revit.DB import FilteredElementCollector, ViewSheet
import re

# ---------------------------------------------------------------------------
# Environment detection
# ---------------------------------------------------------------------------
try:
    _ = __revit__          # noqa: F821
    uiapp = __revit__      # noqa: F821
    uidoc = uiapp.ActiveUIDocument
    doc   = uidoc.Document
except NameError:
    import RevitServices
    from RevitServices.Persistence import DocumentManager
    doc   = DocumentManager.Instance.CurrentDBDocument
    uiapp = DocumentManager.Instance.CurrentUIApplication
    uidoc = uiapp.ActiveUIDocument

try:
    DIRECTION = -1 if __shiftclick__ else 1    # noqa: F821
except NameError:
    DIRECTION = 1

# ---------------------------------------------------------------------------
# Sheet cache
# ---------------------------------------------------------------------------
_cache = {"sheets": [], "id_to_idx": {}, "count": 0}


def _sheet_sort_key(sheet_number):
    parts = re.split(r'(\d+)', sheet_number.strip())
    return [(0, int(p), '') if p.isdigit() else (1, 0, p.lower()) for p in parts]


def _build_cache(document):
    sheets = [s for s in FilteredElementCollector(document)
                            .OfClass(ViewSheet)
                            .WhereElementIsNotElementType()
              if not s.IsPlaceholder]
    sheets.sort(key=lambda s: _sheet_sort_key(s.SheetNumber))
    _cache["sheets"]    = sheets
    _cache["id_to_idx"] = {s.Id.IntegerValue: i for i, s in enumerate(sheets)}
    _cache["count"]     = len(sheets)


def get_sheets(document):
    current_count = (FilteredElementCollector(document)
                        .OfClass(ViewSheet)
                        .WhereElementIsNotElementType()
                        .GetElementCount())
    if current_count != _cache["count"]:
        _build_cache(document)
    return _cache["sheets"], _cache["id_to_idx"]


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

def get_active_sheet_id(document, ui_document):
    active_view = ui_document.ActiveView
    if isinstance(active_view, ViewSheet):
        return active_view.Id.IntegerValue
    owning_id = getattr(active_view, 'OwnerViewId', None)
    if owning_id and owning_id.IntegerValue != -1:
        candidate = document.GetElement(owning_id)
        if isinstance(candidate, ViewSheet):
            return candidate.Id.IntegerValue
    return None


def navigate_sheet(direction):
    sheets, id_to_idx = get_sheets(doc)
    if not sheets:
        return

    current_id = get_active_sheet_id(doc, uidoc)

    if current_id is None or current_id not in id_to_idx:
        target_idx = 0 if direction == 1 else len(sheets) - 1
    else:
        target_idx = (id_to_idx[current_id] + direction) % len(sheets)

    uidoc.ActiveView = sheets[target_idx]


navigate_sheet(DIRECTION)