#!/usr/bin/python3.7

'''
Hillary Elrick

Used by AJAX call in /src/primer-design/web/js/loadingPage.js which is attached to the
primer design popup. When user clicks the lock button on the Notes column to edit the guide
notes and then re-clicks it to lock the fields again, this script is triggered for every
guide that had its notes changed. It updates the database and rewrites the Guide GFF
'''

import cgi
import sys
import os
from bson.objectid import ObjectId

# import external classes based on relative file location
dir_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(dir_path, '../../../helpers'))
from Config import Config

def updateDB(guideID, genome, newNote, dbConnection):
	guideCollection = dbConnection.guideCollection

	if newNote is None:
		newNote = ""
	
	update_result = guideCollection.update_one({"_id": ObjectId(guideID)}, {'$set': {'Notes': newNote}})
	
	if update_result.matched_count != 1:
		print("Problem Updating Record, Incorrect number of guide records matched")	
	else:
		try:
			sys.path.insert(0,os.path.join(dbConnection.ROOT_PATH,'customPython/'))
			import MongoHandler			
			MongoHandler.writeGFF(genome)
			print("Successfully Updated Guide Note")
		except Exception as e:
			print(f"Problem writing gff file: {e}")\

def main():
	arg = cgi.FieldStorage()
	print('Content-Type: text/html\n')
	
	try:
		guideID = arg.getvalue("recordID")
		newNote = arg.getvalue("newValue")
		genome = arg.getvalue("genome")
	except Exception as e:
		print(f"Incorrect information passed to script: {e}")
		return	

	if genome:
		dbConnection = Config(genome)	
		updateDB(guideID, genome, newNote, dbConnection)
	else:
		print("No genome passed to script")

if __name__ == "__main__":
	main()
