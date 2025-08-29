# encoding: utf-8
import System

from rpw.ui.forms import (
    FlexForm, Label, ComboBox, Separator, Button, CheckBox, TextBox
)

from pyrevit import script, DB, HOST_APP, revit
from pyrevit.forms import alert, ProgressBar
from pyrevit.revit.db.create import FamilyLoaderOptionsHandler

output = script.get_output()
logger = script.get_logger()


def update_element_type_name(doc, elem_type, find_str, replace_str, dry_run, direct_name_update=False):
    current_name = DB.Element.Name.GetValue(elem_type)
    if current_name and find_str and find_str in current_name:
        new_name = current_name.replace(find_str, replace_str)
        if not dry_run:
            try:
                if direct_name_update:
                    # Directly set the Name property on the element type inside a transaction
                    with revit.Transaction("Rename TextNoteType"):
                        elem_type.Name = new_name
                else:
                    doc.RenameElement(elem_type.Id, new_name)
                return current_name, new_name, False
            except Exception as e:
                logger.error("Could not rename '{}': {}".format(current_name, e))
                return current_name, None, True
        return current_name, new_name, False
    return None, None, False


def update_text_font_in_family(doc, family, font_from, font_to, width_factor,
                               name_find, name_replace, dry_run):
    result = []
    font_bip = DB.BuiltInParameter.TEXT_FONT
    width_bip = DB.BuiltInParameter.TEXT_WIDTH_SCALE
    family_doc = doc.EditFamily(family)
    types = DB.FilteredElementCollector(family_doc).OfClass(DB.ElementType).ToElements()

    tx = None
    try:
        if not dry_run:
            tx = revit.Transaction("Update Font/Width/Name in Family", family_doc)
            tx.__enter__()

        for et in types:
            updated = False
            font_param = et.get_Parameter(font_bip)
            old_font = font_param.AsString() if font_param else None
            if font_param and old_font == font_from:
                if not dry_run:
                    font_param.Set(font_to)
                updated = True
            width_param = et.get_Parameter(width_bip)
            if width_param:
                if not dry_run:
                    width_param.Set(width_factor)
                updated = True

            # In family editing, still use RenameElement (no direct update here)
            old_name, new_name, readonly = update_element_type_name(
                family_doc, et, name_find, name_replace, dry_run
            )
            if old_name and new_name:
                updated = True

            if updated:
                result.append((
                    et.FamilyName, old_font, font_to, width_factor,
                    old_name, new_name, readonly
                ))

    finally:
        if tx:
            tx.__exit__(None, None, None)
        family_doc.Close(False)

    if result and not dry_run:
        family_doc.LoadFamily(doc, FamilyLoaderOptionsHandler())

    return result


def update_text_types(doc, element_types, font_from, font_to, width_factor,
                      name_find, name_replace, dry_run):
    result = []
    font_bip = DB.BuiltInParameter.TEXT_FONT
    width_bip = DB.BuiltInParameter.TEXT_WIDTH_SCALE

    tx = None
    try:
        if not dry_run:
            tx = revit.Transaction("Update Font/Width/Name in Types", doc)
            tx.__enter__()

        for et in element_types:
            try:
                updated = False
                font_param = et.get_Parameter(font_bip)
                old_font = font_param.AsString() if font_param else None
                if font_param and old_font == font_from:
                    if not dry_run:
                        font_param.Set(font_to)
                    updated = True
                width_param = et.get_Parameter(width_bip)
                if width_param:
                    if not dry_run:
                        width_param.Set(width_factor)
                    updated = True

                # Use direct_name_update=True only for TextNoteType elements
                direct_update = isinstance(et, DB.TextNoteType)
                old_name, new_name, readonly = update_element_type_name(
                    doc, et, name_find, name_replace, dry_run, direct_name_update=direct_update
                )
                if old_name and new_name:
                    updated = True

                if updated:
                    result.append((
                        DB.Element.Name.GetValue(et), old_font,
                        font_to, width_factor, old_name, new_name, readonly
                    ))
            except Exception as e:
                logger.error("Error updating {}: {}".format(DB.Element.Name.GetValue(et), e))

    finally:
        if tx:
            tx.__exit__(None, None, None)

    return result


