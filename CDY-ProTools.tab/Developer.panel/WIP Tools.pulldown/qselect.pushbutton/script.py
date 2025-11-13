# -*- coding: utf-8 -*-
__doc__ = "QSelect - Splasher-style fast selector (Categories -> Parameters -> Values) - single-threaded"
import os
import sys
import traceback
import clr

clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")
clr.AddReference("System.Data")
clr.AddReference("PresentationFramework")

from System import DBNull
from System.Data import DataTable
from System.Drawing import Font, FontStyle, Color, Size, Point
from System.Windows.Forms import (
    Form,
    ComboBox,
    TextBox,
    CheckedListBox,
    ListBox,
    Button,
    Label,
    MessageBox,
    DialogResult,
    AnchorStyles,
    DockStyle,
    HorizontalAlignment,
    FormStartPosition,
    ComboBoxStyle,
    SelectionMode,
    CheckState
)

from pyrevit import revit, forms
from pyrevit import script
from Autodesk.Revit.DB import FilteredElementCollector
from System.Collections.Generic import List
from Autodesk.Revit.DB import ElementId
from pyrevit.compat import get_elementid_value_func

# Revit doc/ui
doc = revit.doc
uidoc = revit.uidoc

# Excluded categories - keep minimal but you can expand as needed
EXCLUDED_CAT_IDS = set([
    int(revit.DB.BuiltInCategory.OST_RoomSeparationLines),
    int(revit.DB.BuiltInCategory.OST_Cameras),
    int(revit.DB.BuiltInCategory.OST_CurtainGrids),
    int(revit.DB.BuiltInCategory.OST_Elev),
    int(revit.DB.BuiltInCategory.OST_Grids),
    int(revit.DB.BuiltInCategory.OST_IOSModelGroups),
    int(revit.DB.BuiltInCategory.OST_Views),
    int(revit.DB.BuiltInCategory.OST_SitePropertyLineSegment),
    int(revit.DB.BuiltInCategory.OST_SectionBox),
    int(revit.DB.BuiltInCategory.OST_ShaftOpening),
    int(revit.DB.BuiltInCategory.OST_BeamAnalytical),
    int(revit.DB.BuiltInCategory.OST_StructuralFramingOpening),
    int(revit.DB.BuiltInCategory.OST_MEPSpaceSeparationLines),
    int(revit.DB.BuiltInCategory.OST_DuctSystem),
    int(revit.DB.BuiltInCategory.OST_Lines),
    int(revit.DB.BuiltInCategory.OST_PipingSystem),
    int(revit.DB.BuiltInCategory.OST_Matchline),
    int(revit.DB.BuiltInCategory.OST_CenterLines),
    int(revit.DB.BuiltInCategory.OST_CurtainGridsRoof),
    int(revit.DB.BuiltInCategory.OST_SWallRectOpening),
    -2000278,
    -1,
])

# ---- Utility: safe parameter value extraction (like Splasher) ----
def safe_get_param_value(param):
    """Return string representation of parameter value (robust)."""
    try:
        if param is None or not param.HasValue:
            return "None"
        st = param.StorageType
        st_str = st.ToString()
        if st_str == "Double":
            # AsValueString usually produces nicely formatted string
            sval = param.AsValueString()
            return sval if sval is not None else "None"
        if st_str == "ElementId":
            elid = param.AsElementId()
            if elid is None or elid.IntegerValue < 0:
                return "None"
            try:
                el = doc.GetElement(elid)
                if el is not None:
                    # return the element name if possible
                    return revit.DB.Element.Name.GetValue(el)
            except:
                return "None"
            return "None"
        if st_str == "Integer":
            # try AsValueString to handle Yes/No nicely
            try:
                avs = param.AsValueString()
                if avs is not None:
                    return avs
            except:
                pass
            try:
                return str(param.AsInteger())
            except:
                return "None"
        if st_str == "String":
            s = param.AsString()
            return s if s is not None and s != "" else "None"
    except Exception:
        return "None"
    return "None"


