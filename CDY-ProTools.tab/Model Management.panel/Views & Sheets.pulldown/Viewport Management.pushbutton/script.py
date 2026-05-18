# -*- coding: utf-8 -*-

from pyrevit import revit, DB, forms
from Autodesk.Revit.DB import *

from System.Windows.Forms import (
    Form, DataGridView, DockStyle, Button, Panel,
    DataGridViewAutoSizeColumnsMode, DataGridViewSelectionMode,
    ComboBox, TextBox, Label, DataGridViewComboBoxColumn,
    DataGridViewTextBoxColumn
)
from System.Drawing import Size, Color, Point
import System.Windows.Forms as WF

doc   = revit.doc
uidoc = revit.uidoc

READONLY_COLOR = Color.FromArgb(220, 220, 220)
CONFLICT_COLOR = Color.LightCoral
CONFLICT_SEL   = Color.IndianRed

COL_ID     = 0
COL_SHEET  = 1
COL_DETAIL = 2
COL_VNAME  = 3
COL_SNAME  = 4
COL_TITLE  = 5


# --------------------------------------------------------
# HELPERS
# --------------------------------------------------------

def get_all_sheets():
    sheets = FilteredElementCollector(doc).OfClass(ViewSheet).ToElements()
    return sorted([(s.SheetNumber, s.Name, s.Id) for s in sheets], key=lambda x: x[0])


def taken_detail_numbers(sheet_id):
    """Return set of detail numbers already on a sheet."""
    used = set()
    for vp in FilteredElementCollector(doc).OfClass(Viewport):
        if vp.SheetId == sheet_id:
            p = vp.get_Parameter(BuiltInParameter.VIEWPORT_DETAIL_NUMBER)
            if p:
                used.add(p.AsString())
    return used


def next_free_detail(wanted, used):
    """Return wanted if free, else append -1, -2 … until free."""
    if wanted not in used:
        return wanted
    i = 1
    while "{}-{}".format(wanted, i) in used:
        i += 1
    return "{}-{}".format(wanted, i)


def get_viewports_from_views(view_ids):
    return [vp for vp in FilteredElementCollector(doc).OfClass(Viewport)
            if vp.ViewId in view_ids]


# --------------------------------------------------------
# INPUT DETECTION
# --------------------------------------------------------

selection_ids = list(uidoc.Selection.GetElementIds())
viewports, views = [], []

for elid in selection_ids:
    el = doc.GetElement(elid)
    if isinstance(el, Viewport):
        viewports.append(el)
    elif isinstance(el, View) and not el.IsTemplate:
        views.append(el)

if views and not viewports:
    viewports = get_viewports_from_views([v.Id for v in views])

if not viewports:
    forms.alert("Select Viewports or Views.", exitscript=True)

all_sheets           = get_all_sheets()
sheet_names          = ["{} - {}".format(n, nm) for n, nm, _ in all_sheets]
sheet_id_by_name     = {"{} - {}".format(n, nm): sid for n, nm, sid in all_sheets}
sheet_num_by_display = {"{} - {}".format(n, nm): n   for n, nm, _  in all_sheets}


# --------------------------------------------------------
# DATA MODEL
# --------------------------------------------------------

rows = []
for vp in viewports:
    view  = doc.GetElement(vp.ViewId)
    sheet = doc.GetElement(vp.SheetId)

    detail_param = vp.get_Parameter(BuiltInParameter.VIEWPORT_DETAIL_NUMBER)
    title_param  = vp.get_Parameter(BuiltInParameter.VIEW_DESCRIPTION)

    rows.append({
        "vp_id":         vp.Id.IntegerValue,
        "sheet_num":     sheet.SheetNumber,
        "sheet_display": "{} - {}".format(sheet.SheetNumber, sheet.Name),
        "detail":        detail_param.AsString() if detail_param else "",
        "detail_ro":     detail_param.IsReadOnly  if detail_param else True,
        "view_name":     view.Name,
        "title":         title_param.AsString() if title_param else "",
        "title_ro":      title_param.IsReadOnly  if title_param else True,
    })


# --------------------------------------------------------
# UI
# --------------------------------------------------------

