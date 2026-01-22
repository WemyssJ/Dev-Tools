# Boilerplate text
import clr

clr.AddReference("RevitServices")
import RevitServices
from RevitServices.Persistence import DocumentManager 

clr.AddReference("RevitAPI")
import Autodesk 
from Autodesk.Revit.DB import *

# Name Doc = Current doc/app/ui
doc = DocumentManager.Instance.CurrentDBDocument

# Define list/unwrap list functions
def uwlist(input):
    result = input if isinstance(input, list) else [input]
    return UnwrapElement(result)

# Preparing input from dynamo to revit
sheets = uwlist(IN[0])

# Get revision sequences and revisions
revSeqs = FilteredElementCollector(doc).OfClass(RevisionNumberingSequence).ToElements()
revIds  = Revision.GetAllRevisionIds(doc)
revs    = [doc.GetElement(i) for i in revIds]

# Set up Date lists
AllDates = []
DeDupDates = []
for r in revs:
	AllDates += [r.RevisionDate]
	if r.RevisionDate not in DeDupDates:
		DeDupDates += [r.RevisionDate]
		
NonUniqueDates = []
indexx = 0
for r in revs:
	
	if indexx == 0:
		indexx += 1
		continue
		
	if r.RevisionDate == revs[indexx -1].RevisionDate:
		if r.RevisionDate not in NonUniqueDates:
			NonUniqueDates += [r.RevisionDate] 
	indexx += 1

# Empty variable lists to store to
revSeqNames, revCharSeqs = [],[]
rowsOut = []

# Set up Variables
sep = "\t"
SeqNo = 0
SeqDate = 0

# Get sequence names and characters
for r in revs:
	# Get sequence
	rsId = r.RevisionNumberingSequenceId
	rs   = doc.GetElement(rsId)
	# Append the name and start a sequence
	revSeqNames.append(rs.Name)
	charSequence = []
	# Get sequence characters for numeric...
	if rs.NumberType == RevisionNumberType.Numeric:
		settings  = rs.GetNumericRevisionSettings()
		minDigits = settings.MinimumDigits
		prefix    = settings.Prefix
		suffix    = settings.Suffix
		for n in range(settings.StartNumber,99,1):
			char_str = str(n)
			pad_str  = char_str.rjust(minDigits,"0")
			char_seq = prefix + pad_str + suffix
			charSequence.append(char_seq)
	# ... or Alphanumeric
	else:
		settings = rs.GetAlphanumericRevisionSettings()
		prefix    = settings.Prefix
		suffix    = settings.Suffix
		for a in settings.GetSequence():
			char_seq = prefix + a + suffix
			charSequence.append(char_seq)
	# Append the character sequence
	revCharSeqs.append(charSequence)

#Check sheets for revs
for s in sheets:
	trackRevs = []
	sheetRevs = s.GetAllRevisionIds()
	rowOut = ""
	rowOut += s.SheetNumber + sep + s.Name + sep
	# For each revision in the document
	for i in revIds:
		# Check if the sheet has it
		DupeDateCounter = 0
		if i in sheetRevs:
			# Get the sequence Id name and get its name
			r    = doc.GetElement(i)
			rsId = r.RevisionNumberingSequenceId
			rs   = doc.GetElement(rsId)
			rsn  = rs.Name
			# Find the index of the sequence name
			i_sq = revSeqNames.index(rsn)
			# Find out how many times the sequence occured so far
			i_ch = trackRevs.count(rsn)
			# Find Seq no, revision date and reset ArtLocation to =
			SeqNo = r.SequenceNumber
			SeqDate = r.RevisionDate 
			ArtificialLocation = 0
			# Then track the sequence
			trackRevs.append(rsn)			
            
			# Check if sequence is a duplicated date
			if SeqDate in NonUniqueDates:
				#DupeDateCounter += 1
				# Find location of SeqDate in DeDupDates List. Set as ArtLocation 
				ArtificialLocation = DeDupDates.index(SeqDate)
				# Find location of last SeqDate in DeDupDates List.
				LastDupDateLocation = len(AllDates) - 1 - AllDates[::-1].index(SeqDate)
				# Add 1 because Seq start at 1, however Python Index start at 0
				ArtificialLocation += 1
				LastDupDateLocation += 1
				# Check if first occurance of dupe date
				if ArtificialLocation == SeqNo - DupeDateCounter:
					# true
					# Get the sequence character, then track the sequence
					d = revCharSeqs[i_sq][i_ch] #+ sep
					#increment dupe counter
					DupeDateCounter += 1
				else:
					#false
					d += ""

				#check if last occurance of dupe date
				if LastDupDateLocation == SeqNo - DupeDateCounter:
					# no output
					d = revCharSeqs[i_sq][i_ch] + sep
					DupeDateCounter += 1
				else:
					d = revCharSeqs[i_sq][i_ch]
					#increment dupe counter
					DupeDateCounter += 1
			else: 
				# If date is not a dupe date	
				# Get the sequence character, then track the sequence	
				d = revCharSeqs[i_sq][i_ch] + sep
		else:
			# Get the sequence Id name and get its name
			r    = doc.GetElement(i)
			rsId = r.RevisionNumberingSequenceId
			rs   = doc.GetElement(rsId)
			rsn  = rs.Name
			# Find Seq no, revision date and reset ArtLocation to =
			SeqNo = r.SequenceNumber
			SeqDate = r.RevisionDate 
			ArtificialLocation = 0
			LastDupDateLocation = 0
			# Then track the sequence
			if SeqDate in NonUniqueDates:
				#DupeDateCounter += 1
				# Find location of SeqDate in DeDupDates List. Set as ArtLocation 
				ArtificialLocation = DeDupDates.index(SeqDate)
				LastDupDateLocation = len(AllDates) - 1 - AllDates[::-1].index(SeqDate)
				# Add 1 because Seq start at 1, however Python Index start at 0
				ArtificialLocation += 1
				LastDupDateLocation += 1
				# Check if first occurance of dupe date
				if ArtificialLocation == SeqNo - DupeDateCounter:
					# true
					d = ""
					#increment dupe counter
					DupeDateCounter += 1
				else:
					# no output
					d = ""
				
				if LastDupDateLocation == SeqNo - DupeDateCounter:
					# no output
					d = "" + sep
					DupeDateCounter += 1
				else:
					d = "" #+ sep
					DupeDateCounter += 1
			else:
			# If Rev not on sheet, no output + tab
				d = "" + sep
		rowOut += d 
	# Add the value to the end
	rowsOut.append(rowOut)


# Create header
header = "Document No." + sep + "Document Name" + sep + sep.join(DeDupDates) + sep
rowsOut.insert(0,header)

# Preparing output to Dynamo
OUT = rowsOut