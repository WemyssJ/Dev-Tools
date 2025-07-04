# -*- coding: utf-8 -*-
"""
Checks github for update
Clones a panel to the Modify tab when a document is opened.
Creates an API endpoint to select an element by ID in a specific 3D view.
"""

import clr
clr.AddReference('AdWindows')
import Autodesk.Windows as AdWindows

# Add Windows Forms reference for window focusing
clr.AddReference('System.Windows.Forms')
from System.Windows.Forms import SendKeys

from pyrevit import HOST_APP, routes
from System import EventHandler
from Autodesk.Revit.DB import (
    Events, ElementId, Transaction, View3D, ViewFamilyType,
    FilteredElementCollector, BoundingBoxXYZ,
    ViewFamily, XYZ
)
from Autodesk.Revit.UI import UIDocument
from System.Collections.Generic import List
from pyrevit.coreutils import logger

from pyrevit import forms
import core


# Toast notify for new updates
try:
    if core.update_needed() == True:
        forms.toaster.send_toast("New update for DevTools extension available: {}".format(core.get_git_version()))
    else:
        pass
except Exception:
    pass


# Create a logger instance for this script
script_logger = logger.get_logger('switchback_api')

def find_and_clone_target_panel1():
    ribbon = AdWindows.ComponentManager.Ribbon
    if not ribbon:
        return
    
    # Find the Modify tab
    target_tab = next((tab for tab in ribbon.Tabs 
                      if tab.Title == "Modify" and tab.IsVisible), None)
    
    if not target_tab:
        return
        
    # Find the source target panel
    source_panel = None
    for tab in ribbon.Tabs:
        if not tab.IsVisible:
            continue
        for panel in tab.Panels:
            if panel.Source and "Test Button" == panel.Source.Title:
                source_panel = panel
                break
        if source_panel:
            break
            
    if not source_panel:
        return
        
    # Check if panel already exists in Modify tab
    if any(panel.Source and panel.Source.Title == source_panel.Source.Title 
           for panel in target_tab.Panels):
        return
        
    # Clone panel to Modify tab
    target_tab.Panels.Add(AdWindows.RibbonPanel())
    new_panel = target_tab.Panels[target_tab.Panels.Count - 1]
    new_panel.Source = source_panel.Source.Clone()
    new_panel.IsEnabled = True

def find_and_clone_target_panel2():
    ribbon = AdWindows.ComponentManager.Ribbon
    if not ribbon:
        return
    
    # Find the Modify tab
    target_tab = next((tab for tab in ribbon.Tabs 
                      if tab.Title == "geeWiz" and tab.IsVisible), None)
    
    if not target_tab:
        return
        
    # Find the source target panel
    source_panel = None
    for tab in ribbon.Tabs:
        if not tab.IsVisible:
            continue
        for panel in tab.Panels:
            if panel.Source and "System" == panel.Source.Title:
                source_panel = panel
                break
        if source_panel:
            break
            
    if not source_panel:
        return
        
    # Check if panel already exists in Modify tab
    if any(panel.Source and panel.Source.Title == source_panel.Source.Title 
           for panel in target_tab.Panels):
        return
        
    # Clone panel to Modify tab
    target_tab.Panels.Add(AdWindows.RibbonPanel())
    new_panel = target_tab.Panels[target_tab.Panels.Count - 1]
    new_panel.Source = source_panel.Source.Clone()
    new_panel.IsEnabled = True

def find_and_clone_target_panel3():
    ribbon = AdWindows.ComponentManager.Ribbon
    if not ribbon:
        return
    
    # Find the Modify tab
    target_tab = next((tab for tab in ribbon.Tabs 
                      if tab.Title == "geeWiz" and tab.IsVisible), None)
    
    if not target_tab:
        return
        
    # Find the source target panel
    source_panel = None
    for tab in ribbon.Tabs:
        if not tab.IsVisible:
            continue
        for panel in tab.Panels:
            if panel.Source and "Quality Assurance" == panel.Source.Title:
                source_panel = panel
                break
        if source_panel:
            break
            
    if not source_panel:
        return
        
    # Check if panel already exists in Modify tab
    if any(panel.Source and panel.Source.Title == source_panel.Source.Title 
           for panel in target_tab.Panels):
        return
        
    # Clone panel to Modify tab
    target_tab.Panels.Add(AdWindows.RibbonPanel())
    new_panel = target_tab.Panels[target_tab.Panels.Count - 1]
    new_panel.Source = source_panel.Source.Clone()
    new_panel.IsEnabled = True

