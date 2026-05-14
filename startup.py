# -*- coding: utf-8 -*-
# CDY-ProTools startup.py (refactored)
# - Hides Developer panel and pyRevit tab until unlocked
# - Registers CDY Tools dockable panel (5 tabs + Favourites)

# =============================================================================
# IMPORTS
# =============================================================================

import clr
import os
import os.path as op
import json
import sys
import imp

clr.AddReference("AdWindows")
clr.AddReference("PresentationFramework")
clr.AddReference("PresentationCore")
clr.AddReference("WindowsBase")

import System
import Autodesk.Windows as AdWindows
import Autodesk.Revit.DB as DB

from System import EventHandler, Action
from System.Windows import Thickness, FontWeights, TextWrapping
from System.Windows import HorizontalAlignment as System_HAlign
from System.Windows.Controls import (
    StackPanel, Button, TextBlock,
    TabControl, TabItem, ScrollViewer,
    Separator, Grid, DockPanel
)
from System.Windows.Controls import ScrollBarVisibility, Dock
from System.Windows.Media import Brushes, SolidColorBrush
from System.Windows import Media

from Autodesk.Revit.UI import IExternalEventHandler, ExternalEvent
from Autodesk.Revit.UI.Events import IdlingEventArgs
from Autodesk.Revit.DB import ElementId, BuiltInParameter
from Autodesk.Revit.UI.Selection import ObjectType

from pyrevit import forms, HOST_APP


# =============================================================================
# SECTION 1 - HIDE DEVELOPER / PYREVIT UNTIL UNLOCKED
# =============================================================================

TAB_NAME       = "CDY-ProTools"
DEV_PANEL_NAME = "Developer"
PYRVT_TAB_NAME = "pyRevit"
UNLOCK_FILE    = os.path.join(os.getenv("APPDATA"), "CDY-ProTools", "dev_unlock.json")


def hide_panels():
    ribbon = AdWindows.ComponentManager.Ribbon
    if not ribbon:
        return
    visible = False
    if os.path.exists(UNLOCK_FILE):
        try:
            with open(UNLOCK_FILE, "r") as f:
                data = json.load(f)
            if data.get("unlocked", False):
                visible = True
        except:
            visible = False
    for tab in ribbon.Tabs:
        if tab.Title == TAB_NAME:
            for panel in tab.Panels:
                if panel.Source and panel.Source.Title == DEV_PANEL_NAME:
                    panel.IsVisible = visible
                    panel.IsEnabled = visible
        if tab.Title == PYRVT_TAB_NAME:
            tab.IsVisible = visible


def on_idling(sender, args):
    try:
        hide_panels()
    except:
        pass
    finally:
        HOST_APP.uiapp.Idling -= EventHandler[IdlingEventArgs](on_idling)


HOST_APP.uiapp.Idling += EventHandler[IdlingEventArgs](on_idling)


# =============================================================================
# SECTION 2 - SCRIPT PATH REGISTRY (was 3)
# =============================================================================

_bimtools_tab = op.join(
    os.getenv("APPDATA"),
    "pyRevit", "Extensions", "BIMTools.extension", "CDY-ProTools.tab"
)


def _script(relative_path):
    return op.join(_bimtools_tab, relative_path)


SCRIPTS = {
    # -- Views ----------------------------------------------------------------
    "open_host_sheet":       _script(r"General.panel\Navigation.pulldown\Find Sheet.pushbutton\script.py"),
    "open_view_on_sheet":    _script(r"General.panel\Navigation.pulldown\Find View.pushbutton\script.py"),
    "open_parent_view":      _script(r"General.panel\Navigation.pulldown\Find ParentView.pushbutton\script.py"),
    # -- Modelling ------------------------------------------------------------
    "pick_2d":               _script(r"Drawing Tools.panel\Drafting.pulldown\Pick Detail Elements.pushbuttonscript.py"),
    "pick_3d":               _script(r"Drawing Tools.panel\Drafting.pulldown\Pick Model Elements.pushbutton\script.py"),
    "pick_grouped":          _script(r"Drawing Tools.panel\Drafting.pulldown\Pick Grouped Elements.pushbutton\script.py"),
    "flip_grid_bubbles":     _script(r"Drawing Tools.panel\Drafting.pulldown\Flip Grids.pushbutton\scriptAlternate.py"),
    "flip_level_bubbles":    _script(r"Drawing Tools.panel\Drafting.pulldown\Flip Levels.pushbutton\script.py"),
    # -- Dimensions -----------------------------------------------------------
    "dim_gridlines":         _script(r"Drawing Tools.panel\Drafting.pulldown\Dim Grids.pushbutton\script.py"),
    "dim_levels":            _script(r"Drawing Tools.panel\Drafting.pulldown\Dim Levls.pushbutton\script.py"),
    # -- Tagging --------------------------------------------------------------
    "select_untagged":       _script(r"Quality Assurance.panel\Model Check.pulldown\Select Untagged.pushbutton\script.py"),
    "Highlight_selected":    _script(r"DockableWindowExclusives\Highlight Selected.pushbutton\script.py"),
    "Reset_all_overrides":   _script(r"DockableWindowExclusives\Reset All Overrides.pushbutton\script.py"),
    "Reset_sel_overrides":   _script(r"DockableWindowExclusives\Reset Selected Overrides.pushbutton\script.py"),
    # -- DWG / Files ----------------------------------------------------------
    "open_dwg_autocad":      _script(r"Drawing Tools.panel\AutoCAD.pulldown\Open DWG.pushbutton\script.py"),
    "reload_dwg":            _script(r"Drawing Tools.panel\AutoCAD.pulldown\Reload DWG.pushbutton\script.py"),
    "greyscale_dwg":         _script(r"Drawing Tools.panel\AutoCAD.pulldown\Grey Scale DWG.pushbutton\script.py"),
    "revert_greyscale_dwg":  _script(r"Drawing Tools.panel\AutoCAD.pulldown\Revert Grey Scale DWG.pushbutton\script.py"),
    "open_bim360":           _script(r"General.panel\Navigation.pulldown\Forma Location.pushbutton\script.py"),
    "open_central_location": _script(r"General.panel\Navigation.pulldown\CentralModelLocation.pushbutton\script.py"),
    "open_local_location":   _script(r"General.panel\Navigation.pulldown\ModelLocation.pushbutton\script.py"),
}

TOOL_LABELS = {
    "open_host_sheet":       "Open Host Sheet",
    "open_view_on_sheet":    "Open View Selected on Sheet",
    "open_parent_view":      "Open Parent / Primary View",
    "pick_2d":               "Pick 2D Elements",
    "pick_3d":               "Pick 3D Elements",
    "pick_grouped":          "Pick Grouped Elements",
    "flip_grid_bubbles":     "Flip Grid Bubbles",
    "flip_level_bubbles":    "Flip Level Bubbles",
    "dim_gridlines":         "Dimension Selected Gridlines",
    "dim_levels":            "Dimension Selected Levels",
    "select_untagged":       "Select Untagged in Active View",
    "Highlight_selected":    "Highlight Selected",
    "Reset_all_overrides":   "Reset All Overrides",
    "Reset_sel_overrides":   "Reset Selected Overrides",
    "open_dwg_autocad":      "Open Selected DWG in AutoCAD",
    "reload_dwg":            "Reload Selected DWG",
    "greyscale_dwg":         "Grey Scale Selected DWG",
    "revert_greyscale_dwg":  "Revert Grey Scale",
    "open_bim360":           "Open BIM360 / ACC",
    "open_central_location": "Open Central Model Location",
    "open_local_location":   "Open Local File Location",
}


# =============================================================================
# HIGHLIGHT COLOUR STORE
# Shared between the colour picker button and the highlight script.
# Defaults to green (0, 200, 0).  The script reads CDY_HIGHLIGHT_COLOR.
# =============================================================================

CDY_HIGHLIGHT_COLOR = (0, 200, 0)   # (R, G, B) tuple, mutable at runtime

# Keeps references to modeless WinForms windows alive after _exec_script returns,
# preventing them from being garbage collected (e.g. QSelect).
_MODELESS_WINDOWS = {}

# =============================================================================
# SECTION 3 - SCRIPT EXECUTION
# =============================================================================

def _set_status(tb, message, error=False):
    tb.Text       = message
    tb.Foreground = Brushes.Crimson if error else Brushes.SeaGreen


class _ExecParams(object):
    def __init__(self, path):
        self.command_name           = op.splitext(op.basename(op.dirname(path)))[0]
        self.command_path           = path
        self.command_extension_name = "CDY-ProTools"
        self.result_dict            = {}
        self.config_file            = None
        self.needs_clean_engine     = False
        self.use_persistent_engine  = False
        self.refreshed_engine       = False
        self.first_new_engine       = False


def _inject_extension_paths(script_path):
    """Inject the extension lib/ and tab/ root into sys.path so that
    scripts using relative imports (e.g. Snippets._context_manager) work
    when executed outside of pyRevit's normal loader."""
    # Walk up from the script folder to find the .extension root
    node = op.dirname(script_path)
    ext_root = None
    while node:
        parent = op.dirname(node)
        if op.basename(node).lower().endswith(".extension"):
            ext_root = node
            break
        if parent == node:
            break
        node = parent
    if ext_root:
        for candidate in [
            ext_root,
            op.join(ext_root, "lib"),
            op.join(ext_root, "bin"),
        ]:
            if op.exists(candidate) and candidate not in sys.path:
                sys.path.insert(0, candidate)
    # Also add the script's own .tab root so intra-tab imports work
    node = op.dirname(script_path)
    while node:
        parent = op.dirname(node)
        if op.basename(node).lower().endswith(".tab"):
            if node not in sys.path:
                sys.path.insert(0, node)
            break
        if parent == node:
            break
        node = parent


