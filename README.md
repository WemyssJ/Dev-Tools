To Install:

1.	If you have previously installed pyRevit, please uninstall and **ENSURE** you have the latest version of Revit (2022.1.7, 2023.1.5, 2024.2.1  – Tried and Tested).
2.	If Revit is open, close entirely.
3.	Install pyRevit_4.8.16.24121_signed.exe (https://github.com/pyrevitlabs/pyRevit/releases/download/v4.8.16.24121%2B2117/pyRevit_4.8.16.24121_signed.exe).
4.	Copy "extensions.json", SAVED HERE and paste to (overwriting existing file): C:\Users\YOURUSERNAME\AppData\Roaming\pyRevit-Master\extensions. (AppData is hidden in files - ensure Hidden files are enabled in the "View" tab.
5.	Copy "Dynamo Revit" Folder, SAVED HERE and paste to (overwriting existing file): C:\Users\YOURUSERNAME\AppData\Roaming\Dynamo.
6.	Create a new project within Revit (this project won't be saved, therefore any name / template can be used).
7.	Navigate to pyRevit within the ribbon. On the left hand side click the pyRevit drop down > Extensions and install extension "BIMTools". Save to default location on C:\ Drive
8.	Close Revit entirely.
9.	Copy “pyRevit_config”, SAVED HERE and paste to (overwriting existing file): C:\Users\YOURUSERNAME\AppData\Roaming\pyRevit.
10.	Open a project and you should now have access to DevTools.




Version 1.0.00: Useful pyRevit tools + 'Export DocReg'', 'Strip Model', 'Pile E+N', 'Pile Renumbering', 'Disable Analytical', 'Quick Links' \
Version 1.0.01: 'Tag Align' and 'E+N+ZUpToDate' added \
Version 1.0.02: 'Pile Renumbering' reliance on GeniusLoci Removed, 'Disable Analytical' and 'Print Sheets'. moved to bin, PackagesUsed.txt added to all custom tools \
Version 1.0.03: 'Pile Renumbering' Now allows starting number and outputs number of piles renamed. 'Pile E+N' also outputs number of piles coordinated
Version 1.0.04: 'Pad Renumbering' added \
Version 1.0.05: 'Pile Renumbering' Now only renames STRUCTURAL FOUNDATIONS with a type name "Pile" rather than containing "Pile"  \
Version 1.0.06: Hooks removed (moved to BIMTools) \
Version 1.0.07: 'E+N+Z UpToDate' fixed \
Version 1.0.08: BIM Guidance and Revit 2024 quick links added \
Version 1.0.09: Strip Model now maintains '3D Coversheet', DocReg updated to suit new file naming protocol \
Version 1.0.10: Sync Views added \
Version 1.0.11: Strip Model improved. UI overhaul \
Version 1.0.12: Autodesk ID removed from strip model naming \
Version 1.0.13: Strip model naming reoganised\
Version 1.0.14: View/Sheet renaming added, Warnings added\
