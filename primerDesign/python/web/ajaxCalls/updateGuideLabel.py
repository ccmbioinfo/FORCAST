#!/usr/bin/python
'''
Hillary Elrick

Used by AJAX call in /primerDesign/python/web/js/loadingPage.js which is attached to the
primer design popup. When user clicks the lock button on the Label column to edit the guide
notes and then re-clicks it to lock the fields again, this script is triggered for every
guide that had its label changed. It updates the database and rewrites the Guide GFF
'''

import cgi
import sys
import os
from bson.objectid import ObjectId
sys.path.append('../..')
from Config import Config


def updateDB(guideID, genome, newLabel, dbConnection):
	
	guideCollection = dbConnection.guideCollection
	
	if newLabel is None:
		newLabel = ""
	
	update_result = guideCollection.update_one({"_id": ObjectId(guideID)}, {'$set':{'label' : newLabel}})
	
	if update_result.matched_count != 1:
		print("Problem Updating Record, Incorrect number of guide records matched")	
	else:
		try:
			sys.path.insert(0, os.path.join(dbConnection.ROOT_PATH,'customPython/'))
			import MongoHandler
			MongoHandler.writeGFF(genome)
		except Exception as e:
			print("Problem writing gff file: " + str(e))
			return
		print("Successfully Updated Guide Label")
	return


def main():
	arg = cgi.FieldStorage()
	print('Content-Type: text/html\n')

	try:
		guideID = arg.getvalue("recordID")
		newLabel = arg.getvalue("newValue")
		genome = arg.getvalue("genome")
	except Exception as e:
		print("Incorrect information passed to script: " + str(e))
		return	

	if not guideID or not genome:
		print("Required parameters not passed to script (guideID and/or genome)")
		return 

	dbConnection = Config(genome)
	updateDB(guideID, genome, newLabel, dbConnection)


if __name__ == "__main__":
	main()
