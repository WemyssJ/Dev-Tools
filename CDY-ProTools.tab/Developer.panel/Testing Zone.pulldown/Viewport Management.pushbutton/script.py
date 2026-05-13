# -*- coding: utf-8 -*-

from pyrevit import revit, DB, forms
from Autodesk.Revit.DB import *

from System.Windows.Forms import (
    Form, DataGridView, DockStyle, Button, Panel,
    DataGridViewAutoSizeColumnsMode, DataGridViewSelectionMode,
    ComboBox, TextBox, Label
)

from System.Drawing import Size, Color, Point


doc = revit.doc
uidoc = revit.uidoc


# --------------------------------------------------------
# HELPERS
# --------------------------------------------------------

def get_viewports_from_views(view_ids):
    return [
        vp for vp in FilteredElementCollector(doc).OfClass(Viewport)
        if vp.ViewId in view_ids
    ]


# --------------------------------------------------------
# INPUT DETECTION
# --------------------------------------------------------

selection_ids = list(uidoc.Selection.GetElementIds())

viewports = []
views = []

for elid in selection_ids:
    el = doc.GetElement(elid)

    if isinstance(el, Viewport):
        viewports.append(el)

    elif isinstance(el, View):
        if not el.IsTemplate:
            views.append(el)

if views and not viewports:
    viewports = get_viewports_from_views([v.Id for v in views])

if not viewports:
    forms.alert("Select Viewports or Views.", exitscript=True)


# --------------------------------------------------------
# DATA MODEL
# --------------------------------------------------------

rows = []

for vp in viewports:

    view = doc.GetElement(vp.ViewId)
    sheet = doc.GetElement(vp.SheetId)

    rows.append({
        "vp_id": vp.Id.IntegerValue,
        "sheet": sheet.SheetNumber,
        "detail": vp.get_Parameter(BuiltInParameter.VIEWPORT_DETAIL_NUMBER).AsString(),
        "view_name": view.Name,
        "sheet_name": sheet.Name,
        "title": vp.get_Parameter(BuiltInParameter.VIEW_DESCRIPTION).AsString() or ""
    })


# --------------------------------------------------------
# UI
# --------------------------------------------------------

