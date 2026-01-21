# -*- coding: utf-8 -*-
__doc__ = "QSelect - Splasher-style fast selector (Categories -> Parameters -> Values) - single-threaded (view-based, lazy values)"
import os
import sys
import traceback
import clr
import System

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
from Autodesk.Revit.DB import BuiltInParameter
from System.Collections.Generic import List
from Autodesk.Revit.DB import ElementId
from pyrevit.compat import get_elementid_value_func

##############################################################################################
# TELEMETRY IMPORTS #
##############################################################################################
# Only works IF specified TELEMETRY_JSON path exists within %AppData%\pyRevit\Extensions\BIMTools.extension\lib\telemetry_auto.py"
# Records tool usage by date & revit version
import os, sys

# Add lib folder for telemetry_auto
lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'lib'))
if lib_path not in sys.path:
    sys.path.append(lib_path)

import telemetry_auto

tool_name = os.path.basename(os.path.dirname(__file__)) 
TOOL_NAME = tool_name.replace(".pushbutton", "")
telemetry_auto.log_tool_usage(TOOL_NAME)
##############################################################################################

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
        # categories: list of dicts:
        # { name: str, id: ElementId, param_names: [str], values_cache: {pname: {val_text: [ElementId, ...]}} }
        self.categories = []
        self.cat_lookup = {}
        self.current_category = None
        self.current_filtered_params = []  # list of (display, pname)
        self._checked_param_names = []     # currently checked param names
        self.cached = False

        # Start caching categories+param-names synchronously (single-threaded) with pyrevit ProgressBar
        self.cache_categories_paramnames_in_view()

    # ---------------- Helper: collect parameter names from a sample element ----------------
    def _collect_param_names_from_element(self, element):
        """
        Given a Revit element, return a set of parameter names that includes:
         - parameter.Definition.Name for element.Parameters
         - parameter.Definition.Name for element.get_Parameter(BuiltInParameter)
        This is used only on ONE sample element per category (very fast).
        """
        names = set()
        if element is None:
            return names

        # 1) regular parameter collection
        try:
            for p in element.Parameters:
                try:
                    pname = p.Definition.Name
                    if pname:
                        names.add(pname)
                except Exception:
                    continue
        except Exception:
            pass

        # 2) built-in parameters (check which built-ins return a parameter for this element)
        try:
            for bip in System.Enum.GetValues(BuiltInParameter):
                try:
                    p = element.get_Parameter(bip)
                    if p is None:
                        continue
                    try:
                        pname = p.Definition.Name
                        if pname:
                            names.add(pname)
                    except Exception:
                        continue
                except Exception:
                    # some BuiltInParameter values may raise on certain element types; ignore
                    continue
        except Exception:
            pass

        return names

    # ---------------- Caching (view-based, parameter names only, NO ELEMENT SCAN except one sample element) ----------------
    def cache_categories_paramnames_in_view(self):
        """
        Cache categories visible in the active view and parameter *names* for those categories.
        THIS FUNCTION DOES NOT SCAN ELEMENTS OR READ PARAMETER VALUES EXCEPT FOR A SINGLE SAMPLE ELEMENT PER CATEGORY.
        """
        try:
            self.categories = []
            self.cat_lookup = {}
            cats = [c for c in doc.Settings.Categories]
            model_cats = [c for c in cats if c.CategoryType.ToString() == "Model"]
            total = len(model_cats)

            # attempt to get active view id so we can filter which categories are actually present in view
            active_view_id = None
            try:
                active_view_id = uidoc.ActiveView.Id
            except Exception:
                active_view_id = None

            get_elementid_value = get_elementid_value_func()

            # Build a set of categories that actually have elements in the active view (fast check using FilteredElementCollector.GetElementCount)
            categories_in_view = set()
            try:
                for c in model_cats:
                    try:
                        if get_elementid_value(c.Id) in EXCLUDED_CAT_IDS:
                            continue
                        # quick count to see if this category exists in view (0 => ignore)
                        if active_view_id:
                            collector = FilteredElementCollector(doc, active_view_id).WhereElementIsNotElementType().OfCategoryId(c.Id)
                        else:
                            collector = FilteredElementCollector(doc).WhereElementIsNotElementType().OfCategoryId(c.Id)
                        try:
                            count = collector.GetElementCount()
                        except Exception:
                            # fallback - do not call ToElementIds() for speed unless necessary
                            count = len(list(collector.ToElementIds()))
                        if count > 0:
                            categories_in_view.add(c.Id.IntegerValue)
                    except Exception:
                        continue
            except Exception:
                # if anything goes wrong here, fallback to assuming all model categories are in view
                categories_in_view = set([c.Id.IntegerValue for c in model_cats])

            # Gather project-level parameter definitions and their CategorySet from the ParameterBindings (fast)
            param_bindings_map = {}  # def.Name -> set of category integer ids
            try:
                it = doc.ParameterBindings.ForwardIterator()
                it.Reset()
                while it.MoveNext():
                    try:
                        definition = it.Key
                        binding = it.Current
                        # definition can be a FamilyParameter or ExternalDefinition or InternalDefinition
                        dname = None
                        try:
                            dname = definition.Name
                        except Exception:
                            try:
                                dname = definition.Definition.Name
                            except Exception:
                                dname = None
                        if not dname:
                            continue

                        # binding may be InstanceBinding or TypeBinding (both expose Categories via CategorySet)
                        catset = None
                        try:
                            # some bindings expose .Categories
                            catset = binding.Categories
                        except Exception:
                            # some older bindings may expose CategorySet via other means - skip if not available
                            catset = None

                        if catset:
                            # collect integer ids of categories bound for this parameter
                            bound_cats = set()
                            try:
                                for cat in catset:
                                    try:
                                        bound_cats.add(cat.Id.IntegerValue)
                                    except Exception:
                                        continue
                            except Exception:
                                # catset may not be directly iterable in IronPython; try alternative
                                try:
                                    enum_it = catset.ForwardIterator()
                                    enum_it.Reset()
                                    while enum_it.MoveNext():
                                        ct = enum_it.Current
                                        try:
                                            bound_cats.add(ct.Id.IntegerValue)
                                        except Exception:
                                            continue
                                except Exception:
                                    pass
                            param_bindings_map.setdefault(dname, set()).update(bound_cats)
                    except Exception:
                        continue
            except Exception:
                # if something fails iterating bindings, leave map empty (we'll still show categories)
                param_bindings_map = {}

            with forms.ProgressBar(title="Caching categories & parameter names (view)...", cancellable=True, step=1) as pb:
                for idx, c in enumerate(sorted(model_cats, key=lambda x: x.Name)):
                    if pb.cancelled:
                        forms.alert("Caching cancelled by user.")
                        return
                    try:
                        # skip excluded categories
                        if get_elementid_value(c.Id) in EXCLUDED_CAT_IDS:
                            pb.update_progress(idx + 1, total)
                            continue

                        # skip categories not present in the view (fast)
                        if c.Id.IntegerValue not in categories_in_view:
                            pb.update_progress(idx + 1, total)
                            continue

                        # Build parameter names list using the parameter bindings map:
                        param_names = set()
                        # Add any parameter definitions bound to this category (from ParameterBindings)
                        for pname, bound_cats in param_bindings_map.items():
                            try:
                                if c.Id.IntegerValue in bound_cats:
                                    param_names.add(pname)
                            except Exception:
                                continue

                        # As a minimal enhancement, include a few well-known built-in parameter names that are common across many categories
                        common_builtins = [
                            "Comments", "Mark", "Type Name", "Family", "Type Comments", "Level"
                        ]
                        for bn in common_builtins:
                            param_names.add(bn)

                        # --- SAMPLE ONE ELEMENT from this category (very fast) to capture parameters exposed only via element or BuiltInParameter ---
                        try:
                            # Try to get a single representative element quickly
                            sample_elem = None
                            if active_view_id:
                                collector = FilteredElementCollector(doc, active_view_id).WhereElementIsNotElementType().OfCategoryId(c.Id)
                            else:
                                collector = FilteredElementCollector(doc).WhereElementIsNotElementType().OfCategoryId(c.Id)
                            try:
                                # Try to use FirstElement (fast)
                                sample_elem = collector.FirstElement()
                            except Exception:
                                # fallback - try ToElements and take first
                                try:
                                    elems = collector.ToElements()
                                    if elems:
                                        sample_elem = elems[0]
                                except Exception:
                                    try:
                                        el_ids = list(collector.ToElementIds())
                                        if el_ids:
                                            sample_elem = doc.GetElement(el_ids[0])
                                    except Exception:
                                        sample_elem = None

                            if sample_elem is not None:
                                try:
                                    names_from_elem = self._collect_param_names_from_element(sample_elem)
                                    for pn in names_from_elem:
                                        param_names.add(pn)
                                except Exception:
                                    # ignore any errors from sample extraction
                                    pass
                        except Exception:
                            pass

                        cat_name = c.Name
                        cat_info = {
                            "name": cat_name,
                            "id": c.Id,
                            "param_names": sorted(param_names),
                            "values_cache": {}  # lazy cache: pname -> { val_text -> [ElementId, ...] }
                        }
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
            self.lblStatus.Text = "Categories cached (view, defs + sample elem): {}".format(len(names))
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
            # Populate parameter names (we cached names only)
            self.populate_parameters()
            # Clear values until a parameter is checked
            self.populate_values(clear=True)
            # Update status with an approximate element count in view for this category (fast)
            try:
                active_view_id = uidoc.ActiveView.Id
                if active_view_id:
                    collector = FilteredElementCollector(doc, active_view_id).WhereElementIsNotElementType().OfCategoryId(self.current_category["id"])
                else:
                    collector = FilteredElementCollector(doc).WhereElementIsNotElementType().OfCategoryId(self.current_category["id"])
                try:
                    count = collector.GetElementCount()
                except Exception:
                    count = len(list(collector.ToElementIds()))
                self.lblStatus.Text = "Category: {} | Elements in view: {}".format(sel, count)
            except Exception:
                self.lblStatus.Text = "Category: {} selected".format(sel)
        except Exception:
            traceback.print_exc()

    def populate_parameters(self):
        # rebuild parameter list for current category using cached param_names
        try:
            self.checkedParams.ItemCheck -= self.on_param_item_check
        except Exception:
            pass
        try:
            self.checkedParams.Items.Clear()
            self.current_filtered_params = []
            if not self.current_category:
                return
            pnames = self.current_category.get("param_names", [])
            ftxt = (self.txtParamFilter.Text or "").strip().lower()
            for pname in sorted(pnames):
                if ftxt and ftxt not in pname.lower():
                    continue
                # we don't have per-param counts yet (values not loaded) - show name only
                display = "{}".format(pname)
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
            # Populate values: this will lazily read element parameter values as needed
            self.populate_values()
        except Exception:
            traceback.print_exc()

    def _ensure_values_for_param(self, pname):
        """
        Ensure that current_category['values_cache'][pname] exists.
        If not, scan elements in active view for the category, read pname and build {val_text: [ElementId,...]}
        (This is the first place where element iteration happens - it is lazy and per-parameter.)
        """
        if not self.current_category:
            return {}
        cache = self.current_category.setdefault("values_cache", {})
        if pname in cache:
            return cache[pname]

        val_dict = {}
        try:
            # collect elements for this category in active view
            try:
                active_view_id = uidoc.ActiveView.Id
            except Exception:
                active_view_id = None

            if active_view_id:
                collector = FilteredElementCollector(doc, active_view_id).WhereElementIsNotElementType().OfCategoryId(self.current_category["id"])
            else:
                collector = FilteredElementCollector(doc).WhereElementIsNotElementType().OfCategoryId(self.current_category["id"])

            # iterate elements and read the parameter (use LookupParameter for speed)
            try:
                elements = collector.ToElements()
            except Exception:
                # fallback: get element ids then GetElement
                elids = list(collector.ToElementIds())
                elements = [doc.GetElement(x) for x in elids]

            for e in elements:
                try:
                    if e is None:
                        continue
                    p = e.LookupParameter(pname)
                    if p is None:
                        # some params may be different (shared vs instance); try scanning all
                        found = None
                        for pp in e.Parameters:
                            try:
                                if pp.Definition and pp.Definition.Name == pname:
                                    found = pp
                                    break
                            except Exception:
                                continue
                        p = found
                    val_text = safe_get_param_value(p) if p is not None else "None"
                    val_text = val_text or "None"
                    val_dict.setdefault(val_text, []).append(e.Id)
                except Exception:
                    continue
        except Exception:
            traceback.print_exc()

        cache[pname] = val_dict
        return val_dict

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

            # Aggregate values across selected params. For each param, ensure its value map is prepared.
            aggregated_value_map = {}  # key=(pname,val_text) -> (count, [ElementId...])
            for pname in param_names:
                val_dict = self._ensure_values_for_param(pname) or {}
                for val_text, elids in val_dict.items():
                    key = (pname, val_text)
                    if key not in aggregated_value_map:
                        aggregated_value_map[key] = [0, []]
                    aggregated_value_map[key][0] += len(elids)
                    aggregated_value_map[key][1].extend(elids)

            ftxt = (self.txtValueFilter.Text or "").strip().lower()
            entries = []
            # sort by parameter then value
            for (pname, val_text), (cnt, elids) in sorted(aggregated_value_map.items(), key=lambda x: (x[0][0].lower(), x[0][1].lower())):
                if ftxt and ftxt not in val_text.lower() and ftxt not in pname.lower():
                    continue
                display = "{} : {}  ({})".format(pname, val_text, cnt)
                entries.append((display, pname, val_text, cnt, elids))
            for display, pname, val_text, cnt, elids in entries:
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

            # Collect matched ElementIds using cached per-param value maps (built on demand)
            matched_ids = set()
            for pname, vals in selected_map.items():
                val_dict = self.current_category.get("values_cache", {}).get(pname)
                if val_dict is None:
                    val_dict = self._ensure_values_for_param(pname)
                for v in vals:
                    elids = val_dict.get(v, [])
                    for eid in elids:
                        if eid is not None:
                            matched_ids.add(eid)

            # Prepare .NET List[ElementId] safely
            element_ids = List[ElementId]()
            for eid in matched_ids:
                try:
                    # ensure it's an ElementId
                    if isinstance(eid, ElementId):
                        element_ids.Add(eid)
                    else:
                        element_ids.Add(ElementId(eid))
                except Exception:
                    try:
                        element_ids.Add(ElementId(int(eid)))
                    except Exception:
                        continue

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
