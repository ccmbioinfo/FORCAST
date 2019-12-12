#!/usr/bin/python
import cgi,sys,os
import csv
import bson
from bson.objectid import ObjectId
import pymongo
from pymongo import MongoClient
sys.path.append('../..')
from Config import Config

fileDir = "primerDesign/python/files/csvFiles"

def getGuides(ids, dbConnection):
	"""
	Gets guides from Mongo database using list of guide record ids
	"""
	guideCollection = dbConnection.guideCollection
	guideResults = []
	for curr_id in ids:
		guide = guideCollection.find_one({"_id": ObjectId(curr_id)})
		guideResults.append(guide)

	return guideResults


def findPrimers(ids, dbConnection):
	"""
	Gets primers from Mongo database that have been designed with this specific
	set of guides
	"""
	primerCollection = dbConnection.primerCollection
	primerResults = []
	primers = primerCollection.find({"guides.ids" : { "$size" : len(ids), "$all": ids }, "status" : "Accepted"})
	for primer in primers:
		primerResults.append(primer)
	return primerResults


def writeCSV(genome, geneName, ROOT_PATH, guideResults, primerResults):
	filename = str(geneName) + "-accepted_primers.csv"
	csv_genomeDir = os.path.join(ROOT_PATH, fileDir, genome)
	# check that the genome has a csv dir
	if not os.path.exists(csv_genomeDir):
		os.makedirs(csv_genomeDir)
	
	filepath = os.path.join(csv_genomeDir, filename)
	try:
		with open(filepath, mode='w') as csv_file:
			writer = csv.writer(csv_file, delimiter=",")
			writer.writerow(['Guides:'])
			writer.writerow(['Location','Sequence','PAM'])
			for g in guideResults:
				writer.writerow([str(g['guideLocation']), str(g['guideSeq']),str(g['pamSeq'])])
			writer.writerow([])	
			writer.writerow(['Primers:'])
			writer.writerow(['Primer Name', 'Sequence', 'Tm'])
			for record in primerResults:					
				writer.writerow([(str(geneName)+"_"+record['type'].lower()+"_F1"), record['leftprimer'], record['leftTM']])
				writer.writerow([(str(geneName)+"_"+record['type'].lower()+"_R1"), record['rightprimer'], record['rightTM']])
	except Exception, e:
		print("Error: " + str(e))
	
	return filename
				
		
def main():
	print("Content-type: text/html\n")	
	args = cgi.FieldStorage()
	try:
		geneName = args.getvalue('gene')
		genome = args.getvalue('genome')
		ids = []	
		found_all = False
		count = str(0)
		while not found_all:
			if count in args:
				ids.append(args.getvalue(count))
				count = str(int(count) + 1)
			else:
				found_all = True	
	except Exception, e:
		print("Problem with calls to script " + str(e))

	# get connection to database
	dbConnection = Config(genome)
	guideResults = getGuides(ids, dbConnection)
	primerResults = findPrimers(ids, dbConnection)
	filename = writeCSV(genome, geneName, dbConnection.ROOT_PATH, guideResults, primerResults)
	print os.path.join("files/csvFiles", genome, filename)
	return

if __name__ == "__main__":
	main()
