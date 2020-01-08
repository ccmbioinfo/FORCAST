#!/usr/bin/python
'''
Hillary Elrick

Used by AJAX call in src/primer-design/web/js/loadingPage.js which is attached to the
primer design popup. When a user changes the status of a guide (either 'Accepted' or 'Rejected'),
this updates the record in the database and rewrites the Primer GFF.
'''
import cgi
import sys
import os
from bson.objectid import ObjectId

# import external classes based on relative file location
dir_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(dir_path, '../../../helpers'))
from Config import Config
import MongoHandler

def updateDB(recordID, genome, newStatus, dbConnection):
	# get the primer collection and update it
	primerCollection = dbConnection.primerCollection	
	update_result = primerCollection.update_one({"_id": ObjectId(recordID)}, {'$set':{'status' : newStatus}})
	
	if update_result.matched_count != 1:
		print("Problem Updating Record, Incorrect number of primer records matched")
	else:
		try:
			MongoHandler.writeGFF(genome)
		except Exception as e:
			print("Problem writing gff file: " + str(e))
			return
		print("Successfully updated the record")
	return

def main():
	arg = cgi.FieldStorage()
	print('Content-Type: text/html\n')
	
	try:
		recordID = arg.getvalue("record")
		status = arg.getvalue("newstatus")
		genome = arg.getvalue("genome")
	except Exception as e:
		print("Incorrect information passed to script: " + str(e))
		return	

	if not recordID or not status or not genome:
		print("Required information not passed to script")
		return

	dbConnection = Config(genome)	
	updateDB(recordID, genome, status, dbConnection)


if __name__ == "__main__":
	main()
