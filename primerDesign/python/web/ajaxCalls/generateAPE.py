#!/usr/bin/python
import cgi
import sys
from bson.objectid import ObjectId

sys.path.append('../..')
from Config import Config
from Config import saveGeneObject
from classes.Gene import Gene
from classes.APE import APE

apeDir = "../../files/apeFiles"

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
		 
	'''	
	geneName = 'Jak1'
	genome = 'Rnor_6'
	found_all = True
	ids = ['5cc06dc12e18ca425a4fe11f', '5cc06e0c2e18ca42d8dfd9a9']
	geneName = 'Gt(ROSA)26Sor'
	genome = 'mm10'
	found_all = True
	ids = ['5c950f2669670c602fe90d34', '5c950fbd69670c61168b1c7c', '5c95146969670c63c8fe7b0d', '5cbe080a2e18ca0c501b29cd']
	'''
	
	if geneName and genome and found_all:
		# get a connection to the right db
		dbConnection = Config(genome)
		
		"""		
		# checks if there's a Gene object already created
		geneObj = Config.getGeneObject(geneName, genome)
		if not geneObj:
			''' this is for the cases where the saved gene object
			was deleted, or it was generated on a different server, 
			or the official gene symbol has been changed '''
			# don't want warnings because we need a url even if no protein-coding exons
			geneObj = Gene(geneName, genome, suppressWarnings=True)
			saveGeneObject(geneObj)
		"""
		
		geneObj = Gene(geneName, genome, suppressWarnings=True)
		
		# get all the guides passed in
		guideResults = getGuides(ids, dbConnection)
		
		# finds all the primers designed for this set of guides
		primerResults = findPrimers(ids, dbConnection)

		# creates an APE object using the gene, guides, and primers	
		APEObj = APE(None, None, [[geneObj], guideResults, primerResults])
				
		try:
			APEString = APEObj.addFeaturesMongo()
			filePath = APEObj.writeMongoAPE(APEString)
		except Exception, e:
			print str(e)

		print filePath
			
	else:
		print("Missing values passed to script: ") 
		if not geneName:
			print("No Gene Name")
		if not found_all:
			print("Error parsing guides")
		return	
	return	


if __name__ == "__main__":
	main()