def _exec_script(path, uiapp):
    if not path:
        return "No path provided."
    if not op.exists(path):
        return "Script not found:\n{}".format(path)
    try:
        script_dir = op.dirname(path)
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)
        _inject_extension_paths(path)

        uidoc = uiapp.ActiveUIDocument if uiapp else None
        doc   = uidoc.Document if uidoc else None

        exec_params         = _ExecParams(path)
        # Use full path hash + id to guarantee uniqueness and avoid module cache collisions
        mod_name            = "cdy_script_{:x}_{:x}".format(abs(hash(path)), id(exec_params) & 0xFFFF)
        mod                 = imp.new_module(mod_name)
        mod.__file__        = op.dirname(path)  # dir not file — pyRevit resolves XAML relative to this
        mod.__revit__       = uiapp
        mod.__uidoc__       = uidoc
        mod.__doc__         = doc
        mod.EXEC_PARAMS     = exec_params
        mod.__commandname__ = exec_params.command_name
        mod.__commandpath__ = op.dirname(path)  # dir not file — pyRevit resolves XAML relative to this

        try:
            from pyrevit import revit as _pvrevit
            mod.revit = _pvrevit
        except Exception:
            pass

        # Use a private ScriptProxy — never mutate the shared pyRevit script module
        # as that corrupts EXEC_PARAMS for subsequently launched pyRevit tools
        class _ScriptProxy(object):
            def exit(self):
                raise SystemExit
            def get_config(self, section=None):
                class _Cfg(object):
                    def __getattr__(self, name):
                        return None
                    def __setattr__(self, name, val):
                        pass
                    def save_changes(self):
                        pass
                return _Cfg()
            def get_logger(self):
                import logging
                return logging.getLogger(exec_params.command_name)
            def get_output(self):
                return None
        mod.script = _ScriptProxy()

        sys.modules[mod_name] = mod

        with open(path, "r") as f:
            source = f.read()
        mod.__dict__["__name__"] = "__main__"
        exec(compile(source, path, "exec"), mod.__dict__)
        for _wvar in ("_qselect_form", "window", "_window", "form", "_form"):
            _wobj = mod.__dict__.get(_wvar)
            if _wobj is not None:
                _MODELESS_WINDOWS[path + ":" + _wvar] = _wobj
        sys.modules.pop(mod_name, None)
        return None
    except SystemExit:
        sys.modules.pop(mod_name, None)
        return None
    except Exception:
        sys.modules.pop(mod_name, None)
        import traceback
        return traceback.format_exc()


class ScriptLaunchHandler(IExternalEventHandler):
    def __init__(self, script_key):
        self.script_key = script_key
        self.status     = None

    def Execute(self, uiapp):
        from Autodesk.Revit.UI import RevitCommandId
        path = SCRIPTS.get(self.script_key)
        if not path:
            return

        # Try PostCommand first
        uid = _build_uid_from_path(path)
        if uid:
            try:
                cmd_id = RevitCommandId.LookupCommandId(uid)
                if cmd_id and uiapp.CanPostCommand(cmd_id):
                    uiapp.PostCommand(cmd_id)
                    return
            except Exception:
                pass

        # Fall back to direct exec — safe now DocReg uses __file__ not script.get_bundle_file
        err = _exec_script(path, uiapp)
        if self.status and err:
            _set_status(self.status, err, error=True)

    def GetName(self):
        return "CDY {}".format(self.script_key)


# =============================================================================
# SECTION 4 - FAVOURITES PERSISTENCE
# =============================================================================

_FAV_FILE = os.path.join(os.getenv("APPDATA"), "pyRevit", "CDY-ProTools-favourites.json")

_SCRIPT_CMD_MAP = {}



def _build_uid_from_path(script_path):
    """
    Build the correct Revit command UID from a script path, including any
    .pulldown nesting between .panel and .pushbutton.

    Flat:   CustomCtrl_%CustomCtrl_%<tab>%<panel>%<btn>
    Nested: CustomCtrl_%CustomCtrl_%<tab>%<panel>%CustomCtrl_%<pulldown>%<btn>

    Uses string splitting on both backslash and / so it works regardless of which
    os.path functions are available (important when running inside Revit on
    Windows where op.dirname may behave unexpectedly with iron-python).
    """
    # Normalise to backslash and split into parts, drop the trailing script.py
    parts = script_path.replace("/", "\\").split("\\")
    if parts and parts[-1].lower() == "script.py":
        parts = parts[:-1]

    btn_name   = ""
    pulldowns  = []   # collected innermost-first as we walk backwards
    panel_name = ""
    tab_name   = ""

    for part in reversed(parts):
        if part.endswith(".pushbutton") and not btn_name:
            btn_name = part[:-len(".pushbutton")]
        elif part.endswith(".pulldown"):
            pulldowns.append(part[:-len(".pulldown")])
        elif part.endswith(".panel") and not panel_name:
            panel_name = part[:-len(".panel")]
        elif part.endswith(".tab"):
            tab_name = part[:-len(".tab")]
            break

    if not (tab_name and panel_name and btn_name):
        return None

    # pulldowns were innermost-first; reverse so outermost comes first in UID
    pulldowns.reverse()
    pulldown_seg = "".join("CustomCtrl_%{}%".format(pd) for pd in pulldowns)
    uid = "CustomCtrl_%CustomCtrl_%{}%{}%{}{}".format(
        tab_name, panel_name, pulldown_seg, btn_name)
    return uid

def _build_command_registry():
    global _SCRIPT_CMD_MAP

    try:
        from pyrevit import extensions as exts
        for ext in exts.get_installed_ui_extensions():
            try:
                for cmd in ext.get_all_commands():
                    try:
                        script_path = op.normcase(op.normpath(cmd.script))
                        _SCRIPT_CMD_MAP[script_path] = cmd.unique_id
                    except Exception:
                        pass
            except Exception:
                pass
        print("CDY: command registry (API): {} entries".format(len(_SCRIPT_CMD_MAP)))
    except Exception as ex:
        print("CDY: command registry API failed: {}".format(ex))

    try:
        if op.exists(_bimtools_tab):
            for dirpath, dirnames, filenames in os.walk(_bimtools_tab):
                if "script.py" not in filenames:
                    continue
                if not op.basename(dirpath).endswith(".pushbutton"):
                    continue
                script_path = op.join(dirpath, "script.py")
                key = op.normcase(op.normpath(script_path))
                if key not in _SCRIPT_CMD_MAP:
                    uid = _build_uid_from_path(script_path)
                    if uid:
                        _SCRIPT_CMD_MAP[key] = uid
        print("CDY: command registry (total): {} entries".format(len(_SCRIPT_CMD_MAP)))
    except Exception as ex:
        print("CDY: command registry walk failed: {}".format(ex))


_build_command_registry()


def _get_command_id(script_path):
    try:
        from Autodesk.Revit.UI import RevitCommandId
    except Exception:
        return None, None

    key = op.normcase(op.normpath(script_path))

    unique_id = _SCRIPT_CMD_MAP.get(key)
    if unique_id:
        try:
            cmd_id = RevitCommandId.LookupCommandId(unique_id)
            if cmd_id:
                return cmd_id, unique_id
        except Exception:
            pass
        return None, unique_id

    uid = _build_uid_from_path(script_path)
    if uid:
        _SCRIPT_CMD_MAP[key] = uid
        try:
            cmd_id = RevitCommandId.LookupCommandId(uid)
            if cmd_id:
                return cmd_id, uid
        except Exception:
            pass
        return None, uid

    return None, None


def _heal_path(path):
    if op.exists(path):
        return path
    btn_dir = op.basename(op.dirname(path))
    for dirpath, dirnames, filenames in os.walk(_bimtools_tab):
        if "script.py" in filenames and op.basename(dirpath) == btn_dir:
            return op.join(dirpath, "script.py")
    return path


def _load_favs():
    try:
        if op.exists(_FAV_FILE):
            with open(_FAV_FILE, "r") as f:
                data = json.load(f)
            result  = []
            changed = False
            for item in data:
                if isinstance(item, dict) and "path" in item:
                    item = dict(item)
                    healed = _heal_path(item["path"])
                    if healed != item["path"]:
                        item["path"] = healed
                        changed = True
                    # Always recompute the command_id from path so stale
                    # flat IDs (missing pulldown segments) get corrected.
                    correct_uid = _build_uid_from_path(item["path"])
                    if correct_uid and item.get("command_id") != correct_uid:
                        item["command_id"] = correct_uid
                        changed = True
                    elif not item.get("command_id"):
                        _, uid = _get_command_id(item["path"])
                        if uid:
                            item["command_id"] = uid
                            changed = True
                    result.append(item)
                elif isinstance(item, str) and item in SCRIPTS:
                    result.append({"label": TOOL_LABELS.get(item, item),
                                   "path":  SCRIPTS[item]})
                    changed = True
            if changed:
                _save_favs(result)
            return result
    except Exception:
        pass
    return []


def _save_favs(favs):
    try:
        folder = op.dirname(_FAV_FILE)
        if not op.exists(folder):
            os.makedirs(folder)
        with open(_FAV_FILE, "w") as f:
            json.dump(favs, f, indent=2)
    except Exception:
        pass


def _fav_has_path(path):
    return any(f.get("path") == path for f in _load_favs())


def _fav_add(label, path, command_id=None):
    favs = _load_favs()
    if not any(f.get("path") == path for f in favs):
        entry = {"label": label, "path": path}
        if not command_id:
            _, uid = _get_command_id(path)
            if uid:
                entry["command_id"] = uid
        else:
            entry["command_id"] = command_id
        favs.append(entry)
        _save_favs(favs)
        return True
    return False


