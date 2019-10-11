#!/usr/bin/python
'''
Hillary Elrick

Used by AJAX call in /primerDesign/python/web/js/loadingPage.js which is attached to the primer design popup.
When a user changes the status of a Guide, this script updates the database and rewrites the Guide GFF
'''

import cgi
import sys
import os
from bson.objectid import ObjectId
sys.path.append('../..')
from Config import Config


def updateDB(genome, recordID, newStatus, dbConnection):

	guideCollection = dbConnection.guideCollection	
	update_result = guideCollection.update_one({"_id": ObjectId(recordID)}, {'$set': {'status': newStatus}})
	
	if update_result.matched_count != 1:
		print("Problem Updating Record, Incorrect number of guide records matched")
	else:
		try:
			sys.path.insert(0,os.path.join(dbConnection.ROOT_PATH,'customPython/'))
			import MongoHandler			
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
		print("Required parameters not passed to script")
		return
	
	try:
		dbConnection = Config(genome)	
		updateDB(genome, recordID, status, dbConnection)
	except Exception as e:
		print("Error updating guide records: " + str(e))
		return


if __name__ == "__main__":
	main()