class BatchEditor(Form):

    def __init__(self, data):

        self.data = data

        self.Text = "Viewport / View Batch Editor"
        self.Size = Size(1300, 750)

        # ---------------- GRID ----------------
        self.grid = DataGridView()
        self.grid.Dock = DockStyle.Fill
        self.grid.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill

        self.grid.SelectionMode = DataGridViewSelectionMode.CellSelect
        self.grid.MultiSelect = True
        self.grid.AllowUserToAddRows = False
        self.grid.AllowUserToDeleteRows = False

        self.grid.ColumnHeaderMouseClick += self.on_column_header_click

        # Columns (ID hidden)
        self.grid.ColumnCount = 6

        self.grid.Columns[0].Name = "ID"
        self.grid.Columns[0].Visible = False

        self.grid.Columns[1].Name = "Sheet"
        self.grid.Columns[2].Name = "Detail Number"
        self.grid.Columns[3].Name = "View Name"
        self.grid.Columns[4].Name = "Sheet Name"
        self.grid.Columns[5].Name = "Title on Sheet"

        # Populate grid
        for item in data:
            r = self.grid.Rows.Add()

            self.grid.Rows[r].Cells[0].Value = item["vp_id"]
            self.grid.Rows[r].Cells[1].Value = item["sheet"]
            self.grid.Rows[r].Cells[2].Value = item["detail"]
            self.grid.Rows[r].Cells[3].Value = item["view_name"]
            self.grid.Rows[r].Cells[4].Value = item["sheet_name"]
            self.grid.Rows[r].Cells[5].Value = item["title"]

        # ---------------- PANEL ----------------
        panel = Panel()
        panel.Dock = DockStyle.Bottom
        panel.Height = 180

        # =====================================================
        # ROW 1 - ACTIONS
        # =====================================================

        self.apply_btn = Button()
        self.apply_btn.Text = "Apply"
        self.apply_btn.Location = Point(10, 10)
        self.apply_btn.Width = 120
        self.apply_btn.Click += self.apply_changes

        self.clear_btn = Button()
        self.clear_btn.Text = "Clear Titles"
        self.clear_btn.Location = Point(140, 10)
        self.clear_btn.Width = 120
        self.clear_btn.Click += self.clear_titles

        self.sync_v2d = Button()
        self.sync_v2d.Text = "View → Detail"
        self.sync_v2d.Location = Point(270, 10)
        self.sync_v2d.Width = 140
        self.sync_v2d.Click += self.sync_view_to_detail

        self.sync_d2v = Button()
        self.sync_d2v.Text = "Detail → View"
        self.sync_d2v.Location = Point(420, 10)
        self.sync_d2v.Width = 140
        self.sync_d2v.Click += self.sync_detail_to_view

        # Divider
        self.divider = Label()
        self.divider.Text = ""
        self.divider.AutoSize = False
        self.divider.Location = Point(10, 50)
        self.divider.Width = 1250
        self.divider.Height = 1
        self.divider.BackColor = Color.LightGray

        # =====================================================
        # ROW 2 - FIND / REPLACE
        # =====================================================

        y = 85

        self.find_label = Label()
        self.find_label.Text = "Find:"
        self.find_label.Location = Point(10, y)

        self.find_box = TextBox()
        self.find_box.Location = Point(55, y - 3)
        self.find_box.Width = 160

        self.replace_label = Label()
        self.replace_label.Text = "Replace:"
        self.replace_label.Location = Point(230, y)

        self.replace_box = TextBox()
        self.replace_box.Location = Point(295, y - 3)
        self.replace_box.Width = 160

        self.scope_box = ComboBox()
        self.scope_box.Location = Point(470, y - 3)
        self.scope_box.Width = 160
        self.scope_box.Items.Add("All")
        self.scope_box.Items.Add("Selected Rows")
        self.scope_box.Items.Add("Selected Cells")
        self.scope_box.SelectedIndex = 0

        self.replace_btn = Button()
        self.replace_btn.Text = "Replace"
        self.replace_btn.Location = Point(640, y - 5)
        self.replace_btn.Width = 120
        self.replace_btn.Click += self.find_replace

        # Add controls
        panel.Controls.Add(self.apply_btn)
        panel.Controls.Add(self.clear_btn)
        panel.Controls.Add(self.sync_v2d)
        panel.Controls.Add(self.sync_d2v)

        panel.Controls.Add(self.divider)

        panel.Controls.Add(self.find_label)
        panel.Controls.Add(self.find_box)
        panel.Controls.Add(self.replace_label)
        panel.Controls.Add(self.replace_box)
        panel.Controls.Add(self.scope_box)
        panel.Controls.Add(self.replace_btn)

        self.Controls.Add(self.grid)
        self.Controls.Add(panel)


    # --------------------------------------------------------
    # COLUMN SELECT
    # --------------------------------------------------------

    def on_column_header_click(self, sender, e):
        col = e.ColumnIndex
        self.grid.ClearSelection()

        for r in range(self.grid.Rows.Count):
            self.grid.Rows[r].Cells[col].Selected = True


    # --------------------------------------------------------
    # SYNC
    # --------------------------------------------------------

    def sync_view_to_detail(self, sender, args):

        rows = self.grid.SelectedRows
        if rows.Count == 0:
            rows = self.grid.Rows

        for r in rows:
            v = r.Cells[3].Value
            if v:
                r.Cells[2].Value = str(v)

        forms.alert("View → Detail synced.")


    def sync_detail_to_view(self, sender, args):

        rows = self.grid.SelectedRows
        if rows.Count == 0:
            rows = self.grid.Rows

        for r in rows:
            d = r.Cells[2].Value
            if d:
                r.Cells[3].Value = str(d)

        forms.alert("Detail → View synced.")


    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    def validate(self):

        seen = {}
        conflicts = set()

        for r in range(self.grid.Rows.Count):
            self.grid.Rows[r].DefaultCellStyle.BackColor = Color.White

        for r in range(self.grid.Rows.Count):

            sheet = str(self.grid.Rows[r].Cells[1].Value)
            detail = str(self.grid.Rows[r].Cells[2].Value)

            key = (sheet, detail)

            if key in seen:
                conflicts.add(r)
                conflicts.add(seen[key])
            else:
                seen[key] = r

        for r in conflicts:
            row = self.grid.Rows[r]
            row.DefaultCellStyle.BackColor = Color.LightCoral
            row.DefaultCellStyle.SelectionBackColor = Color.IndianRed

        return len(conflicts) == 0


    # --------------------------------------------------------
    # APPLY (FULL 3-PHASE SAFE SYSTEM)
    # --------------------------------------------------------

    def apply_changes(self, sender, args):

        if not self.validate():
            forms.alert("Duplicate detail numbers detected.")
            return

        try:
            ops = []

            for r in self.grid.Rows:
                if r.IsNewRow:
                    continue

                vp = doc.GetElement(ElementId(int(r.Cells[0].Value)))
                view = doc.GetElement(vp.ViewId)

                ops.append({
                    "vp": vp,
                    "view": view,
                    "detail": str(r.Cells[2].Value),
                    "view_name": str(r.Cells[3].Value),
                    "title": str(r.Cells[5].Value)
                })

            # =================================================
            # PHASE 1: TEMP DETAIL NUMBERS
            # =================================================
            t1 = Transaction(doc, "Temp Detail Numbers")
            t1.Start()

            for o in ops:
                vp = o["vp"]
                p = vp.get_Parameter(BuiltInParameter.VIEWPORT_DETAIL_NUMBER)
                if p and not p.IsReadOnly:
                    p.Set("__TMP_DN_{}".format(vp.Id.IntegerValue))

            t1.Commit()

            # =================================================
            # PHASE 2: TEMP VIEW NAMES
            # =================================================
            t2 = Transaction(doc, "Temp View Names")
            t2.Start()

            for o in ops:
                v = o["view"]
                if v:
                    v.Name = "__TMP_VIEW_{}".format(v.Id.IntegerValue)

            t2.Commit()

            # =================================================
            # PHASE 3: FINAL VALUES
            # =================================================
            t3 = Transaction(doc, "Final Values")
            t3.Start()

            for o in ops:

                vp = o["vp"]
                view = o["view"]

                p = vp.get_Parameter(BuiltInParameter.VIEWPORT_DETAIL_NUMBER)
                if p and not p.IsReadOnly:
                    p.Set(o["detail"])

                tp = vp.get_Parameter(BuiltInParameter.VIEW_DESCRIPTION)
                if tp and not tp.IsReadOnly:
                    tp.Set(o["title"])

                if view:
                    view.Name = o["view_name"]

            t3.Commit()

            forms.alert("Update complete (fully safe 3-phase system).")

        except Exception as ex:
            forms.alert(str(ex))


    # --------------------------------------------------------
    # CLEAR TITLES
    # --------------------------------------------------------

    def clear_titles(self, sender, args):

        for r in self.grid.SelectedRows:
            r.Cells[5].Value = ""

        forms.alert("Titles cleared.")


    # --------------------------------------------------------
    # FIND / REPLACE
    # --------------------------------------------------------

    def find_replace(self, sender, args):

        f = self.find_box.Text
        rep = self.replace_box.Text
        scope = self.scope_box.SelectedItem

        if not f:
            forms.alert("Enter find text.")
            return

        def apply(cell):
            if cell.Value:
                v = str(cell.Value)
                if f in v:
                    cell.Value = v.replace(f, rep)

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

        forms.alert("Replace complete.")


# --------------------------------------------------------
# RUN
# --------------------------------------------------------

BatchEditor(rows).ShowDialog()