def _fav_remove(path):
    _save_favs([f for f in _load_favs() if f.get("path") != path])


def _fav_toggle_key(key):
    path = SCRIPTS.get(key)
    if not path:
        return False
    if _fav_has_path(path):
        _fav_remove(path)
        return False
    _fav_add(TOOL_LABELS.get(key, key), path)
    return True


def _fav_is_key(key):
    path = SCRIPTS.get(key)
    return _fav_has_path(path) if path else False


# =============================================================================
# SECTION 5 - EXTENSION SCRIPT SCANNER (for Browse & Add)
# =============================================================================

def _scan_scripts(root):
    """Walk the extension tab and return pushbutton scripts safe to expose in the
    Browse & Add picker.  Three categories are intentionally excluded:

    - Developer.panel   : internal/debug tools hidden behind the unlock file
    - DockableWindowExclusives : scripts launched only via the dockable panel
                                 itself; they rely on injected context and must
                                 not be double-launched from Favourites
    - bin (any segment) : compiled helpers / support files, not user-facing tools
    """
    # Normalise to forward-slash for consistent substring checks
    _BLOCKED = ("developer.panel", "dockablewindowexclusives", "\\bin\\", "/bin/")

    results = []
    if not op.exists(root):
        return results
    for dirpath, dirnames, filenames in os.walk(root):
        if "script.py" not in filenames:
            continue
        if not op.basename(dirpath).endswith(".pushbutton"):
            continue
        # Normalise path once for all checks
        norm = dirpath.lower().replace("\\", "/")
        if any(blk in norm for blk in ("developer.panel",
                                        "dockablewindowexclusives",
                                        "/bin/")):
            continue
        tool_name = op.basename(dirpath)[:-len(".pushbutton")]
        results.append({"label": tool_name,
                        "path":  op.join(dirpath, "script.py")})
    results.sort(key=lambda x: x["label"].lower())
    return results


# =============================================================================
# SECTION 6 - HIDE LAYER TOGGLE
# =============================================================================

_hide_layer_active = [False]


class HideLayerToggleHandler(IExternalEventHandler):

    def __init__(self):
        self.status     = None
        self.toggle_btn = None

    def _ui(self, fn):
        self.toggle_btn.Dispatcher.Invoke(Action(fn))

    def _set_active(self):
        def _do():
            if self.toggle_btn:
                self.toggle_btn.Background = SolidColorBrush(Media.Color.FromRgb(180, 40, 40))
                self.toggle_btn.Foreground = Brushes.White
                self.toggle_btn.Content    = u"\u25cf Active - Press ESC to Finish"
            if self.status:
                _set_status(self.status, "Click DWG layers to hide. ESC to stop.")
        self._ui(_do)

    def _set_inactive(self, count):
        def _do():
            if self.toggle_btn:
                self.toggle_btn.ClearValue(Button.BackgroundProperty)
                self.toggle_btn.ClearValue(Button.ForegroundProperty)
                self.toggle_btn.Content = "Hide Layer (Toggle)"
            if self.status:
                msg = "Hide mode off - {} layer(s) hidden.".format(count) if count \
                      else "Hide mode off."
                _set_status(self.status, msg)
        self._ui(_do)

    def _update(self, name, total):
        def _do():
            if self.status:
                _set_status(self.status,
                            "Hidden '{}' ({} total). ESC to stop.".format(name, total))
        self._ui(_do)

    def Execute(self, uiapp):
        if _hide_layer_active[0]:
            _hide_layer_active[0] = False
            return

        uidoc = uiapp.ActiveUIDocument
        doc   = uidoc.Document
        _hide_layer_active[0] = True
        count = 0
        seen  = set()
        self._set_active()

        while _hide_layer_active[0]:
            try:
                ref = uidoc.Selection.PickObject(
                    ObjectType.PointOnElement,
                    "Click a DWG layer to hide it  (ESC to finish)")
            except:
                break

            elem        = doc.GetElement(ref.ElementId)
            import_inst = None
            gs_id       = None

            if isinstance(elem, DB.ImportInstance):
                import_inst = elem
                try:
                    gs_id = import_inst.GetGeometryObjectFromReference(ref).GraphicsStyleId
                except:
                    pass
            else:
                parent = elem
                while parent:
                    if isinstance(parent, DB.ImportInstance):
                        import_inst = parent
                        break
                    try:
                        hp     = parent.get_Parameter(BuiltInParameter.HOST_ID_PARAM)
                        parent = doc.GetElement(hp.AsElementId()) if hp else None
                    except:
                        parent = None
                try:
                    gs_id = elem.GraphicsStyleId
                except:
                    pass

            if not import_inst or not gs_id:
                continue
            gs = doc.GetElement(gs_id)
            if not gs:
                continue

            name     = gs.GraphicsStyleCategory.Name
            root_cat = import_inst.Category
            if not root_cat or name in seen:
                continue
            try:
                layer_cat = root_cat.SubCategories.get_Item(name)
            except:
                layer_cat = None
            if not layer_cat:
                continue

            view   = doc.ActiveView
            tid    = view.ViewTemplateId
            target = doc.GetElement(tid) \
                     if tid != DB.ElementId.InvalidElementId else view

            from Autodesk.Revit.DB import Transaction
            with Transaction(doc, "CDY: Hide Layer '{}'".format(name)) as t:
                t.Start()
                try:
                    target.SetCategoryHidden(layer_cat.Id, True)
                    t.Commit()
                    seen.add(name)
                    count += 1
                    self._update(name, count)
                except Exception as e:
                    t.RollBack()
                    def _err(m=str(e)):
                        if self.status:
                            _set_status(self.status,
                                        "Could not hide layer: {}".format(m), error=True)
                    self._ui(_err)

        _hide_layer_active[0] = False
        self._set_inactive(count)

    def GetName(self):
        return "CDY Hide Layer Toggle"


# =============================================================================
# SECTION 6b - FAVOURITES LAUNCH HANDLER
# =============================================================================

class FavLaunchHandler(IExternalEventHandler):
    def __init__(self):
        self.path      = None
        self.cmd_name  = None
        self.label     = ""
        self.status_tb = None

    def _report(self, msg, error=True):
        if self.status_tb:
            def _show(tb=self.status_tb, m=msg, e=error):
                _set_status(tb, m, error=e)
            self.status_tb.Dispatcher.Invoke(Action(_show))

    def Execute(self, uiapp):
        from Autodesk.Revit.UI import RevitCommandId

        # Resolve UID
        uid = self.cmd_name
        if not uid and self.path:
            uid = _build_uid_from_path(self.path)
            if uid:
                self.cmd_name = uid
        if not uid and self.path:
            _, uid = _get_command_id(self.path)
            if uid:
                self.cmd_name = uid

        # Try PostCommand if we have a UID
        if uid:
            try:
                cmd_id = RevitCommandId.LookupCommandId(uid)
                if cmd_id and uiapp.CanPostCommand(cmd_id):
                    uiapp.PostCommand(cmd_id)
                    return
            except Exception:
                pass

        # PostCommand not available (hidden panel buttons can't be PostCommand'd).
        # These are safe to exec directly — they are simple scripts with no XAML/WPFWindow.
        # The DocReg corruption issue is fixed in DocReg itself (uses __file__ not
        # script.get_bundle_file), so _exec_script is safe to use here again.
        if self.path:
            err = _exec_script(self.path, uiapp)
            if err:
                self._report(u"'{}' failed:\n{}".format(self.label, err))
            return

        self._report(u"No path or command ID for '{}'.".format(self.label))

    def GetName(self):
        return "CDY Fav Launch"


_fav_handler = FavLaunchHandler()
_fav_event   = ExternalEvent.Create(_fav_handler)


# =============================================================================
# SECTION 7 - INSTANTIATE HANDLERS & EVENTS
# =============================================================================

from System.Collections.Generic import List as DotNetList


def System_List_ElementId(ids):
    lst = DotNetList[ElementId]()
    for i in ids:
        lst.Add(i)
    return lst


_h_open_sheet   = ScriptLaunchHandler("open_host_sheet");   _e_open_sheet   = ExternalEvent.Create(_h_open_sheet)
_h_open_view    = ScriptLaunchHandler("open_view_on_sheet"); _e_open_view    = ExternalEvent.Create(_h_open_view)
_h_open_parent  = ScriptLaunchHandler("open_parent_view");  _e_open_parent  = ExternalEvent.Create(_h_open_parent)

_h_pick2d       = ScriptLaunchHandler("pick_2d");           _e_pick2d       = ExternalEvent.Create(_h_pick2d)
_h_pick3d       = ScriptLaunchHandler("pick_3d");           _e_pick3d       = ExternalEvent.Create(_h_pick3d)
_h_pick_grouped = ScriptLaunchHandler("pick_grouped");      _e_pick_grouped = ExternalEvent.Create(_h_pick_grouped)
_h_flip_grid    = ScriptLaunchHandler("flip_grid_bubbles"); _e_flip_grid    = ExternalEvent.Create(_h_flip_grid)
_h_flip_level   = ScriptLaunchHandler("flip_level_bubbles");_e_flip_level   = ExternalEvent.Create(_h_flip_level)

_h_dim_grids    = ScriptLaunchHandler("dim_gridlines");     _e_dim_grids    = ExternalEvent.Create(_h_dim_grids)
_h_dim_levels   = ScriptLaunchHandler("dim_levels");        _e_dim_levels   = ExternalEvent.Create(_h_dim_levels)

_h_sel_untagged   = ScriptLaunchHandler("select_untagged");         _e_sel_untagged   = ExternalEvent.Create(_h_sel_untagged)


