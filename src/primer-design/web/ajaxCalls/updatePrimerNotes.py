#!/usr/bin/python3.7

'''
Hillary Elrick

Used by AJAX call in src/primer-design/web/js/loadingPage.js which is attached to the
primer design popup. This function is called when clicking the 'Update Notes' button
and accepts the primer record id and the new notes field. It updates the database and rewrites
the Primer GFF file
'''

import cgi
import sys
import os
from bson.objectid import ObjectId

# import external classes based on relative file location
dir_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(dir_path, '../../../helpers'))
from Config import Config

def updateDB(recordID, genome, newNotes, dbConnection):
	# get the primer collection
	primerCollection = dbConnection.primerCollection
	
	if newNotes is None:
		newNotes = ""
	
	update_result = primerCollection.update_one({"_id": ObjectId(recordID)}, {'$set':{'notes' : newNotes}})
	
	if update_result.matched_count != 1:
		print("Problem Updating Record, Incorrect number of primer records matched")
	else:
		try:
			sys.path.insert(0, os.path.join(dbConnection.ROOT_PATH, 'customPython/'))
			import MongoHandler
			MongoHandler.writeGFF(genome)
			print("Successfully Updated Notes")
		except Exception as e:
			print(f"Problem writing gff file: {e}")

def main():
	arg = cgi.FieldStorage()
	print ('Content-Type: text/html\n')
	
	try:
		recordID = arg.getvalue("record")
		newNotes = arg.getvalue("newNotes")
		genome = arg.getvalue("genome")
	except Exception as e:
		print(f"Incorrect information passed to script: {e}")
		return	

	if not recordID or not genome:
		print("Missing required values for script (recordID and/or genome)")
		return
	
	dbConnection = Config(genome)
	primerCollection = dbConnection.primerCollection
	updateDB(recordID, genome, newNotes, dbConnection)

if __name__ == "__main__":
	main()
