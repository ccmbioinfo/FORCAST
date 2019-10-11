#!/usr/bin/python
'''
Hillary Elrick

Used by AJAX call in manualPrimerEntry.js (Manual Primer Popup) when 'Add to Database' is clicked which
creates the primer mongo record out of values entered in the form and rewrites the Primer GFF
'''

import cgi
import sys
import os
import re
sys.path.append('../..')
from Config import Config

# map the internal dict keys to more descriptive values for error reporting
KEY_MAPPING = {
	'type': 'Primer Type',
	'leftprimer': 'Forward Primer',
	'leftTM': 'Forward Tm',
	'rightprimer': 'Reverse Primer',
	'rightTM': 'Reverse Tm'}


# need to store the primer pair with the guides it was designed for
def getAcceptedGuideIDs(ensid, dbConnection):
	guideIDs = []
	guideCollection = dbConnection.guideCollection
	acceptedGuides = guideCollection.find({"ENSID": ensid, "status" : "Accepted"})
	for guide in acceptedGuides:
		guideIDs.append(str(guide['_id']))

	if len(guideIDs) == 0 or len(guideIDs) > 4:
		print("Error with number of accepted guides. Please close this window and ensure that only 1-4 guides are marked as accepted.")

	return guideIDs


# format all the fields for the primer record
def formatRecord(primerRecord, genome):
	# add the accepted guides
	primerRecord["guides"] = {}
	primerRecord["guides"]["ids"] =  getAcceptedGuideIDs(primerRecord['ENSID'], genome)
	primerRecord["guides"]["rank"] = "manual"

	# organize the location fields
	parseLocation(primerRecord)

	# add blank notes and default status
	primerRecord["notes"] = ""
	primerRecord["status"] = "Accepted"


def parseLocation(primerRecord):
	# get the strand and chromosome from the left primer
	locationSearch = re.search(r"(chr[[0-9]{1,2}|X|Y|M]):([0-9]*)-[0-9]*:([+|\-])", primerRecord["left_genomicLocation"])
	if locationSearch:
		primerRecord["chr"] = locationSearch.group(1)
		primerRecord["left_genomicLocation"] = locationSearch.group(2)
		primerRecord["strand"] = locationSearch.group(3)
	else:
		print("Error parsing forward location string. Unexpected format")
		sys.exit()

	# parse out the start location from the right primer
	startSearch = re.search(r"(chr[[0-9]{1,2}|X|Y|M]):([0-9]*)-[0-9]*:[+|\-]", primerRecord["right_genomicLocation"])
	if startSearch:
		rightChromosome = startSearch.group(1)
		primerRecord["right_genomicLocation"] = startSearch.group(2)
	else:
		print("Error parsing reverse location string. Unexpected format")
		sys.exit()

	try:
		if primerRecord["chr"] != rightChromosome:
			print("The primers don't seem to be on the same chromosome")
			sys.exit()
		# TODO: Calculate 2nd product size for the EM primer
		primerRecord["productSize"] = str(abs(int(primerRecord["right_genomicLocation"]) - int(primerRecord["left_genomicLocation"])))
	except Exception, e:
		print("Problem calculating product size" + str(e))
		sys.exit()

	return


def addPrimerMongo(primerRecord, dbConnection):
	# get the primer collection from the connection to the db
	primerCollection = dbConnection.primerCollection

	# check if primer pair with that sequence exists
	samePairCount = primerCollection.find({"leftprimer" : primerRecord['leftprimer'], "rightprimer" : primerRecord['rightprimer']}).count()
	if samePairCount > 0:
		print("A primer pair with the same sequences already exists in the database. Record not added")
		sys.exit()
	else:
		#insert the record into the database
		primerCollection.insert(primerRecord)
		print("Successfully Added Primer Pair")

	return

def rewriteGFF(dbConnection, genome):
        try:
                sys.path.insert(0, os.path.join(dbConnection.ROOT_PATH,'customPython/'))
                import MongoHandler
                MongoHandler.writeGFF(genome)
        except Exception, e:
                print("Problem updating the gff file: " + str(e))

'''
#TODO: this will throw an error, need to get the genome argument
def rewriteGFF():
	try:
		sys.path.insert(0, os.path.join(Config.ROOT_PATH, 'customPython/'))
		import MongoHandler
		MongoHandler.writeGFF()
	except Exception, e:
		print("Problem updating the gff file: " + str(e))
'''

def main():
	print("Content-type: text/html\n")
	args = cgi.FieldStorage()

	primerRecord = {
		"batchName" : None,
		"ENSID" : None,
		"release" : None,
		"type" : None,
		"leftprimer" : None,
		"leftTM" : None,
		"leftGC" : None,
		"leftlen" : None,
		"left_genomicLocation" : None,
		"rightprimer" : None,
		"rightTM" : None,
		"rightGC" : None,
		"rightlen" : None,
		"right_genomicLocation" : None
	}
	try:
		primerRecord['batchName'] = args.getvalue('gene')
		primerRecord['ENSID'] = args.getvalue('ensid')
		primerRecord['release'] = args.getvalue('release')
		primerRecord['type'] = args.getvalue('type')
		primerRecord['leftprimer'] = args.getvalue('leftprimer')
		primerRecord['leftTM'] = args.getvalue('leftTM')
		primerRecord['leftGC'] = args.getvalue('leftGC')
		primerRecord['leftlen'] = args.getvalue('leftlen')
		primerRecord['left_genomicLocation'] = args.getvalue('left_genomicLocation')
		primerRecord['rightprimer'] = args.getvalue('rightprimer')
		primerRecord['rightTM'] = args.getvalue('rightTM')
		primerRecord['rightGC'] = args.getvalue('rightGC')
		primerRecord['rightlen'] = args.getvalue('rightlen')
		primerRecord['right_genomicLocation'] = args.getvalue('right_genomicLocation')
		genome = args.getvalue('genome')
	except Exception, e:
		print("Problem with calls to script " + str(e))

	#TODO: remove this is for testing
	#primerRecord = {'batchName': 'Pdlim7', 'rightprimer': 'AGTTAAGCTGTCTAAGCGGGAACGCC', 'rightTM': '55.8', 'rightlen': '26', 'leftTM': '56.4', 'leftGC': '53.85', 'type': 'WT', 'right_genomicLocation': 'chr17:45590698-45590723:+', 'release': '94', 'left_genomicLocation': 'chr17:45590950-45590925:-', 'rightGC': '53.85', 'leftprimer' : 'AGTCATGCTCAGAACCAGATGGCAGC', 'leftlen': '26'}

	for key, value in primerRecord.iteritems():
		if value is None:
			if key in KEY_MAPPING:
				print("Please define the property: " + KEY_MAPPING[key] + " before inserting primer record")
			else:
				print("Problem with call to script. Contact support. Value for " + key + " not defined by function")
			sys.exit()
	#format and then add the record
	try:
		# initialize db connection to the correct genome
                dbConnection = Config(genome)	
		formatRecord(primerRecord, dbConnection)
		addPrimerMongo(primerRecord, dbConnection)
		rewriteGFF(dbConnection, genome)
	except Exception, e:
		print("Error: " + str(e))


	return

if __name__ == "__main__":
	main()
