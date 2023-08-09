#!/usr/bin/python3.7

'''
Hillary Elrick

Used by AJAX call in /primer-design/web/js/loadingPage.js which is attached to the
primer design popup. This function is called when clicking the 'Add Primers to Database' button.
When the designPrimers.py script is initially run, it creates json files for the primers in the
jsonDir labelled with the gene symbol, rank, release, and type (i.e. WT or EM). Then, when a user selects
a given primer on the front end, this information is passed via ajax to this script which then locates the
correct json file and loads it into the database. Afterwards the the Primer GFF file is rewritten
'''

import cgi
import sys
import os
import json
# import external classes based on relative file location
dir_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(dir_path, '../../../helpers'))
from Config import Config

jsonDir = "../../files/jsonFiles"


def addToDatabase(dbConnection, geneName, release, primerPairs):
	primerCollection = dbConnection.primerCollection
	# iterate through dict of primer selections
	for key, value in primerPairs.items():
		if key == 'wtPair':
			primerType = "WT"
		elif key == 'emPair':
			primerType = "EM"
		else:
			print("Problem with primer selection")

		count = 0

		'''
		json files are stored with the ensembl release at the time of design appended 
		to the file name. Need to get the current ensembl release to find these files.
		'''
		import fetchEnsemblRelease		
		ens_release_num = fetchEnsemblRelease.getRelease()	
		fileFound = False
		while not fileFound:
			if int(release) > ens_release_num:
				print("Unable to find " + primerType + " file")
				return
			json_filename = geneName + "_" + release + "_"
			path = os.path.join(jsonDir, (json_filename + primerType + "-" + str(primerPairs[key]) + ".json"))
			try:
				fh = open(path, 'r')	
				fileFound = True
			except:
				release = str(int(release) + 1)	

		with open((path), 'r') as primerJSON:
			primerRecord = json.load(primerJSON)
			# attempt to insert record
			recordStatus = addPrimerMongo(primerCollection, primerRecord)
	
		if recordStatus == 1:
			print("Error: " + primerType + " Primer Already Exists in the Database")
		if recordStatus == 0:
			print(primerType + " Primer Successfully Added to Database")

# uses the dict to see if it's already been inserted		
def addPrimerMongo(primerCollection, primerRecord):
	'''
	Remove the status, geneName, and notes to see if any
	already exist in the database with an
	identical Sequence, Type, Details, etc.
	'''
	core_record = dict(primerRecord)
	del core_record['status']
	del core_record['batchName']
	del core_record['ENSID']
	try:
		del core_record['notes']
	except:
		# this is ok, it's just because the primer doesn't have notes
		# we should add them to the base record though
		primerRecord["notes"] = ""
		
	found_count = primerCollection.find(core_record).count()
	
	if found_count != 0:
		return 1  # it's already stored
	else:
		primerCollection.insert(primerRecord)
		return 0  # return success status code


def rewriteGFF(dbConnection, genome):
	try:
		sys.path.insert(0, os.path.join(dbConnection.ROOT_PATH,'customPython/'))
		import MongoHandler
		MongoHandler.writeGFF(genome)
	except Exception as e:
		print(f"Problem updating the gff file: {e}")		


def main():	
	print("Content-type: text/html\n")	
	
	args = cgi.FieldStorage()
	try:
		geneName = args.getvalue('gene')
		release = args.getvalue('release')
		genome = args.getvalue('genome')
		primerPairs = {}
		for pair in ['wtPair', 'emPair']:
			if args.getvalue(pair) and args.getvalue(pair) != 'NaN':
				primerPairs[pair] = args.getvalue(pair)
	except Exception as e:
		print(f"Problem with calls to script {e}")

	# example of how input variables should be formatted
	'''
	geneName = 'Ggh'
	release = '94'
	primerPairs = {'wtPair':0}
	genome = 'mm10'
	'''

	try:		
		if geneName and release and primerPairs and genome:
			# initialize db connection to the correct genome
			dbConnection = Config(genome)
			try:
				addToDatabase(dbConnection, geneName, release, primerPairs)			
				rewriteGFF(dbConnection, genome)
			except Exception as e:
				print(f"Error adding to Database: {e}")
			
		else:
			print("Missing values passed to script")
	except Exception as e:
		print(e)
			
	return


if __name__ == "__main__":
	main()
