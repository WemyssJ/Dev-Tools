# -*- coding: utf-8 -*-
__doc__ = "Multi-Category Material Changer - select categories, current material, and target material"

import clr
import sys
import traceback
clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")
clr.AddReference("PresentationFramework")

from System import Array
from System.Drawing import Point, Size, Font
from System.Windows.Forms import (
    Form, CheckedListBox, ListBox, ComboBox, TextBox,
    Button, Label, CheckState, SelectionMode, HorizontalAlignment
)
from pyrevit import revit, forms
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, ElementId, Transaction

doc = revit.doc
uidoc = revit.uidoc

# ----- Helper -----
def safe_get_param_value(param):
    try:
        if param is None or not param.HasValue:
            return None
        st = param.StorageType.ToString()
        if st == "ElementId":
            eid = param.AsElementId()
            return eid if eid and eid.IntegerValue >= 0 else None
    except:
        return None
    return None

# ----- Main Form -----
class MaterialChangerForm(Form):
    def __init__(self):
        self.Text = "Material Changer"
        self.Width = 950
        self.Height = 600
        self.StartPosition = 0
        self.Font = Font("Segoe UI", 10)

        # --- Categories Column ---
        self.lblCat = Label(Text="Categories", Location=Point(12, 10), Size=Size(300, 20))
        self.Controls.Add(self.lblCat)
        self.txtCatFilter = TextBox(Location=Point(12, 35), Width=300)
        self.txtCatFilter.TextChanged += self.on_cat_search
        self.Controls.Add(self.txtCatFilter)
        self.checkedCategories = CheckedListBox(Location=Point(12, 65), Size=Size(300, 400))
        self.checkedCategories.CheckOnClick = True
        self.checkedCategories.ItemCheck += self.on_cat_check
        self.Controls.Add(self.checkedCategories)

        # --- Current Material Column ---
        self.lblCurMat = Label(Text="Current Material", Location=Point(330, 10), Size=Size(300, 20))
        self.Controls.Add(self.lblCurMat)
        self.txtCurMatFilter = TextBox(Location=Point(330, 35), Width=300)
        self.txtCurMatFilter.TextChanged += self.on_curmat_search
        self.Controls.Add(self.txtCurMatFilter)
        self.checkedCurrentMat = CheckedListBox(Location=Point(330, 65), Size=Size(300, 400))
        self.checkedCurrentMat.CheckOnClick = True
        self.Controls.Add(self.checkedCurrentMat)

        # --- Target Material Column ---
        self.lblTargetMat = Label(Text="Target Material", Location=Point(650, 10), Size=Size(280, 20))
        self.Controls.Add(self.lblTargetMat)
        self.txtTargetMatFilter = TextBox(Location=Point(650, 35), Width=280)
        self.txtTargetMatFilter.TextChanged += self.on_targetmat_search
        self.Controls.Add(self.txtTargetMatFilter)
        self.checkedTargetMat = CheckedListBox(Location=Point(650, 65), Size=Size(280, 400))
        self.checkedTargetMat.CheckOnClick = True
        self.Controls.Add(self.checkedTargetMat)

        # --- Status and Buttons ---
        self.lblStatus = Label(Text="Elements matching current selection: 0", Location=Point(12, 480), Size=Size(600, 30))
        self.Controls.Add(self.lblStatus)
        self.btnConfirm = Button(Text="Confirm", Location=Point(650, 480), Size=Size(120, 30))
        self.btnConfirm.Click += self.on_confirm
        self.Controls.Add(self.btnConfirm)
        self.btnClose = Button(Text="Close", Location=Point(780, 480), Size=Size(120, 30))
        self.btnClose.Click += lambda s,a: self.Close()
        self.Controls.Add(self.btnClose)

        # ----- Data Caches -----
        self.all_categories = []
        self.all_materials = {}
        self.selected_category_ids = set()
        self.elements_in_selected_cats = []
        self.populate_categories()
        self.populate_target_materials()

    # --- Categories ---
    def populate_categories(self):
        cats = [c for c in doc.Settings.Categories if c.CategoryType.ToString() == "Model"]
        self.all_categories = sorted(cats, key=lambda x: x.Name)
        self.checkedCategories.Items.Clear()
        for c in self.all_categories:
            self.checkedCategories.Items.Add(c.Name, False)

    def on_cat_search(self, sender, args):
        txt = (self.txtCatFilter.Text or "").lower()
        self.checkedCategories.Items.Clear()
        for c in self.all_categories:
            if txt in c.Name.lower():
                self.checkedCategories.Items.Add(c.Name, False)

    def on_cat_check(self, sender, e):
        # delay execution until after check state applied
        from System.Threading import Thread, ThreadStart
        def update_materials():
            self.selected_category_ids = set()
            for i in range(self.checkedCategories.Items.Count):
                if self.checkedCategories.GetItemChecked(i):
                    name = self.checkedCategories.Items[i]
                    cat = next((c for c in self.all_categories if c.Name == name), None)
                    if cat:
                        self.selected_category_ids.add(cat.Id.IntegerValue)
            # collect elements in selected categories
            self.elements_in_selected_cats = []
            if self.selected_category_ids:
                for catid in self.selected_category_ids:
                    collector = FilteredElementCollector(doc).WhereElementIsNotElementType().OfCategoryId(ElementId(catid))
                    try:
                        elems = collector.ToElements()
                    except:
                        elems = [doc.GetElement(eid) for eid in collector.ToElementIds()]
                    self.elements_in_selected_cats.extend(elems)
            self.populate_current_materials()
        Thread(ThreadStart(update_materials)).Start()

    # --- Current Material ---
    def populate_current_materials(self):
        self.checkedCurrentMat.BeginUpdate()
        try:
            checked_before = [self.checkedCurrentMat.Items[i] for i in range(self.checkedCurrentMat.Items.Count) if self.checkedCurrentMat.GetItemChecked(i)]
            mat_set = set()
            for e in self.elements_in_selected_cats:
                try:
                    for pname in ["Material", "Structural Material"]:
                        p = e.LookupParameter(pname)
                        eid = safe_get_param_value(p)
                        if eid:
                            mat_set.add(eid)
                except:
                    continue
            # Build list of (name, id)
            self.current_material_list = []
            for eid in mat_set:
                mat = doc.GetElement(eid)
                if mat:
                    self.current_material_list.append((mat.Name, eid))
            self.current_material_list.sort(key=lambda x:x[0])
            # update listbox
            self.checkedCurrentMat.Items.Clear()
            for name, eid in self.current_material_list:
                checked = name in checked_before
                self.checkedCurrentMat.Items.Add(name, checked)
            self.lblStatus.Text = "Elements matching current selection: {}".format(len(self.elements_in_selected_cats))
        finally:
            self.checkedCurrentMat.EndUpdate()

    def on_curmat_search(self, sender, args):
        txt = (self.txtCurMatFilter.Text or "").lower()
        self.checkedCurrentMat.Items.Clear()
        for name, eid in self.current_material_list:
            if txt in name.lower():
                self.checkedCurrentMat.Items.Add(name, False)

    # --- Target Material ---
    def populate_target_materials(self):
        mats = FilteredElementCollector(doc).OfClass(revit.DB.Material).ToElements()
        self.all_materials = sorted(mats, key=lambda x: x.Name)
        self.checkedTargetMat.Items.Clear()
        for m in self.all_materials:
            self.checkedTargetMat.Items.Add(m.Name, False)

    def on_targetmat_search(self, sender, args):
        txt = (self.txtTargetMatFilter.Text or "").lower()
        self.checkedTargetMat.Items.Clear()
        for m in self.all_materials:
            if txt in m.Name.lower():
                self.checkedTargetMat.Items.Add(m.Name, False)

    # --- Confirm Assignment ---
    def on_confirm(self, sender, args):
        # Get selected current materials
        selected_cur_ids = []
        for i in range(self.checkedCurrentMat.Items.Count):
            if self.checkedCurrentMat.GetItemChecked(i):
                name = self.checkedCurrentMat.Items[i]
                eid = next((eid for n, eid in self.current_material_list if n==name), None)
                if eid:
                    selected_cur_ids.append(eid)
        if not selected_cur_ids:
            forms.alert("No current materials selected.")
            return
        # Get selected target material
        selected_target_ids = []
        for i in range(self.checkedTargetMat.Items.Count):
            if self.checkedTargetMat.GetItemChecked(i):
                selected_target_ids.append(self.all_materials[i].Id)
        if not selected_target_ids:
            forms.alert("No target material selected.")
            return
        target_id = selected_target_ids[0]

        # Apply target material to elements with selected current materials
        with Transaction(doc, "Change Materials") as t:
            t.Start()
            count = 0
            for e in self.elements_in_selected_cats:
                try:
                    for pname in ["Material", "Structural Material"]:
                        p = e.LookupParameter(pname)
                        eid = safe_get_param_value(p)
                        if eid and eid in selected_cur_ids:
                            p.Set(target_id)
                            count +=1
                except:
                    continue
            t.Commit()
        forms.alert("Updated {} elements with new material.".format(count))
        self.lblStatus.Text = "Elements matching current selection: {}".format(len(self.elements_in_selected_cats))

# --- Run ---
def main():
    try:
        f = MaterialChangerForm()
        f.ShowDialog()
    except Exception:
        traceback.print_exc()
        forms.alert("Unhandled error: {}".format(sys.exc_info()[1]))

if __name__ == "__main__":
    main()