def find_and_clone_target_panel4():
    ribbon = AdWindows.ComponentManager.Ribbon
    if not ribbon:
        return
    
    # Find the Modify tab
    target_tab = next((tab for tab in ribbon.Tabs 
                      if tab.Title == "geeWiz" and tab.IsVisible), None)
    
    if not target_tab:
        return
        
    # Find the source target panel
    source_panel = None
    for tab in ribbon.Tabs:
        if not tab.IsVisible:
            continue
        for panel in tab.Panels:
            if panel.Source and "Model Management" == panel.Source.Title:
                source_panel = panel
                break
        if source_panel:
            break
            
    if not source_panel:
        return
        
    # Check if panel already exists in Modify tab
    if any(panel.Source and panel.Source.Title == source_panel.Source.Title 
           for panel in target_tab.Panels):
        return
        
    # Clone panel to Modify tab
    target_tab.Panels.Add(AdWindows.RibbonPanel())
    new_panel = target_tab.Panels[target_tab.Panels.Count - 1]
    new_panel.Source = source_panel.Source.Clone()
    new_panel.IsEnabled = True

def find_and_clone_target_panel5():
    ribbon = AdWindows.ComponentManager.Ribbon
    if not ribbon:
        return
    
    # Find the Modify tab
    target_tab = next((tab for tab in ribbon.Tabs 
                      if tab.Title == "geeWiz" and tab.IsVisible), None)
    
    if not target_tab:
        return
        
    # Find the source target panel
    source_panel = None
    for tab in ribbon.Tabs:
        if not tab.IsVisible:
            continue
        for panel in tab.Panels:
            if panel.Source and "Drawing Tools" == panel.Source.Title:
                source_panel = panel
                break
        if source_panel:
            break
            
    if not source_panel:
        return
        
    # Check if panel already exists in Modify tab
    if any(panel.Source and panel.Source.Title == source_panel.Source.Title 
           for panel in target_tab.Panels):
        return
        
    # Clone panel to Modify tab
    target_tab.Panels.Add(AdWindows.RibbonPanel())
    new_panel = target_tab.Panels[target_tab.Panels.Count - 1]
    new_panel.Source = source_panel.Source.Clone()
    new_panel.IsEnabled = True

def find_and_clone_target_panel6():
    ribbon = AdWindows.ComponentManager.Ribbon
    if not ribbon:
        return
    
    # Find the Modify tab
    target_tab = next((tab for tab in ribbon.Tabs 
                      if tab.Title == "geeWiz" and tab.IsVisible), None)
    
    if not target_tab:
        return
        
    # Find the source target panel
    source_panel = None
    for tab in ribbon.Tabs:
        if not tab.IsVisible:
            continue
        for panel in tab.Panels:
            if panel.Source and "Other" == panel.Source.Title:
                source_panel = panel
                break
        if source_panel:
            break
            
    if not source_panel:
        return
        
    # Check if panel already exists in Modify tab
    if any(panel.Source and panel.Source.Title == source_panel.Source.Title 
           for panel in target_tab.Panels):
        return
        
    # Clone panel to Modify tab
    target_tab.Panels.Add(AdWindows.RibbonPanel())
    new_panel = target_tab.Panels[target_tab.Panels.Count - 1]
    new_panel.Source = source_panel.Source.Clone()
    new_panel.IsEnabled = True


# Run on startup / reload
find_and_clone_target_panel1()
find_and_clone_target_panel2()
find_and_clone_target_panel3()
find_and_clone_target_panel4()
find_and_clone_target_panel5()
find_and_clone_target_panel6()

# Run on document open on event
def doc_opening_handler(sender, args):
    find_and_clone_target_panel1()
    find_and_clone_target_panel2()
    find_and_clone_target_panel3()
    find_and_clone_target_panel4()
    find_and_clone_target_panel5()
    find_and_clone_target_panel6()

# Register the event handler to load the target panel when a document is opened
HOST_APP.app.DocumentOpening += \
    EventHandler[Events.DocumentOpeningEventArgs](
        doc_opening_handler
    )
