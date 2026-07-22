"""Prints calculated hash values for each extension."""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens


__context__ = 'zero-doc'


from pyrevit import forms


test_panel_uuid = "c4e8f127-9d3b-4a71-b6e2-1f0d7c5a8b94"

forms.open_dockable_panel(test_panel_uuid)