class BatchEditor(Form):

    def __init__(self, data):
        self.data = data
        self.Text = "Viewport / View Batch Editor"
        self.Size = Size(1300, 750)

        # ---- Grid ----
        self.grid = DataGridView()
        self.grid.Dock                  = DockStyle.Fill
        self.grid.AutoSizeColumnsMode   = DataGridViewAutoSizeColumnsMode.Fill
        self.grid.SelectionMode         = DataGridViewSelectionMode.CellSelect
        self.grid.MultiSelect           = True
        self.grid.AllowUserToAddRows    = False
        self.grid.AllowUserToDeleteRows = False
        self.grid.ColumnHeaderMouseClick += self.on_column_header_click
        self.grid.CellValueChanged       += self.on_sheet_name_changed

        # Columns
        for name, visible, readonly, combo_items in [
            ("ID",             False, True,  None),
            ("Sheet",          True,  True,  None),
            ("Detail Number",  True,  False, None),
            ("View Name",      True,  False, None),
            ("Sheet Name",     True,  False, sheet_names),
            ("Title on Sheet", True,  False, None),
        ]:
            if combo_items is not None:
                col = DataGridViewComboBoxColumn()
                col.FlatStyle = WF.FlatStyle.Flat
                for item in combo_items:
                    col.Items.Add(item)
            else:
                col = DataGridViewTextBoxColumn()
                col.ReadOnly = readonly

            col.Name    = name
            col.Visible = visible
            self.grid.Columns.Add(col)

        # Populate
        for item in data:
            r   = self.grid.Rows.Add()
            row = self.grid.Rows[r]

            row.Cells[COL_ID].Value     = item["vp_id"]
            row.Cells[COL_SHEET].Value  = item["sheet_num"]
            row.Cells[COL_DETAIL].Value = item["detail"]
            row.Cells[COL_VNAME].Value  = item["view_name"]
            row.Cells[COL_SNAME].Value  = item["sheet_display"]
            row.Cells[COL_TITLE].Value  = item["title"]

            self._grey(row.Cells[COL_SHEET])

            if item["detail_ro"]:
                self._grey(row.Cells[COL_DETAIL], lock=True)

            if item["title_ro"]:
                self._grey(row.Cells[COL_TITLE], lock=True)

        # ---- Bottom Panel ----
        panel        = Panel()
        panel.Dock   = DockStyle.Bottom
        panel.Height = 180

        def btn(text, x, w, handler):
            b          = Button()
            b.Text     = text
            b.Location = Point(x, 10)
            b.Width    = w
            b.Click   += handler
            return b

        divider           = Label()
        divider.AutoSize  = False
        divider.Location  = Point(10, 50)
        divider.Width     = 1250
        divider.Height    = 1
        divider.BackColor = Color.LightGray

        y = 85

        self.find_box    = TextBox(); self.find_box.Location    = Point(55,  y-3); self.find_box.Width    = 160
        self.replace_box = TextBox(); self.replace_box.Location = Point(295, y-3); self.replace_box.Width = 160

        self.scope_box               = ComboBox()
        self.scope_box.Location      = Point(470, y-3)
        self.scope_box.Width         = 160
        self.scope_box.DropDownStyle = WF.ComboBoxStyle.DropDownList
        for s in ("All", "Selected Rows", "Selected Cells"):
            self.scope_box.Items.Add(s)
        self.scope_box.SelectedIndex = 0

        find_lbl = Label()
        find_lbl.Text = "Find:"
        find_lbl.Location = Point(10, y)
        find_lbl.BackColor = panel.BackColor
        find_lbl.AutoSize = True

        replace_lbl = Label()
        replace_lbl.Text = "Replace:"
        replace_lbl.Location = Point(230, y)
        replace_lbl.BackColor = panel.BackColor
        replace_lbl.AutoSize = True
        
        rep_btn          = Button()
        rep_btn.Text     = "Replace"
        rep_btn.Location = Point(640, y-5)
        rep_btn.Width    = 120
        rep_btn.Click   += self.find_replace

        for ctrl in (
            btn("Apply",         10,  120, self.apply_changes),
            btn("Clear Titles",  140, 120, self.clear_titles),
            btn("View → Detail", 270, 140, self.sync_view_to_detail),
            btn("Detail → View", 420, 140, self.sync_detail_to_view),
            divider,
            find_lbl, self.find_box, replace_lbl, self.replace_box,
            self.scope_box, rep_btn,
        ):
            panel.Controls.Add(ctrl)

        self.Controls.Add(self.grid)
        self.Controls.Add(panel)

    # --------------------------------------------------------
    # STYLE HELPER
    # --------------------------------------------------------

    def _grey(self, cell, lock=False):
        if lock:
            cell.ReadOnly = True
        cell.Style.BackColor          = READONLY_COLOR
        cell.Style.SelectionBackColor = READONLY_COLOR
        cell.Style.ForeColor          = Color.Gray

    # --------------------------------------------------------
    # EVENTS
    # --------------------------------------------------------

    def on_sheet_name_changed(self, sender, e):
        if e.ColumnIndex != COL_SNAME:
            return
        val = self.grid.Rows[e.RowIndex].Cells[COL_SNAME].Value
        if val and val in sheet_num_by_display:
            self.grid.Rows[e.RowIndex].Cells[COL_SHEET].Value = sheet_num_by_display[str(val)]

    def on_column_header_click(self, sender, e):
        self.grid.ClearSelection()
        for r in range(self.grid.Rows.Count):
            self.grid.Rows[r].Cells[e.ColumnIndex].Selected = True

    # --------------------------------------------------------
    # SYNC
    # --------------------------------------------------------

    def sync_view_to_detail(self, sender, args):
        target = self.grid.SelectedRows if self.grid.SelectedRows.Count else self.grid.Rows
        for r in target:
            v = r.Cells[COL_VNAME].Value
            if v and not r.Cells[COL_DETAIL].ReadOnly:
                r.Cells[COL_DETAIL].Value = str(v)

    def sync_detail_to_view(self, sender, args):
        target = self.grid.SelectedRows if self.grid.SelectedRows.Count else self.grid.Rows
        for r in target:
            d = r.Cells[COL_DETAIL].Value
            if d:
                r.Cells[COL_VNAME].Value = str(d)

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    def validate(self):
        seen, conflicts = {}, set()

        for r in range(self.grid.Rows.Count):
            self.grid.Rows[r].DefaultCellStyle.BackColor = Color.White

        for r in range(self.grid.Rows.Count):
            key = (str(self.grid.Rows[r].Cells[COL_SHEET].Value),
                   str(self.grid.Rows[r].Cells[COL_DETAIL].Value))
            if key in seen:
                conflicts.add(r)
                conflicts.add(seen[key])
            else:
                seen[key] = r

        for r in conflicts:
            self.grid.Rows[r].DefaultCellStyle.BackColor          = CONFLICT_COLOR
            self.grid.Rows[r].DefaultCellStyle.SelectionBackColor = CONFLICT_SEL

        return len(conflicts) == 0

    # --------------------------------------------------------
    # APPLY  (3-phase + safe sheet move)
    # --------------------------------------------------------

    def apply_changes(self, sender, args):
        if not self.validate():
            forms.alert("Duplicate detail numbers detected — conflicts highlighted in red.")
            return

        try:
            ops = []
            for r in self.grid.Rows:
                if r.IsNewRow:
                    continue
                vp         = doc.GetElement(ElementId(int(r.Cells[COL_ID].Value)))
                view       = doc.GetElement(vp.ViewId)
                sname_disp = str(r.Cells[COL_SNAME].Value)

                # Capture position and title type BEFORE any transactions alter the vp
                ops.append({
                    "vp":          vp,
                    "view":        view,
                    "detail":      str(r.Cells[COL_DETAIL].Value),
                    "view_name":   str(r.Cells[COL_VNAME].Value),
                    "title":       str(r.Cells[COL_TITLE].Value),
                    "target_sid":  sheet_id_by_name.get(sname_disp),
                    "current_sid": vp.SheetId,
                    "box_centre":  vp.GetBoxCenter(),        # position on sheet
                    "type_id":     vp.GetTypeId(),           # viewport type (label style)
                })

            # Phase 1 – temp detail numbers
            t1 = Transaction(doc, "Temp Detail Numbers")
            t1.Start()
            for o in ops:
                p = o["vp"].get_Parameter(BuiltInParameter.VIEWPORT_DETAIL_NUMBER)
                if p and not p.IsReadOnly:
                    p.Set("__TMP_{}".format(o["vp"].Id.IntegerValue))
            t1.Commit()

            # Phase 2 – temp view names
            t2 = Transaction(doc, "Temp View Names")
            t2.Start()
            for o in ops:
                if o["view"]:
                    o["view"].Name = "__TMP_VIEW_{}".format(o["view"].Id.IntegerValue)
            t2.Commit()

            # Phase 3 – final values + sheet moves
            t3 = Transaction(doc, "Apply Viewport Changes")
            t3.Start()

            # Track detail numbers claimed this batch per target sheet
            batch_used  = {}
            fallbacks   = []   # (wanted, actual) pairs to report after commit

            for o in ops:
                vp   = o["vp"]
                view = o["view"]

                moving = o["target_sid"] and o["target_sid"] != o["current_sid"]

                if moving:
                    target_sid = o["target_sid"]

                    if target_sid not in batch_used:
                        batch_used[target_sid] = taken_detail_numbers(target_sid)

                    wanted = o["detail"]
                    safe   = next_free_detail(wanted, batch_used[target_sid])
                    batch_used[target_sid].add(safe)

                    if safe != wanted:
                        fallbacks.append((wanted, safe))

                    # Delete old, recreate on new sheet at same position
                    doc.Delete(vp.Id)
                    new_sheet = doc.GetElement(target_sid)
                    new_vp    = Viewport.Create(doc, new_sheet.Id, view.Id, o["box_centre"])

                    # Restore viewport type (controls title display style)
                    if o["type_id"] and o["type_id"] != ElementId.InvalidElementId:
                        new_vp.ChangeTypeId(o["type_id"])

                    # Detail number
                    p = new_vp.get_Parameter(BuiltInParameter.VIEWPORT_DETAIL_NUMBER)
                    if p and not p.IsReadOnly:
                        p.Set(safe)

                    # Title on sheet
                    tp = new_vp.get_Parameter(BuiltInParameter.VIEW_DESCRIPTION)
                    if tp and not tp.IsReadOnly:
                        tp.Set(o["title"])

                else:
                    # In-place update
                    p = vp.get_Parameter(BuiltInParameter.VIEWPORT_DETAIL_NUMBER)
                    if p and not p.IsReadOnly:
                        p.Set(o["detail"])

                    tp = vp.get_Parameter(BuiltInParameter.VIEW_DESCRIPTION)
                    if tp and not tp.IsReadOnly:
                        tp.Set(o["title"])

                if view:
                    view.Name = o["view_name"]

            t3.Commit()

            if fallbacks:
                msg = "\n".join(
                    "  '{}' → '{}' (already taken)".format(w, s)
                    for w, s in fallbacks
                )
                forms.alert("Some detail numbers were reassigned:\n\n" + msg)
            else:
                forms.alert("Update complete.")

        except Exception as ex:
            forms.alert(str(ex))

    # --------------------------------------------------------
    # CLEAR TITLES
    # --------------------------------------------------------

    def clear_titles(self, sender, args):
        for r in self.grid.SelectedRows:
            if not r.Cells[COL_TITLE].ReadOnly:
                r.Cells[COL_TITLE].Value = ""

    # --------------------------------------------------------
    # FIND / REPLACE
    # --------------------------------------------------------

    def find_replace(self, sender, args):
        f   = self.find_box.Text
        rep = self.replace_box.Text

        if not f:
            forms.alert("Enter find text.")
            return

        def apply(cell):
            if cell.ReadOnly or cell.Value is None:
                return
            v = str(cell.Value)
            if f in v:
                cell.Value = v.replace(f, rep)

        scope = self.scope_box.SelectedItem
        if scope == "All":
            for r in range(self.grid.Rows.Count):
                for c in range(self.grid.Columns.Count):
                    apply(self.grid.Rows[r].Cells[c])
        elif scope == "Selected Rows":
            for r in self.grid.SelectedRows:
                for c in range(self.grid.Columns.Count):
                    apply(r.Cells[c])
        elif scope == "Selected Cells":
            for c in self.grid.SelectedCells:
                apply(c)


# --------------------------------------------------------
# RUN
# --------------------------------------------------------

WF.Application.EnableVisualStyles()
BatchEditor(rows).ShowDialog()