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
    vps = []
    all_vps = FilteredElementCollector(doc).OfClass(Viewport).ToElements()

    for vp in all_vps:
        if vp.ViewId in view_ids:
            vps.append(vp)

    return vps


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
    view_ids = [v.Id for v in views]
    viewports = get_viewports_from_views(view_ids)

if not viewports:
    forms.alert("Select Viewports OR Views.", exitscript=True)


# --------------------------------------------------------
# DATA MODEL
# --------------------------------------------------------

rows = []

for vp in viewports:

    view = doc.GetElement(vp.ViewId)
    sheet = doc.GetElement(vp.SheetId)

    detail_num = vp.get_Parameter(
        BuiltInParameter.VIEWPORT_DETAIL_NUMBER
    ).AsString()

    title_param = vp.get_Parameter(
        BuiltInParameter.VIEW_DESCRIPTION
    )

    title = title_param.AsString() if title_param else ""

    rows.append({
        "viewport": vp,
        "view": view,
        "sheet": sheet,
        "sheet_number": sheet.SheetNumber,
        "sheet_name": sheet.Name,
        "detail_number": detail_num,
        "view_name": view.Name,
        "title_on_sheet": title
    })


# --------------------------------------------------------
# UI
# --------------------------------------------------------

class BatchEditor(Form):

    def __init__(self, data):

        self.data = data

        self.Text = "Viewport / View Batch Editor"
        self.Size = Size(1200, 720)

        # ---------------- GRID ----------------
        self.grid = DataGridView()
        self.grid.Dock = DockStyle.Fill
        self.grid.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill

        self.grid.SelectionMode = DataGridViewSelectionMode.CellSelect
        self.grid.MultiSelect = True

        self.grid.AllowUserToAddRows = False
        self.grid.AllowUserToDeleteRows = False
        self.grid.RowHeadersVisible = True

        self.grid.ColumnHeaderMouseClick += self.on_column_header_click

        self.grid.ColumnCount = 5

        self.grid.Columns[0].Name = "Sheet"
        self.grid.Columns[0].ReadOnly = True

        self.grid.Columns[1].Name = "Detail Number"
        self.grid.Columns[2].Name = "View Name"
        self.grid.Columns[3].Name = "Sheet Name"
        self.grid.Columns[3].ReadOnly = True
        self.grid.Columns[4].Name = "Title on Sheet"

        for item in data:
            i = self.grid.Rows.Add()
            self.grid.Rows[i].Cells[0].Value = item["sheet_number"]
            self.grid.Rows[i].Cells[1].Value = item["detail_number"]
            self.grid.Rows[i].Cells[2].Value = item["view_name"]
            self.grid.Rows[i].Cells[3].Value = item["sheet_name"]
            self.grid.Rows[i].Cells[4].Value = item["title_on_sheet"]

        # ---------------- PANEL ----------------
        panel = Panel()
        panel.Dock = DockStyle.Bottom
        panel.Height = 160

        # =====================================================
        # ROW 1 - ACTIONS
        # =====================================================

        self.apply_btn = Button()
        self.apply_btn.Text = "Apply Changes"
        self.apply_btn.Location = Point(10, 10)
        self.apply_btn.Width = 140
        self.apply_btn.Click += self.apply_changes

        self.clear_btn = Button()
        self.clear_btn.Text = "Clear Titles"
        self.clear_btn.Location = Point(160, 10)
        self.clear_btn.Width = 140
        self.clear_btn.Click += self.clear_titles

        # NEW: SYNC BUTTONS
        self.sync_view_to_detail_btn = Button()
        self.sync_view_to_detail_btn.Text = "View → Detail"
        self.sync_view_to_detail_btn.Location = Point(310, 10)
        self.sync_view_to_detail_btn.Width = 140
        self.sync_view_to_detail_btn.Click += self.sync_view_to_detail

        self.sync_detail_to_view_btn = Button()
        self.sync_detail_to_view_btn.Text = "Detail → View"
        self.sync_detail_to_view_btn.Location = Point(460, 10)
        self.sync_detail_to_view_btn.Width = 140
        self.sync_detail_to_view_btn.Click += self.sync_detail_to_view

        # =====================================================
        # DIVIDER
        # =====================================================

        self.divider = Label()
        self.divider.Text = ""
        self.divider.AutoSize = False
        self.divider.Location = Point(10, 50)
        self.divider.Width = 1100
        self.divider.Height = 1
        self.divider.BackColor = Color.LightGray

        # =====================================================
        # ROW 2 - FIND / REPLACE
        # =====================================================

        base_y = 80

        self.find_label = Label()
        self.find_label.Text = "Find:"
        self.find_label.AutoSize = True
        self.find_label.Location = Point(10, base_y)

        self.find_box = TextBox()
        self.find_box.Location = Point(55, base_y - 3)
        self.find_box.Width = 160

        self.replace_label = Label()
        self.replace_label.Text = "Replace:"
        self.replace_label.AutoSize = True
        self.replace_label.Location = Point(230, base_y)

        self.replace_box = TextBox()
        self.replace_box.Location = Point(295, base_y - 3)
        self.replace_box.Width = 160

        self.scope_box = ComboBox()
        self.scope_box.Location = Point(470, base_y - 4)
        self.scope_box.Width = 160
        self.scope_box.Items.Add("All")
        self.scope_box.Items.Add("Selected Rows")
        self.scope_box.Items.Add("Selected Cells")
        self.scope_box.SelectedIndex = 0

        self.replace_btn = Button()
        self.replace_btn.Text = "Replace"
        self.replace_btn.Location = Point(640, base_y - 5)
        self.replace_btn.Width = 120
        self.replace_btn.Click += self.find_replace

        # ---------------- ADD CONTROLS ----------------

        panel.Controls.Add(self.apply_btn)
        panel.Controls.Add(self.clear_btn)

        panel.Controls.Add(self.sync_view_to_detail_btn)
        panel.Controls.Add(self.sync_detail_to_view_btn)

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

    def on_column_header_click(self, sender, event):

        col = event.ColumnIndex
        self.grid.ClearSelection()

        for r in range(self.grid.Rows.Count):
            self.grid.Rows[r].Cells[col].Selected = True


    # --------------------------------------------------------
    # SYNC: VIEW → DETAIL
    # --------------------------------------------------------

    def sync_view_to_detail(self, sender, args):

        rows = self.grid.SelectedRows
        if rows.Count == 0:
            rows = self.grid.Rows

        for r in rows:
            v = r.Cells[2].Value
            if v:
                r.Cells[1].Value = str(v)

        forms.alert("View → Detail synced.")


    # --------------------------------------------------------
    # SYNC: DETAIL → VIEW
    # --------------------------------------------------------

    def sync_detail_to_view(self, sender, args):

        rows = self.grid.SelectedRows
        if rows.Count == 0:
            rows = self.grid.Rows

        for r in rows:
            d = r.Cells[1].Value
            if d:
                r.Cells[2].Value = str(d)

        forms.alert("Detail → View synced.")


    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    def validate(self):

        seen = {}
        conflicts = set()

        for i in range(self.grid.Rows.Count):
            self.grid.Rows[i].DefaultCellStyle.BackColor = Color.White

        for i in range(self.grid.Rows.Count):

            sheet = str(self.grid.Rows[i].Cells[0].Value)
            detail = str(self.grid.Rows[i].Cells[1].Value)

            key = (sheet, detail)

            if key in seen:
                conflicts.add(i)
                conflicts.add(seen[key])
            else:
                seen[key] = i

        for i in conflicts:
            row = self.grid.Rows[i]
            row.DefaultCellStyle.BackColor = Color.LightCoral
            row.DefaultCellStyle.SelectionBackColor = Color.IndianRed

        return len(conflicts) == 0


    # --------------------------------------------------------
    # APPLY
    # --------------------------------------------------------

    def apply_changes(self, sender, args):

        if not self.validate():
            forms.alert("Duplicate detail numbers detected.")
            return

        t = Transaction(doc, "Batch Update Views")
        t.Start()

        try:
            for i, item in enumerate(self.data):

                vp = item["viewport"]
                view = item["view"]

                new_detail = str(self.grid.Rows[i].Cells[1].Value)
                new_view_name = str(self.grid.Rows[i].Cells[2].Value)
                new_title = str(self.grid.Rows[i].Cells[4].Value)

                if vp:
                    p = vp.get_Parameter(BuiltInParameter.VIEWPORT_DETAIL_NUMBER)
                    if p and not p.IsReadOnly:
                        p.Set(new_detail)

                    tp = vp.get_Parameter(BuiltInParameter.VIEW_DESCRIPTION)
                    if tp and not tp.IsReadOnly:
                        tp.Set(new_title)

                if view and view.Name != new_view_name:
                    view.Name = new_view_name

            t.Commit()
            forms.alert("Update complete.")

        except Exception as ex:
            t.RollBack()
            forms.alert(str(ex))


    # --------------------------------------------------------
    # CLEAR TITLES
    # --------------------------------------------------------

    def clear_titles(self, sender, args):

        for r in self.grid.SelectedRows:
            r.Cells[4].Value = ""

        forms.alert("Titles cleared.")


    # --------------------------------------------------------
    # FIND / REPLACE
    # --------------------------------------------------------

    def find_replace(self, sender, args):

        find_text = self.find_box.Text
        replace_text = self.replace_box.Text
        scope = self.scope_box.SelectedItem

        if not find_text:
            forms.alert("Enter find text.")
            return

        def replace(cell):
            if cell.Value:
                v = str(cell.Value)
                if find_text in v:
                    cell.Value = v.replace(find_text, replace_text)

        if scope == "All":

            for r in range(self.grid.Rows.Count):
                for c in range(self.grid.Columns.Count):
                    replace(self.grid.Rows[r].Cells[c])

        elif scope == "Selected Rows":

            for r in self.grid.SelectedRows:
                for c in range(self.grid.Columns.Count):
                    replace(r.Cells[c])

        elif scope == "Selected Cells":

            for cell in self.grid.SelectedCells:
                replace(cell)

        forms.alert("Replace complete.")


# --------------------------------------------------------
# RUN
# --------------------------------------------------------

BatchEditor(rows).ShowDialog()