# Temp file used to pass the chosen colour to the Highlight script
_HIGHLIGHT_COLOR_FILE = os.path.join(os.getenv("APPDATA"), "pyRevit", "CDY-highlight-color.json")

def _write_highlight_color(r, g, b):
    """Write the chosen colour to a temp JSON file for the Highlight script to read."""
    try:
        with open(_HIGHLIGHT_COLOR_FILE, "w") as f:
            json.dump({"r": r, "g": g, "b": b}, f)
    except Exception:
        pass


class HighlightHandler(IExternalEventHandler):
    """Launches the Highlight script, writing colour to temp file first.
    Tries PostCommand first; falls back to _exec_script for hidden-panel buttons
    where CanPostCommand returns False."""
    def __init__(self):
        self.status = None

    def Execute(self, uiapp):
        from Autodesk.Revit.UI import RevitCommandId

        # Write colour to temp file BEFORE launching — script reads it on startup
        r, g, b = CDY_HIGHLIGHT_COLOR
        _write_highlight_color(r, g, b)

        path = SCRIPTS.get("Highlight_selected")
        uid  = _build_uid_from_path(path) if path else None

        # Try PostCommand (works when Developer panel is visible/enabled)
        if uid:
            try:
                cmd_id = RevitCommandId.LookupCommandId(uid)
                if cmd_id and uiapp.CanPostCommand(cmd_id):
                    uiapp.PostCommand(cmd_id)
                    return
            except Exception:
                pass

        # Fallback: execute directly.
        # PostCommand fails when the button lives inside a hidden/disabled panel
        # (CanPostCommand returns False). _exec_script is safe here — the Highlight
        # script has no XAML/WPFWindow that would conflict with DocReg.
        if path:
            err = _exec_script(path, uiapp)
            if err and self.status:
                _set_status(self.status,
                            "Highlight failed:\n{}".format(err), error=True)
            return

        if self.status:
            _set_status(self.status,
                        "Could not launch Highlight (uid: {})".format(uid or "none"),
                        error=True)

    def GetName(self):
        return "CDY Highlight"


def _exec_script_with_globals(path, uiapp, extra_globals):
    """Like _exec_script but merges extra_globals into the module before exec."""
    if not path:
        return "No path provided."
    if not op.exists(path):
        return "Script not found:\n{}".format(path)
    try:
        script_dir = op.dirname(path)
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)
        _inject_extension_paths(path)
        uidoc = uiapp.ActiveUIDocument if uiapp else None
        doc   = uidoc.Document if uidoc else None
        exec_params         = _ExecParams(path)
        # Use full path hash + id to guarantee uniqueness and avoid module cache collisions
        mod_name            = "cdy_script_{:x}_{:x}".format(abs(hash(path)), id(exec_params) & 0xFFFF)
        mod                 = imp.new_module(mod_name)
        mod.__file__        = op.dirname(path)  # dir not file — pyRevit resolves XAML relative to this
        mod.__revit__       = uiapp
        mod.__uidoc__       = uidoc
        mod.__doc__         = doc
        mod.EXEC_PARAMS     = exec_params
        mod.__commandname__ = exec_params.command_name
        mod.__commandpath__ = op.dirname(path)  # dir not file — pyRevit resolves XAML relative to this
        for k, v in extra_globals.items():
            setattr(mod, k, v)
        try:
            from pyrevit import revit as _pvrevit
            mod.revit = _pvrevit
        except Exception:
            pass
        class _ScriptProxy(object):
            def exit(self): raise SystemExit
            def get_config(self, section=None):
                class _Cfg(object):
                    def __getattr__(self, n): return None
                    def __setattr__(self, n, v): pass
                    def save_changes(self): pass
                return _Cfg()
            def get_logger(self):
                import logging
                return logging.getLogger(exec_params.command_name)
            def get_output(self): return None
        mod.script = _ScriptProxy()
        sys.modules[mod_name] = mod
        with open(path, "r") as f:
            source = f.read()
        mod.__dict__["__name__"] = "__main__"
        exec(compile(source, path, "exec"), mod.__dict__)
        sys.modules.pop(mod_name, None)
        return None
    except SystemExit:
        sys.modules.pop(mod_name, None)
        return None
    except Exception:
        sys.modules.pop(mod_name, None)
        import traceback
        return traceback.format_exc()


_h_highlight = HighlightHandler(); _e_highlight = ExternalEvent.Create(_h_highlight)
_h_reset_all_override = ScriptLaunchHandler("Reset_all_overrides");  _e_reset_all_override = ExternalEvent.Create(_h_reset_all_override)
_h_reset_sel_override = ScriptLaunchHandler("Reset_sel_overrides");  _e_reset_sel_override = ExternalEvent.Create(_h_reset_sel_override)

_h_open_dwg     = ScriptLaunchHandler("open_dwg_autocad");  _e_open_dwg     = ExternalEvent.Create(_h_open_dwg)
_h_reload_dwg   = ScriptLaunchHandler("reload_dwg");        _e_reload_dwg   = ExternalEvent.Create(_h_reload_dwg)
_h_greyscale    = ScriptLaunchHandler("greyscale_dwg");     _e_greyscale    = ExternalEvent.Create(_h_greyscale)
_h_revert_grey  = ScriptLaunchHandler("revert_greyscale_dwg"); _e_revert_grey = ExternalEvent.Create(_h_revert_grey)
_h_hide_layer   = HideLayerToggleHandler();                 _e_hide_layer   = ExternalEvent.Create(_h_hide_layer)


class ACCHandler(IExternalEventHandler):
    """Opens ACC in the browser. region = 'eu' or 'gbr'."""
    def __init__(self):
        self.region = "eu"
        self.status = None

    def Execute(self, uiapp):
        import webbrowser
        doc = uiapp.ActiveUIDocument.Document if uiapp.ActiveUIDocument else None
        if not doc:
            return
        try:
            hub_str  = DB.Document.GetHubId(doc)[2:]
            proj_str = DB.Document.GetProjectId(doc)[2:]
        except Exception as ex:
            if self.status:
                def _e(tb=self.status, m=str(ex)):
                    _set_status(tb, "ACC error: {}".format(m), error=True)
                self.status.Dispatcher.Invoke(Action(_e))
            return
        if self.region == "gbr":
            url = "https://acc.gbr.autodesk.com/insight/accounts/{}/projects/{}/my-dashboard".format(
                hub_str, proj_str)
        else:
            url = "https://acc.autodesk.eu/insight/accounts/{}/projects/{}/home".format(
                hub_str, proj_str)
        webbrowser.open_new_tab(url)

    def GetName(self):
        return "CDY ACC Open"


_h_bim360_eu  = ACCHandler();  _h_bim360_eu.region  = "eu";  _e_bim360_eu  = ExternalEvent.Create(_h_bim360_eu)
_h_bim360_gbr = ACCHandler();  _h_bim360_gbr.region = "gbr"; _e_bim360_gbr = ExternalEvent.Create(_h_bim360_gbr)
# Keep legacy alias so any existing references don't break
_h_bim360 = _h_bim360_eu;  _e_bim360 = _e_bim360_eu
_h_central      = ScriptLaunchHandler("open_central_location"); _e_central  = ExternalEvent.Create(_h_central)
_h_local        = ScriptLaunchHandler("open_local_location");   _e_local    = ExternalEvent.Create(_h_local)


# =============================================================================
# SECTION 8 - DOCKABLE PANEL
#
# Uses raw Revit API (IDockablePaneProvider + UserControl) directly.
# This avoids forms.WPFPanel which hard-requires a XAML file.
# =============================================================================

from Autodesk.Revit.UI import IDockablePaneProvider, DockablePaneId
from System.Windows.Controls import UserControl
from System import Guid

_CDY_PANE_ID    = DockablePaneId(Guid("c4e8f127-9d3b-4a71-b6e2-1f0d7c5a8b94"))
_CDY_PANE_TITLE = "CDY Tools"

# Light grey used throughout the panel
_PANEL_GREY     = Media.Color.FromRgb(235, 235, 235)
_PANEL_GREY_MID = Media.Color.FromRgb(220, 220, 220)