def main():
    doc = HOST_APP.doc
    uidoc = HOST_APP.uidoc

    font_names = sorted([f.Name for f in System.Drawing.FontFamily.Families])

    components = [
        Label("Find and Replace Font in Text Styles and Dimensions"),
        Separator(),
        Label("Find Font:"), ComboBox("font_from", options=font_names, default="Arial Narrow"),
        Label("Replace With Font:"), ComboBox("font_to", options=font_names, default="Arial"),
        Separator(),
        Label("Optional: Set Text Width Factor (1.0 = normal):"), TextBox("width_factor", default="1.0"),
        Separator(),
        Label("Type Name contains (find):"), TextBox("name_find", default=""),
        Label("Replace with:"), TextBox("name_replace", default=""),
        Separator(),
        Label("Elements to change:"),
        CheckBox("families", "Families", default=True),
        CheckBox("textnotes", "Text Note Types", default=True),
        CheckBox("dimensions", "Dimension Types", default=True),
        Separator(),
        CheckBox("dry_run", "Try Run Only (Preview Changes)", default=True),
        Button("OK"),
    ]

    form = FlexForm("Replace Font in Elements", components)
    form.show()
    if not form.values:
        alert("No values selected.")
        return

    font_from = form.values["font_from"]
    font_to = form.values["font_to"]
    width_factor_str = form.values.get("width_factor", "1.0")
    name_find = form.values.get("name_find", "")
    name_replace = form.values.get("name_replace", "")
    dry_run = form.values.get("dry_run", True)

    try:
        width_factor = float(width_factor_str)
    except:
        alert("Invalid width factor.")
        return

    output.print_md("# Replace **{}** → **{}**, Width: **{}**, Type-name: '{}' → '{}'{}"
                    .format(font_from, font_to, width_factor, name_find, name_replace,
                            " (DRY RUN)" if dry_run else ""))

    total = 0
    readonly = 0

    if form.values["families"]:
        families = [f for f in DB.FilteredElementCollector(doc).OfClass(DB.Family)
                    .ToElements() if f.IsEditable]
        output.print_md("## Level‑2: Family Types")
        pb = ProgressBar(cancellable=True)
        for i, fam in enumerate(families):
            if fam.IsInPlace:
                continue
            result = update_text_font_in_family(
                doc, fam, font_from, font_to, width_factor,
                name_find, name_replace, dry_run
            )
            for r in result:
                total += 1
                if r[6]:
                    readonly += 1
                output.print_md("🔤 {} | Font: {}→{}, Width: {}, Name: {}→{}"
                                .format(r[0], r[1], r[2], r[3], r[4] or "-", r[5] or "-"))
            if pb.cancelled:
                break
            pb.update_progress(i, len(families))

    if form.values["textnotes"]:
        types = DB.FilteredElementCollector(doc).OfClass(DB.TextNoteType).ToElements()
        output.print_md("## Text Note Types")
        result = update_text_types(doc, types, font_from, font_to, width_factor,
                                   name_find, name_replace, dry_run)
        for r in result:
            total += 1
            if r[6]:
                readonly += 1
            output.print_md("✏️ {} | Font: {}→{}, Width: {}, Name: {}→{}"
                            .format(r[0], r[1], r[2], r[3], r[4] or "-", r[5] or "-"))

    if form.values["dimensions"]:
        types = DB.FilteredElementCollector(doc).OfClass(DB.DimensionType).ToElements()
        output.print_md("## Dimension Types")
        result = update_text_types(doc, types, font_from, font_to, width_factor,
                                   name_find, name_replace, dry_run)
        for r in result:
            total += 1
            if r[6]:
                readonly += 1
            output.print_md("📐 {} | Font: {}→{}, Width: {}, Name: {}→{}"
                            .format(r[0], r[1], r[2], r[3], r[4] or "-", r[5] or "-"))

    output.print_md("---\n### ✅ Summary")
    output.print_md("- Total types processed: **{}**".format(total))
    output.print_md("- Read‑only rename attempts: **{}**".format(readonly))
    output.print_md("- Mode: **{}**".format("DRY RUN" if dry_run else "LIVE"))

    uidoc.RefreshActiveView()


if __name__ == "__main__":
    main()