# ---- Main WinForms QSelect form (splasher-derived style) ----
class QSelectForm(Form):
    def __init__(self):
        self.Text = "QSelect - Master Selector"
        self.Width = 980
        self.Height = 640
        self.StartPosition = FormStartPosition.CenterScreen
        self.Font = Font("Segoe UI", 10)
        self.Icon = None

        # --- Controls layout (3 columns) ---
        # Category label + search + combobox
        self.lblCat = Label(Text="Step 1: Category", Location=Point(12, 10), Size=Size(300, 20))
        self.Controls.Add(self.lblCat)

        self.txtCatFilter = TextBox(Location=Point(12, 35), Width=300)
        # don't rely on PlaceholderText in IronPython WinForms; keep blank
        self.txtCatFilter.TextChanged += self.on_cat_search
        self.Controls.Add(self.txtCatFilter)

        self.cmbCategories = ComboBox(Location=Point(12, 65), Width=300)
        self.cmbCategories.DropDownStyle = ComboBoxStyle.DropDownList
        self.cmbCategories.SelectedIndexChanged += self.on_category_changed
        self.Controls.Add(self.cmbCategories)

        # Parameters column
        self.lblParam = Label(Text="Step 2: Parameters", Location=Point(330, 10), Size=Size(300, 20))
        self.Controls.Add(self.lblParam)

        self.txtParamFilter = TextBox(Location=Point(330, 35), Width=300)
        self.txtParamFilter.TextChanged += self.on_param_search
        self.Controls.Add(self.txtParamFilter)

        self.checkedParams = CheckedListBox(Location=Point(330, 65), Size=Size(300, 420))
        self.checkedParams.CheckOnClick = True
        self.checkedParams.ItemCheck += self.on_param_item_check
        self.Controls.Add(self.checkedParams)

        # Values column
        self.lblValues = Label(Text="Step 3: Values", Location=Point(650, 10), Size=Size(300, 20))
        self.Controls.Add(self.lblValues)

        self.txtValueFilter = TextBox(Location=Point(650, 35), Width=300)
        self.txtValueFilter.TextChanged += self.on_value_search
        self.Controls.Add(self.txtValueFilter)

        self.listValues = ListBox(Location=Point(650, 65), Size=Size(300, 420))
        self.listValues.SelectionMode = SelectionMode.MultiExtended
        self.Controls.Add(self.listValues)

        # Buttons
        self.btnSelect = Button(Text="Select", Location=Point(760, 500), Size=Size(90, 30))
        self.btnSelect.Click += self.on_select
        self.Controls.Add(self.btnSelect)

        self.btnCancel = Button(Text="Cancel", Location=Point(860, 500), Size=Size(90, 30))
        self.btnCancel.Click += self.on_cancel
        self.Controls.Add(self.btnCancel)

        # status label
        self.lblStatus = Label(Text="", Location=Point(12, 500), Size=Size(720, 30))
        self.Controls.Add(self.lblStatus)

        # Internal caches
        self.categories = []           # list of dicts: {name, id, elements, params_map}
        self.cat_lookup = {}           # name -> dict
        self.current_category = None
        self.current_filtered_params = []  # list of (display, pname)
        self._checked_param_names = []     # currently checked param names
        self.cached = False

        # Start caching synchronously (single-threaded) with pyrevit ProgressBar
        self.cache_all_elements()

    # ---------------- Caching ----------------
    def cache_all_elements(self):
        try:
            self.categories = []
            self.cat_lookup = {}
            cats = [c for c in doc.Settings.Categories]
            model_cats = [c for c in cats if c.CategoryType.ToString() == "Model"]
            total = len(model_cats)

            with forms.ProgressBar(title="Caching elements for QSelect...", cancellable=True, step=1) as pb:
                for idx, c in enumerate(sorted(model_cats, key=lambda x: x.Name)):
                    if pb.cancelled:
                        forms.alert("Caching cancelled by user.")
                        return
                    try:
                        # skip excluded categories
                        get_elementid_value = get_elementid_value_func()
                        if get_elementid_value(c.Id) in EXCLUDED_CAT_IDS:
                            pb.update_progress(idx + 1, total)
                            continue

                        cat_name = c.Name
                        els = FilteredElementCollector(doc).WhereElementIsNotElementType().OfCategoryId(c.Id).ToElements()
                        params_map = {}
                        for e in els:
                            try:
                                for p in e.Parameters:
                                    pname = p.Definition.Name
                                    if pname not in params_map:
                                        params_map[pname] = {}
                                    val = safe_get_param_value(p) or "None"
                                    params_map[pname].setdefault(val, []).append(e.Id)
                            except Exception:
                                # skip problematic element
                                continue

                        cat_info = {"name": cat_name, "id": c.Id, "elements": els, "params_map": params_map}
                        self.categories.append(cat_info)
                        self.cat_lookup[cat_name] = cat_info
                    except Exception:
                        traceback.print_exc()
                    pb.update_progress(idx + 1, total)

            # populate category combobox
            names = [c["name"] for c in self.categories]
            self.cmbCategories.Items.Clear()
            for n in names:
                self.cmbCategories.Items.Add(n)
            if len(names) > 0:
                self.cmbCategories.SelectedIndex = 0
            self.cached = True
            self.lblStatus.Text = "Caching complete. Categories: {}".format(len(names))
        except Exception as ex:
            traceback.print_exc()
            forms.alert("Error during caching: {}".format(str(ex)))

    # ---------------- UI handlers ----------------
    def on_cat_search(self, sender, args):
        txt = (self.txtCatFilter.Text or "").strip().lower()
        sel_index = self.cmbCategories.SelectedIndex
        current = None
        if sel_index >= 0 and sel_index < self.cmbCategories.Items.Count:
            current = self.cmbCategories.Items[sel_index]
        self.cmbCategories.Items.Clear()
        for c in self.categories:
            if txt == "" or txt in c["name"].lower():
                self.cmbCategories.Items.Add(c["name"])
        # try to restore selection if possible
        if current and current in list(self.cmbCategories.Items):
            self.cmbCategories.SelectedItem = current
        elif self.cmbCategories.Items.Count > 0:
            self.cmbCategories.SelectedIndex = 0

    def on_category_changed(self, sender, args):
        try:
            sel = self.cmbCategories.SelectedItem
            if not sel:
                return
            self.current_category = self.cat_lookup.get(sel)
            if self.current_category is None:
                return
            self.populate_parameters()
            self.populate_values(clear=True)
            self.lblStatus.Text = "Category: {} | Elements: {}".format(sel, len(self.current_category["elements"]))
        except Exception:
            traceback.print_exc()

    def populate_parameters(self):
        # rebuild parameter list for current category
        try:
            self.checkedParams.ItemCheck -= self.on_param_item_check
        except Exception:
            pass
        try:
            self.checkedParams.Items.Clear()
            self.current_filtered_params = []
            if not self.current_category:
                return
            params_map = self.current_category["params_map"]
            ftxt = (self.txtParamFilter.Text or "").strip().lower()
            for pname in sorted(params_map.keys()):
                if ftxt and ftxt not in pname.lower():
                    continue
                cnt = sum(len(v) for v in params_map[pname].values())
                display = "{} ({})".format(pname, cnt)
                self.checkedParams.Items.Add(display, False)
                self.current_filtered_params.append((display, pname))
        finally:
            self.checkedParams.ItemCheck += self.on_param_item_check

    def on_param_search(self, sender, args):
        # preserve checks by name
        checked_names = set(self._checked_param_names or [])
        self.populate_parameters()
        # restore checked states
        for i in range(self.checkedParams.Items.Count):
            disp = self.checkedParams.Items[i]
            for disp_name, pname in self.current_filtered_params:
                if disp_name == disp and pname in checked_names:
                    self.checkedParams.SetItemChecked(i, True)
                    break

    def on_param_item_check(self, sender, e):
        # ItemCheck occurs before change is applied; compute final checked names
        try:
            checked_names = []
            for i in range(self.checkedParams.Items.Count):
                try:
                    currently = self.checkedParams.GetItemChecked(i)
                except Exception:
                    currently = False
                if i == e.Index:
                    final_checked = (e.NewValue == CheckState.Checked)
                else:
                    final_checked = currently
                if final_checked:
                    disp = self.checkedParams.Items[i]
                    for disp_name, pname in self.current_filtered_params:
                        if disp_name == disp:
                            checked_names.append(pname)
                            break
            self._checked_param_names = checked_names
            self.populate_values()
        except Exception:
            traceback.print_exc()

    def populate_values(self, clear=False):
        try:
            self.listValues.BeginUpdate()
            self.listValues.Items.Clear()
            if clear or not self.current_category:
                self.listValues.EndUpdate()
                return

            # choose params (either from stored checked names or current UI)
            if hasattr(self, "_checked_param_names") and self._checked_param_names is not None:
                param_names = list(self._checked_param_names)
            else:
                param_names = []
                for i in range(self.checkedParams.Items.Count):
                    try:
                        if self.checkedParams.GetItemChecked(i):
                            disp = self.checkedParams.Items[i]
                            for disp_name, pname in self.current_filtered_params:
                                if disp_name == disp:
                                    param_names.append(pname)
                                    break
                    except Exception:
                        continue

            if not param_names:
                self.listValues.EndUpdate()
                return

            params_map = self.current_category["params_map"]
            value_map = {}
            for pname in param_names:
                val_dict = params_map.get(pname, {})
                for val_text, elids in val_dict.items():
                    key = (pname, val_text)
                    value_map[key] = value_map.get(key, 0) + len(elids)

            ftxt = (self.txtValueFilter.Text or "").strip().lower()
            entries = []
            for (pname, val_text), cnt in sorted(value_map.items(), key=lambda x: (x[0][0].lower(), x[0][1].lower())):
                if ftxt and ftxt not in val_text.lower() and ftxt not in pname.lower():
                    continue
                display = "{} : {}  ({})".format(pname, val_text, cnt)
                entries.append((display, pname, val_text, cnt))
            for display, pname, val_text, cnt in entries:
                self.listValues.Items.Add(display)
            self.lblStatus.Text = "Values shown: {} (params: {})".format(len(entries), len(param_names))
        except Exception:
            traceback.print_exc()
        finally:
            try:
                self.listValues.EndUpdate()
            except Exception:
                pass

    def on_value_search(self, sender, args):
        self.populate_values()

    # ---------------- Selection action (OK button) ----------------
    def on_select(self, sender, args):
        try:
            # Get selected value indices
            sel_indices = list(self.listValues.SelectedIndices)
            if not sel_indices:
                forms.alert("No values selected.")
                return

            # Build map: parameter -> selected values
            selected_map = {}
            for idx in sel_indices:
                item = self.listValues.Items[idx]
                # parse "ParameterName : Value  (count)"
                try:
                    left = item.rsplit("  (", 1)[0]
                    pname, val = left.split(" : ", 1)
                    selected_map.setdefault(pname, []).append(val)
                except Exception:
                    continue

            # Collect matched ElementIds
            matched_ids = set()
            params_map = self.current_category.get("params_map", {})
            for pname, vals in selected_map.items():
                val_dict = params_map.get(pname, {})
                for v in vals:
                    elids = val_dict.get(v, [])
                    for eid in elids:
                        if eid is not None:
                            matched_ids.add(eid)

            # Prepare .NET List[ElementId] safely
            from System.Collections.Generic import List
            from Autodesk.Revit.DB import ElementId

            element_ids = List[ElementId]()
            for eid in matched_ids:
                element_ids.Add(eid)

            # Set selection
            if element_ids.Count > 0:
                uidoc.Selection.SetElementIds(element_ids)
                forms.alert("Selected {} elements.".format(element_ids.Count))
            else:
                forms.alert("No matching elements found.")

        except Exception:
            import traceback, sys
            traceback.print_exc()
            forms.alert("Error during selection: {}".format(sys.exc_info()[1]))


    def on_cancel(self, sender, args):
        self.Close()


# ---- Run ----
def main():
    try:
        f = QSelectForm()
        f.ShowDialog()
    except Exception:
        traceback.print_exc()
        forms.alert("Unhandled error: {}".format(sys.exc_info()[1]))


if __name__ == "__main__":
    main()