class CDYToolsPanel(UserControl, IDockablePaneProvider):

    def SetupDockablePane(self, data):
        data.FrameworkElement = self
        data.VisibleByDefault = True

    def __init__(self):
        UserControl.__init__(self)
        self._star_buttons = {}
        self._fav_panel    = None
        self._fav_status   = None
        try:
            self._build_ui()
        except Exception as ex:
            print("CDY: CDYToolsPanel INIT ERROR: {}".format(ex))

    # ---------------------------------------------------------------- helpers

    def _label(self, text, bold=False, small=False):
        tb = TextBlock()
        tb.Text         = text
        tb.TextWrapping = TextWrapping.Wrap
        tb.Margin       = Thickness(0, 4, 0, 2)
        if bold:
            tb.FontWeight = FontWeights.Bold
        if small:
            tb.FontSize   = 10
            tb.Foreground = Brushes.Gray
        return tb

    def _button(self, text, handler_fn):
        btn = Button()
        btn.Content = text
        btn.Margin  = Thickness(0, 4, 0, 2)
        btn.Padding = Thickness(6, 4, 6, 4)
        btn.HorizontalAlignment = System_HAlign.Stretch
        btn.Click  += handler_fn
        return btn

    def _fav_row(self, label, handler_fn, script_key):
        row = DockPanel()
        row.Margin        = Thickness(0, 4, 0, 2)
        row.LastChildFill = True

        star = Button()
        star.Width   = 26
        star.Padding = Thickness(0)
        star.Margin  = Thickness(4, 0, 0, 0)
        star.Content = u"\u2605"
        star.ToolTip = "Add to / remove from Favourites"
        star.VerticalAlignment = System.Windows.VerticalAlignment.Stretch
        is_fav = _fav_is_key(script_key)
        star.Foreground = SolidColorBrush(
            Media.Color.FromRgb(218, 165, 32) if is_fav
            else Media.Color.FromRgb(180, 180, 180))
        self._star_buttons[script_key] = star

        def _on_star(s, a, k=script_key, sb=star):
            now = _fav_toggle_key(k)
            sb.Foreground = SolidColorBrush(
                Media.Color.FromRgb(218, 165, 32) if now
                else Media.Color.FromRgb(180, 180, 180))
            self._refresh_fav_tab()

        star.Click += _on_star
        DockPanel.SetDock(star, Dock.Right)
        row.Children.Add(star)

        btn = Button()
        btn.Content = label
        btn.Padding = Thickness(6, 4, 6, 4)
        btn.HorizontalAlignment = System_HAlign.Stretch
        btn.Click += handler_fn
        row.Children.Add(btn)
        return row

    def _status(self):
        tb = TextBlock()
        tb.Text         = "---"
        tb.Margin       = Thickness(0, 6, 0, 4)
        tb.TextWrapping = TextWrapping.Wrap
        tb.Foreground   = Brushes.Gray
        tb.FontSize     = 11
        return tb

    def _sep(self):
        s        = Separator()
        s.Margin = Thickness(0, 6, 0, 6)
        return s

    def _make_tab(self, header):
        tab    = TabItem()
        tab.Header = header
        # ── ScrollViewer: semi-transparent over the grey root ──────────────
        scroll = ScrollViewer()
        scroll.VerticalScrollBarVisibility   = ScrollBarVisibility.Auto
        scroll.HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled
        # Alpha 0 = fully transparent — watermark on white root shows through
        scroll.Background = SolidColorBrush(
            Media.Color.FromArgb(0, 255, 255, 255))
        panel  = StackPanel()
        panel.Margin   = Thickness(8)
        scroll.Content = panel
        tab.Content    = scroll
        return tab, panel

    def _section(self, panel, title):
        panel.Children.Add(self._label(title, bold=True))
        panel.Children.Add(self._sep())

    # ---------------------------------------------------------------- root build

    def _build_ui(self):
        root = Grid()

        # Step 1 ── white base so the logo grey reads clearly against it
        root.Background = SolidColorBrush(Media.Color.FromRgb(255, 255, 255))

        # Step 2 ── overlay the CDY watermark DrawingBrush on top of the grey base.
        #           We do this by placing a second child element that carries the
        #           brush, rather than replacing root.Background.
        try:
            import System.Windows.Markup as Markup
            from System.Windows.Controls import Border

            LOGO_XAML = (
                '<DrawingBrush xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"'
                ' Stretch="Uniform" AlignmentX="Center" AlignmentY="Center"'
                ' Viewport="0.05,0.3,0.9,0.4" ViewportUnits="RelativeToBoundingBox">'
                '<DrawingBrush.Drawing><DrawingGroup Opacity="0.35">'
                '<GeometryDrawing Brush="#FFB0B0B0" Geometry="'
                'M20.0244 6.68262V13.5674H19.4531C19.0234 11.7705 18.2227 10.3936 17.0508 9.43652C15.8789 8.47949 14.5508 8.00098 13.0664 8.00098C11.8262 8.00098 10.6885 8.35742 9.65332 9.07031C8.61816 9.7832 7.86133 10.7158 7.38281 11.8682C6.76758 13.3428 6.45996 14.9834 6.45996 16.79C6.45996 18.5674 6.68457 20.1885 7.13379 21.6533C7.58301 23.1084 8.28613 24.2119 9.24316 24.9639C10.2002 25.7061 11.4404 26.0771 12.9639 26.0771C14.2139 26.0771 15.3564 25.8037 16.3916 25.2568C17.4365 24.71 18.5352 23.7676 19.6875 22.4297V24.1436C18.5742 25.3057 17.4121 26.1504 16.2012 26.6777C15 27.1953 13.5938 27.4541 11.9824 27.4541C9.86328 27.4541 7.97852 27.0293 6.32812 26.1797C4.6875 25.3301 3.41797 24.1094 2.51953 22.5176C1.63086 20.9258 1.18652 19.2314 1.18652 17.4346C1.18652 15.54 1.67969 13.7432 2.66602 12.0439C3.66211 10.3447 5 9.02637 6.67969 8.08887C8.36914 7.15137 10.1611 6.68262 12.0557 6.68262C13.4521 6.68262 14.9268 6.98535 16.4795 7.59082C17.3779 7.94238 17.9492 8.11816 18.1934 8.11816C18.5059 8.11816 18.7744 8.00586 18.999 7.78125C19.2334 7.54688 19.3848 7.18066 19.4531 6.68262H20.0244Z'
                'M33.2484 17.9473V23.5137C33.2484 24.5879 33.3119 25.2666 33.4389 25.5498C33.5756 25.8232 33.81 26.043 34.142 26.209C34.474 26.375 35.0941 26.458 36.0023 26.458V27H25.8363V26.458C26.7543 26.458 27.3744 26.375 27.6967 26.209C28.0287 26.0332 28.2582 25.8086 28.3852 25.5352C28.5219 25.2617 28.5902 24.5879 28.5902 23.5137V10.623C28.5902 9.54883 28.5219 8.875 28.3852 8.60156C28.2582 8.31836 28.0287 8.09375 27.6967 7.92773C27.3646 7.76172 26.7445 7.67871 25.8363 7.67871V7.13672H35.0648C37.4672 7.13672 39.225 7.30273 40.3383 7.63477C41.4516 7.9668 42.3598 8.58203 43.0629 9.48047C43.766 10.3691 44.1176 11.4141 44.1176 12.6152C44.1176 14.0801 43.5902 15.291 42.5355 16.248C41.8617 16.8535 40.9193 17.3076 39.7084 17.6104L44.4838 24.334C45.1088 25.2031 45.5531 25.7451 45.8168 25.96C46.2172 26.2627 46.6811 26.4287 47.2084 26.458V27H40.9535L34.5521 17.9473H33.2484Z'
                'M33.2484 8.20605V16.9072H34.0834C35.4408 16.9072 36.4564 16.7852 37.1303 16.541C37.8041 16.2871 38.3314 15.8379 38.7123 15.1934C39.1029 14.5391 39.2982 13.6895 39.2982 12.6445C39.2982 11.1309 38.9418 10.0127 38.2289 9.29004C37.5258 8.56738 36.3881 8.20605 34.8158 8.20605H33.2484Z'
                'M63.0398 21.3457H56.0232L55.1883 23.2793C54.9148 23.9238 54.7781 24.4561 54.7781 24.876C54.7781 25.4326 55.0027 25.8428 55.452 26.1064C55.7156 26.2627 56.365 26.3799 57.4002 26.458V27H50.7938V26.458C51.5066 26.3506 52.0926 26.0576 52.5516 25.5791C53.0105 25.0908 53.577 24.0898 54.2508 22.5762L61.3553 6.72656H61.6336L68.7967 23.0156C69.4803 24.5586 70.0418 25.5303 70.4813 25.9307C70.8133 26.2334 71.282 26.4092 71.8875 26.458V27H62.2781V26.458H62.6736C63.4451 26.458 63.9871 26.3506 64.2996 26.1357C64.5145 25.9795 64.6219 25.7549 64.6219 25.4619C64.6219 25.2861 64.5926 25.1055 64.534 24.9199C64.5145 24.832 64.368 24.4658 64.0945 23.8213L63.0398 21.3457Z'
                'M62.5418 20.2617L59.5828 13.4209L56.5359 20.2617H62.5418Z'
                'M76.2346 27V26.458H76.8938C77.4699 26.458 77.9094 26.3701 78.2121 26.1943C78.5246 26.0088 78.7541 25.7598 78.9006 25.4473C78.9885 25.2422 79.0324 24.627 79.0324 23.6016V10.5352C79.0324 9.51953 78.9787 8.88477 78.8713 8.63086C78.7639 8.37695 78.5441 8.15723 78.2121 7.97168C77.8898 7.77637 77.4504 7.67871 76.8938 7.67871H76.2346V7.13672H85.1262C87.4992 7.13672 89.4084 7.45898 90.8537 8.10352C92.6213 8.89453 93.9592 10.0908 94.8674 11.6924C95.7854 13.2939 96.2443 15.1055 96.2443 17.127C96.2443 18.5234 96.0197 19.8125 95.5705 20.9941C95.1213 22.166 94.5402 23.1377 93.8273 23.9092C93.1145 24.6709 92.2893 25.2861 91.3518 25.7549C90.424 26.2139 89.2863 26.5703 87.9387 26.8242C87.343 26.9414 86.4055 27 85.1262 27H76.2346Z'
                'M83.8078 8.26465V23.7627C83.8078 24.583 83.8469 25.0859 83.925 25.2715C84.0031 25.457 84.135 25.5986 84.3205 25.6963C84.5842 25.8428 84.965 25.916 85.4631 25.916C87.0939 25.916 88.3391 25.3594 89.1984 24.2461C90.3703 22.7422 90.9563 20.4082 90.9563 17.2441C90.9563 14.6953 90.5559 12.6592 89.7551 11.1357C89.1203 9.94434 88.3049 9.13379 87.3088 8.7041C86.6057 8.40137 85.4387 8.25488 83.8078 8.26465Z'
                'M101.514 27V26.458H102.173C102.75 26.458 103.189 26.3701 103.492 26.1943C103.804 26.0088 104.034 25.7598 104.18 25.4473C104.268 25.2422 104.312 24.627 104.312 23.6016V10.5352C104.312 9.51953 104.258 8.88477 104.151 8.63086C104.044 8.37695 103.824 8.15723 103.492 7.97168C103.17 7.77637 102.73 7.67871 102.173 7.67871H101.514V7.13672H110.406C112.779 7.13672 114.688 7.45898 116.133 8.10352C117.901 8.89453 119.239 10.0908 120.147 11.6924C121.065 13.2939 121.524 15.1055 121.524 17.127C121.524 18.5234 121.299 19.8125 120.85 20.9941C120.401 22.166 119.82 23.1377 119.107 23.9092C118.394 24.6709 117.569 25.2861 116.631 25.7549C115.704 26.2139 114.566 26.5703 113.218 26.8242C112.623 26.9414 111.685 27 110.406 27H101.514Z'
                'M109.088 8.26465V23.7627C109.088 24.583 109.127 25.0859 109.205 25.2715C109.283 25.457 109.415 25.5986 109.6 25.6963C109.864 25.8428 110.245 25.916 110.743 25.916C112.374 25.916 113.619 25.3594 114.478 24.2461C115.65 22.7422 116.236 20.4082 116.236 17.2441C116.236 14.6953 115.836 12.6592 115.035 11.1357C114.4 9.94434 113.585 9.13379 112.588 8.7041C111.885 8.40137 110.718 8.25488 109.088 8.26465Z'
                'M147.727 7.13672V7.67871C147.072 7.7666 146.569 7.95703 146.218 8.25C145.729 8.66016 144.958 9.77832 143.903 11.6045L139.597 18.7969V23.6016C139.597 24.627 139.65 25.2666 139.758 25.5205C139.865 25.7646 140.075 25.9844 140.388 26.1797C140.71 26.3652 141.135 26.458 141.662 26.458H142.775V27H131.628V26.458H132.668C133.254 26.458 133.718 26.3555 134.06 26.1504C134.313 26.0137 134.514 25.7793 134.66 25.4473C134.768 25.2129 134.821 24.5977 134.821 23.6016V19.6172L130.148 11.1064C129.221 9.42676 128.566 8.44043 128.186 8.14746C127.805 7.84473 127.297 7.68848 126.662 7.67871V7.13672H136.184V7.67871H135.759C135.183 7.67871 134.777 7.76172 134.543 7.92773C134.318 8.09375 134.206 8.26953 134.206 8.45508C134.206 8.80664 134.597 9.69043 135.378 11.1064L138.967 17.6836L142.541 11.6924C143.43 10.2275 143.874 9.25586 143.874 8.77734C143.874 8.51367 143.747 8.29395 143.493 8.11816C143.161 7.87402 142.551 7.72754 141.662 7.67871V7.13672H147.727Z'
                'M165.77 6.68262L165.931 13.3037H165.33C165.047 11.6436 164.349 10.3105 163.236 9.30469C162.132 8.28906 160.936 7.78125 159.647 7.78125C158.651 7.78125 157.86 8.0498 157.274 8.58691C156.698 9.11426 156.41 9.72461 156.41 10.418C156.41 10.8574 156.512 11.248 156.717 11.5898C157 12.0488 157.454 12.5029 158.079 12.9521C158.538 13.2744 159.598 13.8457 161.258 14.666C163.582 15.8086 165.15 16.8877 165.96 17.9033C166.761 18.9189 167.162 20.0811 167.162 21.3896C167.162 23.0498 166.512 24.4805 165.213 25.6816C163.924 26.873 162.284 27.4688 160.291 27.4688C159.666 27.4688 159.076 27.4053 158.519 27.2783C157.962 27.1514 157.264 26.9121 156.424 26.5605C155.955 26.3652 155.57 26.2676 155.267 26.2676C155.013 26.2676 154.745 26.3652 154.461 26.5605C154.178 26.7559 153.949 27.0537 153.773 27.4541H153.231V19.9541H153.773C154.203 22.0635 155.028 23.6748 156.248 24.7881C157.479 25.8916 158.802 26.4434 160.218 26.4434C161.312 26.4434 162.181 26.1455 162.826 25.5498C163.48 24.9541 163.807 24.2607 163.807 23.4697C163.807 23.001 163.68 22.5469 163.426 22.1074C163.182 21.668 162.806 21.2529 162.298 20.8623C161.79 20.4619 160.892 19.9443 159.603 19.3096C157.796 18.4209 156.497 17.6641 155.706 17.0391C154.915 16.4141 154.305 15.7158 153.875 14.9443C153.455 14.1729 153.246 13.3232 153.246 12.3955C153.246 10.8135 153.827 9.46582 154.989 8.35254C156.151 7.23926 157.616 6.68262 159.383 6.68262C160.028 6.68262 160.653 6.76074 161.258 6.91699C161.717 7.03418 162.274 7.25391 162.928 7.57617C163.592 7.88867 164.056 8.04492 164.32 8.04492C164.574 8.04492 164.774 7.9668 164.92 7.81055C165.067 7.6543 165.204 7.27832 165.33 6.68262H165.77Z'
                '"/></DrawingGroup></DrawingBrush.Drawing></DrawingBrush>'
            )
            watermark_border = Border()
            watermark_border.Background  = Markup.XamlReader.Parse(LOGO_XAML)
            watermark_border.IsHitTestVisible = False   # clicks pass through
            root.Children.Add(watermark_border)
        except Exception as ex:
            print("CDY: Watermark failed: {}".format(ex))

        # Step 3 ── TabControl: fully transparent so root grey shows through,
        #           including the tab-header strip (previously appeared black).
        tabs = TabControl()
        tabs.Background = SolidColorBrush(Media.Color.FromArgb(0, 0, 0, 0))
        tabs.BorderThickness = Thickness(0)

        tabs.Items.Add(self._build_fav_tab())
        tabs.Items.Add(self._build_views_tab())
        tabs.Items.Add(self._build_modelling_tab())
        tabs.Items.Add(self._build_dimensions_tab())
        tabs.Items.Add(self._build_tagging_tab())
        tabs.Items.Add(self._build_files_tab())

        root.Children.Add(tabs)
        self.Content = root

    # ---------------------------------------------------------------- Favourites tab

    def _build_fav_tab(self):
        tab, p = self._make_tab(u"\u2605 Favourites")
        self._fav_panel = p
        self._section(p, "Favourites")
        p.Children.Add(self._label(
            u"Click \u2605 next to any tool to pin it here, "
            u"or use Browse to add any tool from the extension.",
            u"SOME ADDED TOOLS MAY NOT RUN, IF SO, REPORT TO JW.",
            small=True))
        p.Children.Add(self._button(u"\U0001F50D  Browse & Add Tool", self._on_browse))
        p.Children.Add(self._sep())
        self._populate_favs(p)
        return tab

    def _populate_favs(self, p):
        favs = _load_favs()
        if not favs:
            p.Children.Add(self._label(
                u"No favourites yet. Click \u2605 or use Browse above.",
                small=True))
        else:
            for item in favs:
                lbl  = item.get("label", "Unknown")
                path = item.get("path", "")

                row = DockPanel()
                row.Margin        = Thickness(0, 4, 0, 2)
                row.LastChildFill = True

                rem = Button()
                rem.Content    = u"\u00d7"
                rem.Width      = 26
                rem.Padding    = Thickness(0)
                rem.Margin     = Thickness(4, 0, 0, 0)
                rem.Foreground = SolidColorBrush(Media.Color.FromRgb(180, 60, 60))
                rem.ToolTip    = "Remove from Favourites"

                def _on_rem(s, a, pt=path):
                    _fav_remove(pt)
                    self._refresh_fav_tab()
                    for k, v in SCRIPTS.items():
                        if v == pt and k in self._star_buttons:
                            self._star_buttons[k].Foreground = SolidColorBrush(
                                Media.Color.FromRgb(180, 180, 180))

                rem.Click += _on_rem
                DockPanel.SetDock(rem, Dock.Right)
                row.Children.Add(rem)

                tool = Button()
                tool.Content = lbl
                tool.Padding = Thickness(6, 4, 6, 4)
                tool.HorizontalAlignment = System_HAlign.Stretch
                tool.ToolTip = path

                def _on_run(s, a, pt=path, cmd_name=item.get("command_id"),
                            lbl=lbl, status=self._fav_status):
                    _fav_handler.path      = pt
                    _fav_handler.cmd_name  = cmd_name
                    _fav_handler.label     = lbl
                    _fav_handler.status_tb = status
                    _fav_event.Raise()

                tool.Click += _on_run
                row.Children.Add(tool)
                p.Children.Add(row)

        self._fav_status = self._status()
        p.Children.Add(self._fav_status)

    def _refresh_fav_tab(self):
        try:
            p = self._fav_panel
            p.Children.Clear()
            self._section(p, "Favourites")
            p.Children.Add(self._label(
                u"Click \u2605 next to any tool to pin it here, "
                u"or use Browse to add any tool from the extension.",
                small=True))
            p.Children.Add(self._button(
                u"\U0001F50D  Browse & Add Tool", self._on_browse))
            p.Children.Add(self._sep())
            self._populate_favs(p)
        except Exception:
            pass

    def _on_browse(self, sender, args):
        from System.Windows import Window, WindowStartupLocation, ResizeMode
        from System.Windows.Controls import ListBox, ListBoxItem, TextBox, Orientation

        all_scripts = _scan_scripts(_bimtools_tab)
        if not all_scripts:
            forms.alert("No scripts found under:\n{}".format(_bimtools_tab),
                        title="Browse Tools")
            return

        win = Window()
        win.Title  = "Browse & Add to Favourites"
        win.Width  = 500
        win.Height = 540
        win.WindowStartupLocation = WindowStartupLocation.CenterScreen
        win.ResizeMode = ResizeMode.CanResizeWithGrip

        outer = StackPanel()
        outer.Margin = Thickness(10)

        info = TextBlock()
        info.Text         = "Search and select a tool to add to Favourites:"
        info.Margin       = Thickness(0, 0, 0, 6)
        info.TextWrapping = TextWrapping.Wrap
        outer.Children.Add(info)

        search = TextBox()
        search.Margin   = Thickness(0, 0, 0, 6)
        search.Padding  = Thickness(4)
        search.FontSize = 12
        search.ToolTip  = "Type to filter"
        outer.Children.Add(search)

        lb = ListBox()
        lb.Height   = 340
        lb.FontSize = 11

        def _fill(text=""):
            lb.Items.Clear()
            for s in all_scripts:
                if text.lower() in s["label"].lower():
                    li         = ListBoxItem()
                    li.Content = s["label"]
                    li.Tag     = s["path"]
                    li.ToolTip = s["path"]
                    lb.Items.Add(li)

        _fill()
        outer.Children.Add(lb)
        search.TextChanged += lambda s, a: _fill(search.Text)

        btns = StackPanel()
        btns.Orientation = Orientation.Horizontal
        btns.Margin      = Thickness(0, 8, 0, 0)

        add_btn = Button()
        add_btn.Content = "Add to Favourites"
        add_btn.Padding = Thickness(12, 6, 12, 6)
        add_btn.Margin  = Thickness(0, 0, 8, 0)

        close_btn = Button()
        close_btn.Content = "Close"
        close_btn.Padding = Thickness(12, 6, 12, 6)
        close_btn.Click  += lambda s, a: win.Close()

        st = TextBlock()
        st.Margin = Thickness(8, 0, 0, 0)
        st.VerticalAlignment = System.Windows.VerticalAlignment.Center

        def _on_add(s, a):
            sel = lb.SelectedItem
            if not sel:
                st.Text       = "Select a tool first."
                st.Foreground = Brushes.Crimson
                return
            if _fav_add(sel.Content, sel.Tag):
                st.Text       = u"\u2605 Added!"
                st.Foreground = Brushes.SeaGreen
                self._refresh_fav_tab()
            else:
                st.Text       = "Already in Favourites."
                st.Foreground = Brushes.DarkOrange

        add_btn.Click += _on_add
        btns.Children.Add(add_btn)
        btns.Children.Add(close_btn)
        btns.Children.Add(st)
        outer.Children.Add(btns)

        win.Content = outer
        win.ShowDialog()

    # ---------------------------------------------------------------- Tab 1: Views

    def _build_views_tab(self):
        tab, p = self._make_tab("Views")
        self._section(p, "View Navigation")
        p.Children.Add(self._label(
            "Navigate quickly between views, sheets and parent/dependent relationships.",
            small=True))
        p.Children.Add(self._sep())
        p.Children.Add(self._fav_row("Open Host Sheet",             self._on_open_sheet,  "open_host_sheet"))
        p.Children.Add(self._label("Opens the sheet the active view is placed on.", small=True))
        p.Children.Add(self._fav_row("Open View Selected on Sheet", self._on_open_view,   "open_view_on_sheet"))
        p.Children.Add(self._label("Select a viewport on a sheet, then click to jump to that view.", small=True))
        p.Children.Add(self._fav_row("Open Parent / Primary View",  self._on_open_parent, "open_parent_view"))
        p.Children.Add(self._label("Opens the primary view if the active view is a dependent.", small=True))
        st = self._status()
        p.Children.Add(st)
        _h_open_sheet.status = _h_open_view.status = _h_open_parent.status = st
        return tab

    def _on_open_sheet(self, s, a):  _e_open_sheet.Raise()
    def _on_open_view(self, s, a):   _e_open_view.Raise()
    def _on_open_parent(self, s, a): _e_open_parent.Raise()

    # ---------------------------------------------------------------- Tab 2: Modelling

    def _build_modelling_tab(self):
        tab, p = self._make_tab("Modelling")
        self._section(p, "Selection Filters")
        p.Children.Add(self._label("Box-select elements filtered to 2D or 3D categories.", small=True))
        p.Children.Add(self._fav_row("Pick 2D Elements",      self._on_pick2d,       "pick_2d"))
        p.Children.Add(self._fav_row("Pick 3D Elements",      self._on_pick3d,       "pick_3d"))
        p.Children.Add(self._fav_row("Pick Grouped Elements", self._on_pick_grouped, "pick_grouped"))
        p.Children.Add(self._label("For grouped elements: select groups first, then click.", small=True))
        p.Children.Add(self._sep())
        self._section(p, "Datum Bubbles")
        p.Children.Add(self._label("Select grids or levels, then flip their bubble end.", small=True))
        p.Children.Add(self._fav_row("Flip Grid Bubbles",  self._on_flip_grid,  "flip_grid_bubbles"))
        p.Children.Add(self._fav_row("Flip Level Bubbles", self._on_flip_level, "flip_level_bubbles"))
        st = self._status()
        p.Children.Add(st)
        _h_pick2d.status = _h_pick3d.status = _h_pick_grouped.status = st
        _h_flip_grid.status = _h_flip_level.status = st
        return tab

    def _on_pick2d(self, s, a):       _e_pick2d.Raise()
    def _on_pick3d(self, s, a):       _e_pick3d.Raise()
    def _on_pick_grouped(self, s, a): _e_pick_grouped.Raise()
    def _on_flip_grid(self, s, a):    _e_flip_grid.Raise()
    def _on_flip_level(self, s, a):   _e_flip_level.Raise()

    # ---------------------------------------------------------------- Tab 3: Dimensions

    def _build_dimensions_tab(self):
        tab, p = self._make_tab("Dimensions")
        self._section(p, "Auto Dimension")
        p.Children.Add(self._label("Select 2 or more grids or levels, then click.", small=True))
        p.Children.Add(self._fav_row("Dimension Selected Gridlines", self._on_dim_grids,  "dim_gridlines"))
        p.Children.Add(self._label("Places a linear dimension string across all selected grids.", small=True))
        p.Children.Add(self._fav_row("Dimension Selected Levels",    self._on_dim_levels, "dim_levels"))
        p.Children.Add(self._label("Places a vertical dimension string across all selected levels.", small=True))
        st = self._status()
        p.Children.Add(st)
        _h_dim_grids.status = _h_dim_levels.status = st
        return tab

    def _on_dim_grids(self, s, a):  _e_dim_grids.Raise()
    def _on_dim_levels(self, s, a): _e_dim_levels.Raise()

    # ---------------------------------------------------------------- Tab 4: Tagging

    def _build_tagging_tab(self):
        tab, p = self._make_tab("Tagging")
        self._section(p, "Select Untagged Elements")
        p.Children.Add(self._label(
            "Selects all untagged elements of the chosen category in the active view. "
            "Use with Tag All to finish tagging in one step.", small=True))
        p.Children.Add(self._fav_row("Select Untagged in Active View",
                                     self._on_sel_untagged, "select_untagged"))
        p.Children.Add(self._sep())
        self._section(p, "Graphics Overrides")
        p.Children.Add(self._label(
            "Select elements first, then click to apply or reset colour overrides.", small=True))
        p.Children.Add(self._highlight_row())
        p.Children.Add(self._label(
            "Overrides selected elements with the chosen colour in the active view.", small=True))
        p.Children.Add(self._fav_row("Reset Selected Overrides",
                                     self._on_reset_sel_override, "Reset_sel_overrides"))
        p.Children.Add(self._label(
            "Removes all graphic overrides from selected elements in the active view.", small=True))
        p.Children.Add(self._fav_row("Reset All Overrides",
                                     self._on_reset_all_override, "Reset_all_overrides"))
        p.Children.Add(self._label(
            "Removes all graphic overrides from every element in the active view.", small=True))
        st = self._status()
        p.Children.Add(st)
        _h_sel_untagged.status = _h_highlight.status = st
        _h_reset_sel_override.status = _h_reset_all_override.status = st
        return tab

    def _on_sel_untagged(self, s, a):    _e_sel_untagged.Raise()
    def _highlight_row(self):
        """Highlight row: [colour swatch picker] [Highlight Selected ★]"""
        from System.Windows.Controls import ContextMenu, MenuItem

        row = DockPanel()
        row.Margin        = Thickness(0, 4, 0, 2)
        row.LastChildFill = True

        # ── star (favourites) ──────────────────────────────────────────────
        star = Button()
        star.Width   = 26
        star.Padding = Thickness(0)
        star.Margin  = Thickness(4, 0, 0, 0)
        star.Content = u"★"
        star.ToolTip = "Add to / remove from Favourites"
        star.VerticalAlignment = System.Windows.VerticalAlignment.Stretch
        is_fav = _fav_is_key("Highlight_selected")
        star.Foreground = SolidColorBrush(
            Media.Color.FromRgb(218, 165, 32) if is_fav
            else Media.Color.FromRgb(180, 180, 180))
        self._star_buttons["Highlight_selected"] = star

        def _on_star(s, a, sb=star):
            now = _fav_toggle_key("Highlight_selected")
            sb.Foreground = SolidColorBrush(
                Media.Color.FromRgb(218, 165, 32) if now
                else Media.Color.FromRgb(180, 180, 180))
            self._refresh_fav_tab()

        star.Click += _on_star
        DockPanel.SetDock(star, Dock.Right)
        row.Children.Add(star)

        # ── colour swatch picker button ────────────────────────────────────
        self._highlight_swatch = Button()
        self._highlight_swatch.Width   = 26
        self._highlight_swatch.Padding = Thickness(0)
        self._highlight_swatch.Margin  = Thickness(0, 0, 4, 0)
        self._highlight_swatch.ToolTip = "Pick highlight colour"
        self._highlight_swatch.VerticalAlignment = System.Windows.VerticalAlignment.Stretch
        self._update_swatch()

        # Preset colours in a context menu
        cm = ContextMenu()
        presets = [
            (u"Green  (default)", 0,   200, 0  ),
            (u"Red",              220, 40,  40  ),
            (u"Blue",             40,  120, 220 ),
            (u"Yellow",           255, 210, 0   ),
            (u"Cyan",             0,   200, 200 ),
            (u"Magenta",          200, 0,   200 ),
            (u"Orange",           255, 140, 0   ),
            (u"White",            255, 255, 255 ),
            (u"Custom…",     None,None,None),
        ]
        for label, r, g, b in presets:
            mi = MenuItem()
            mi.Header = label
            if r is not None:
                def _pick(s, a, rv=r, gv=g, bv=b):
                    global CDY_HIGHLIGHT_COLOR
                    CDY_HIGHLIGHT_COLOR = (rv, gv, bv)
                    self._update_swatch()
            else:
                def _pick(s, a):
                    self._pick_custom_color()
            mi.Click += _pick
            cm.Items.Add(mi)

        self._highlight_swatch.ContextMenu = cm
        # Left-click also opens the menu
        def _swatch_click(s, a):
            self._highlight_swatch.ContextMenu.IsOpen = True
        self._highlight_swatch.Click += _swatch_click

        DockPanel.SetDock(self._highlight_swatch, Dock.Left)
        row.Children.Add(self._highlight_swatch)

        # ── main button ────────────────────────────────────────────────────
        btn = Button()
        btn.Content = "Highlight Selected"
        btn.Padding = Thickness(6, 4, 6, 4)
        btn.HorizontalAlignment = System_HAlign.Stretch
        btn.Click += self._on_highlight
        row.Children.Add(btn)
        return row

    def _update_swatch(self):
        """Repaint the colour swatch button to reflect CDY_HIGHLIGHT_COLOR."""
        r, g, b = CDY_HIGHLIGHT_COLOR
        self._highlight_swatch.Background = SolidColorBrush(
            Media.Color.FromRgb(r, g, b))
        # Use black or white text depending on luminance
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        self._highlight_swatch.Foreground = SolidColorBrush(
            Media.Color.FromRgb(0, 0, 0) if lum > 140
            else Media.Color.FromRgb(255, 255, 255))
        self._highlight_swatch.Content = u"●"

    def _pick_custom_color(self):
        """Open the Windows native colour picker dialog."""
        clr.AddReference("System.Windows.Forms")
        clr.AddReference("System.Drawing")
        import System.Windows.Forms as WinForms
        import System.Drawing as Drawing

        r, g, b = CDY_HIGHLIGHT_COLOR
        dlg = WinForms.ColorDialog()
        dlg.FullOpen = True   # show the full picker with custom colours expanded
        try:
            dlg.Color = Drawing.Color.FromArgb(r, g, b)
        except:
            pass
        if dlg.ShowDialog() == WinForms.DialogResult.OK:
            global CDY_HIGHLIGHT_COLOR
            c = dlg.Color
            CDY_HIGHLIGHT_COLOR = (int(c.R), int(c.G), int(c.B))
            self._update_swatch()

    def _on_highlight(self, s, a):           _e_highlight.Raise()
    def _on_reset_sel_override(self, s, a):  _e_reset_sel_override.Raise()
    def _on_reset_all_override(self, s, a):  _e_reset_all_override.Raise()

    # ---------------------------------------------------------------- Tab 5: Files

    def _build_files_tab(self):
        tab, p = self._make_tab("Files")
        self._section(p, "DWG Links")
        p.Children.Add(self._label("Select a linked DWG in the canvas first.", small=True))
        p.Children.Add(self._fav_row("Open Selected DWG in AutoCAD", self._on_open_dwg,   "open_dwg_autocad"))
        p.Children.Add(self._fav_row("Reload Selected DWG",          self._on_reload_dwg, "reload_dwg"))
        p.Children.Add(self._label(
            "Overrides all DWG layers to black + halftone in the active view or template.",
            small=True))
        p.Children.Add(self._fav_row("Grey Scale Selected DWG", self._on_greyscale,   "greyscale_dwg"))
        p.Children.Add(self._fav_row("Revert Grey Scale",       self._on_revert_grey, "revert_greyscale_dwg"))
        p.Children.Add(self._label("Removes all colour overrides, restoring Revit defaults.", small=True))

        self._hide_layer_btn = self._button("Hide Layer (Toggle)", self._on_hide_layer)
        p.Children.Add(self._hide_layer_btn)
        p.Children.Add(self._label(
            "Toggle on (button turns red), then click any DWG geometry to hide that "
            "layer instantly. Press ESC to stop. Respects view templates.", small=True))

        p.Children.Add(self._sep())
        self._section(p, "Project Locations")
        # ACC button: left-click = EU, right-click context menu = GBR
        acc_row = self._acc_button_row()
        p.Children.Add(acc_row)
        p.Children.Add(self._label(
            u"Left-click → EU region.  Right-click → GBR region.", small=True))
        p.Children.Add(self._fav_row("Open Central Model Location", self._on_central, "open_central_location"))
        p.Children.Add(self._label("Opens the central model folder in Explorer.", small=True))
        p.Children.Add(self._fav_row("Open Local File Location",    self._on_local,   "open_local_location"))
        p.Children.Add(self._label("Opens the local file folder in Explorer.", small=True))

        st = self._status()
        p.Children.Add(st)
        _h_open_dwg.status   = _h_reload_dwg.status  = st
        _h_greyscale.status  = _h_revert_grey.status  = st
        _h_hide_layer.status = st
        _h_hide_layer.toggle_btn = self._hide_layer_btn
        self._acc_status     = st
        _h_bim360_eu.status  = _h_bim360_gbr.status = st
        _h_bim360.status     = st
        _h_central.status = _h_local.status = st
        return tab

    def _on_open_dwg(self, s, a):    _e_open_dwg.Raise()
    def _on_reload_dwg(self, s, a):  _e_reload_dwg.Raise()
    def _on_greyscale(self, s, a):   _e_greyscale.Raise()
    def _on_revert_grey(self, s, a): _e_revert_grey.Raise()
    def _on_hide_layer(self, s, a):  _e_hide_layer.Raise()
    def _acc_button_row(self):
        """ACC button with left-click (EU) and right-click context menu (GBR)."""
        from System.Windows.Controls import ContextMenu, MenuItem

        row = DockPanel()
        row.Margin        = Thickness(0, 4, 0, 2)
        row.LastChildFill = True

        # ── star button (favourites) ───────────────────────────────────────
        star = Button()
        star.Width   = 26
        star.Padding = Thickness(0)
        star.Margin  = Thickness(4, 0, 0, 0)
        star.Content = u"★"
        star.ToolTip = "Add to / remove from Favourites"
        star.VerticalAlignment = System.Windows.VerticalAlignment.Stretch
        is_fav = _fav_is_key("open_bim360")
        star.Foreground = SolidColorBrush(
            Media.Color.FromRgb(218, 165, 32) if is_fav
            else Media.Color.FromRgb(180, 180, 180))
        self._star_buttons["open_bim360"] = star

        def _on_star(s, a, sb=star):
            now = _fav_toggle_key("open_bim360")
            sb.Foreground = SolidColorBrush(
                Media.Color.FromRgb(218, 165, 32) if now
                else Media.Color.FromRgb(180, 180, 180))
            self._refresh_fav_tab()

        star.Click += _on_star
        DockPanel.SetDock(star, Dock.Right)
        row.Children.Add(star)

        # ── main button (left-click = EU) ──────────────────────────────────
        btn = Button()
        btn.Content = "Open BIM360 / ACC"
        btn.Padding = Thickness(6, 4, 6, 4)
        btn.HorizontalAlignment = System_HAlign.Stretch
        btn.ToolTip = u"Left-click → EU  |  Right-click → GBR"
        btn.Click += self._on_bim360_eu

        # ── right-click context menu (GBR) ─────────────────────────────────
        cm = ContextMenu()
        mi_eu  = MenuItem(); mi_eu.Header  = u"Open ACC — EU region (default)"
        mi_gbr = MenuItem(); mi_gbr.Header = u"Open ACC — GBR region"
        mi_eu.Click  += self._on_bim360_eu
        mi_gbr.Click += self._on_bim360_gbr
        cm.Items.Add(mi_eu)
        cm.Items.Add(mi_gbr)
        btn.ContextMenu = cm

        row.Children.Add(btn)
        return row

    def _on_bim360_eu(self, s, a):
        _h_bim360_eu.status = getattr(self, "_acc_status", None)
        _e_bim360_eu.Raise()

    def _on_bim360_gbr(self, s, a):
        _h_bim360_gbr.status = getattr(self, "_acc_status", None)
        _e_bim360_gbr.Raise()

    def _on_bim360(self, s, a):      _e_bim360_eu.Raise()
    def _on_central(self, s, a):     _e_central.Raise()
    def _on_local(self, s, a):       _e_local.Raise()


# =============================================================================
# SECTION 9 - REGISTER CDY TOOLS PANEL
# Calls HOST_APP.uiapp.RegisterDockablePane directly — no XAML file needed.
# =============================================================================

try:
    _cdy_panel_instance = CDYToolsPanel()
    HOST_APP.uiapp.RegisterDockablePane(
        _CDY_PANE_ID,
        _CDY_PANE_TITLE,
        _cdy_panel_instance
    )
    print("CDY: CDYToolsPanel registered OK.")
except Exception as ex:
    print("CDY: CDYToolsPanel REGISTRATION FAILED: {}".format(ex))
