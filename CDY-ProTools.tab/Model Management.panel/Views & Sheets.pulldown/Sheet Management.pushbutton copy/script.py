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
# GET SELECTED SHEETS
# --------------------------------------------------------

selection_ids = list(uidoc.Selection.GetElementIds())

sheets = []

for elid in selection_ids:

    el = doc.GetElement(elid)

    if isinstance(el, ViewSheet):
        sheets.append(el)

if not sheets:
    forms.alert("Select Sheets.", exitscript=True)


# --------------------------------------------------------
# DATA MODEL
# --------------------------------------------------------

rows = []

for sheet in sheets:

    p2 = sheet.LookupParameter("DRAWING TITLE 2")
    p3 = sheet.LookupParameter("DRAWING TITLE 3")

    rows.append({
        "id": sheet.Id.IntegerValue,
        "sheet_number": sheet.SheetNumber,
        "sheet_name": sheet.Name,
        "title2": p2.AsString() if p2 else "",
        "title3": p3.AsString() if p3 else ""
    })


# --------------------------------------------------------
# UI
# --------------------------------------------------------

class SheetBatchEditor(Form):

    def __init__(self, data):

        self.data = data

        self.Text = "Sheet Batch Editor"
        self.Size = Size(1400, 750)

        # =====================================================
        # GRID
        # =====================================================

        self.grid = DataGridView()
        self.grid.Dock = DockStyle.Fill
        self.grid.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill

        self.grid.SelectionMode = DataGridViewSelectionMode.CellSelect
        self.grid.MultiSelect = True
        self.grid.AllowUserToAddRows = False
        self.grid.AllowUserToDeleteRows = False

        self.grid.ColumnHeaderMouseClick += self.on_column_header_click

        self.grid.ColumnCount = 5

        self.grid.Columns[0].Name = "ID"
        self.grid.Columns[0].Visible = False

        self.grid.Columns[1].Name = "Sheet Number"
        self.grid.Columns[2].Name = "Sheet Name"
        self.grid.Columns[3].Name = "DRAWING TITLE 2"
        self.grid.Columns[4].Name = "DRAWING TITLE 3"

        # Populate
        for item in data:

            r = self.grid.Rows.Add()

            self.grid.Rows[r].Cells[0].Value = item["id"]
            self.grid.Rows[r].Cells[1].Value = item["sheet_number"]
            self.grid.Rows[r].Cells[2].Value = item["sheet_name"]
            self.grid.Rows[r].Cells[3].Value = item["title2"]
            self.grid.Rows[r].Cells[4].Value = item["title3"]

        # =====================================================
        # PANEL
        # =====================================================

        panel = Panel()
        panel.Dock = DockStyle.Bottom
        panel.Height = 180

        # =====================================================
        # APPLY
        # =====================================================

        self.apply_btn = Button()
        self.apply_btn.Text = "Apply"
        self.apply_btn.Location = Point(10, 10)
        self.apply_btn.Width = 120
        self.apply_btn.Click += self.apply_changes

        self.clear_btn = Button()
        self.clear_btn.Text = "Clear Titles"
        self.clear_btn.Location = Point(140, 10)
        self.clear_btn.Width = 140
        self.clear_btn.Click += self.clear_titles

        # Divider
        self.divider = Label()
        self.divider.Text = ""
        self.divider.AutoSize = False
        self.divider.Location = Point(10, 50)
        self.divider.Width = 1300
        self.divider.Height = 1
        self.divider.BackColor = Color.LightGray

        # =====================================================
        # FIND / REPLACE
        # =====================================================

        y = 85

        self.find_label = Label()
        self.find_label.Text = "Find:"
        self.find_label.Location = Point(10, y)

        self.find_box = TextBox()
        self.find_box.Location = Point(55, y - 3)
        self.find_box.Width = 180

        self.replace_label = Label()
        self.replace_label.Text = "Replace:"
        self.replace_label.Location = Point(250, y)

        self.replace_box = TextBox()
        self.replace_box.Location = Point(320, y - 3)
        self.replace_box.Width = 180

        self.scope_box = ComboBox()
        self.scope_box.Location = Point(520, y - 3)
        self.scope_box.Width = 180

        self.scope_box.Items.Add("All")
        self.scope_box.Items.Add("Selected Rows")
        self.scope_box.Items.Add("Selected Cells")

        self.scope_box.SelectedIndex = 0

        self.replace_btn = Button()
        self.replace_btn.Text = "Replace"
        self.replace_btn.Location = Point(720, y - 5)
        self.replace_btn.Width = 120
        self.replace_btn.Click += self.find_replace

        # Add controls
        panel.Controls.Add(self.apply_btn)
        panel.Controls.Add(self.clear_btn)

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
    # VALIDATE SHEET NUMBERS
    # --------------------------------------------------------

    def validate(self):

        seen = {}
        conflicts = set()

        # Reset colours
        for r in range(self.grid.Rows.Count):

            self.grid.Rows[r].DefaultCellStyle.BackColor = Color.White
            self.grid.Rows[r].DefaultCellStyle.SelectionBackColor = Color.DodgerBlue

        for r in range(self.grid.Rows.Count):

            sheet_number = str(self.grid.Rows[r].Cells[1].Value)

            if sheet_number in seen:

                conflicts.add(r)
                conflicts.add(seen[sheet_number])

            else:
                seen[sheet_number] = r

        for r in conflicts:

            row = self.grid.Rows[r]

            row.DefaultCellStyle.BackColor = Color.LightCoral
            row.DefaultCellStyle.SelectionBackColor = Color.IndianRed

        return len(conflicts) == 0


    # --------------------------------------------------------
    # APPLY
    # --------------------------------------------------------

    def apply_changes(self, sender, args):

        if not self.validate():

            forms.alert("Duplicate sheet numbers detected.")
            return

        try:

            ops = []

            for r in self.grid.Rows:

                if r.IsNewRow:
                    continue

                sheet = doc.GetElement(ElementId(int(r.Cells[0].Value)))

                ops.append({
                    "sheet": sheet,
                    "sheet_number": str(r.Cells[1].Value),
                    "sheet_name": str(r.Cells[2].Value),
                    "title2": str(r.Cells[3].Value),
                    "title3": str(r.Cells[4].Value)
                })

            # =================================================
            # PHASE 1
            # TEMP SHEET NUMBERS
            # =================================================

            t1 = Transaction(doc, "Temp Sheet Numbers")
            t1.Start()

            for o in ops:

                sheet = o["sheet"]

                try:
                    sheet.SheetNumber = "__TMP_{}".format(sheet.Id.IntegerValue)
                except:
                    pass

            t1.Commit()

            # =================================================
            # PHASE 2
            # FINAL VALUES
            # =================================================

            t2 = Transaction(doc, "Apply Sheet Changes")
            t2.Start()

            for o in ops:

                sheet = o["sheet"]

                # Sheet Number
                try:
                    sheet.SheetNumber = o["sheet_number"]
                except:
                    pass

                # Sheet Name
                try:
                    sheet.Name = o["sheet_name"]
                except:
                    pass

                # DRAWING TITLE 2
                p2 = sheet.LookupParameter("DRAWING TITLE 2")

                if p2 and not p2.IsReadOnly:
                    p2.Set(o["title2"])

                # DRAWING TITLE 3
                p3 = sheet.LookupParameter("DRAWING TITLE 3")

                if p3 and not p3.IsReadOnly:
                    p3.Set(o["title3"])

            t2.Commit()

            forms.alert("Sheet update complete.")

        except Exception as ex:

            forms.alert(str(ex))


    # --------------------------------------------------------
    # CLEAR TITLES
    # --------------------------------------------------------

    def clear_titles(self, sender, args):

        rows = self.grid.SelectedRows

        if rows.Count == 0:
            rows = self.grid.Rows

        for r in rows:

            r.Cells[3].Value = ""
            r.Cells[4].Value = ""

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

        # =====================================================
        # ALL
        # =====================================================

        if scope == "All":

            for r in range(self.grid.Rows.Count):

                for c in range(1, self.grid.Columns.Count):
                    apply(self.grid.Rows[r].Cells[c])

        # =====================================================
        # SELECTED ROWS
        # =====================================================

        elif scope == "Selected Rows":

            for r in self.grid.SelectedRows:

                for c in range(1, self.grid.Columns.Count):
                    apply(r.Cells[c])

        # =====================================================
        # SELECTED CELLS
        # =====================================================

        elif scope == "Selected Cells":

            for c in self.grid.SelectedCells:
                apply(c)

        forms.alert("Replace complete.")


# --------------------------------------------------------
# RUN
# --------------------------------------------------------

SheetBatchEditor(rows).ShowDialog()