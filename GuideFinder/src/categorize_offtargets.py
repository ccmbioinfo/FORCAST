#!/usr/bin/env python3

"""
Hillary Elrick, August 7th, 2019

Accepts a dictionary of potential guides and their off-targets along with the rgen ID for the guide.
Categorizes the off-targets into intergenic, intronic, and exonic using the segments file for the passed genome.
"""

import os, sys, re
from subprocess import Popen, PIPE, DEVNULL
sys.path.append("/var/www/html/primerDesign/python")
from Config3 import Config
from itertools import product
import cfd_code.cfd_score_calculator3 as cfd


def getRgenRecord(rgenID, dbConnection):
	"""
	Based on the rgenID, fetch the rgen record
	"""
	rgenCollection = dbConnection.rgenCollection
	rgenRecord = rgenCollection.find({"rgenID": str(rgenID)})
	if rgenRecord.count() == 1:
		return rgenRecord.next()
	else:
		raise Exception("Invalid number of records returned from RGEN database for rgenID " + str(rgenID))
		return


def categorizeOffTargets(guideDict, rgenID, genome, batchID):
	"""
	Given the guideDict, rgenID, genome, and batch number, categorize
	the off-targets into 'intronic', 'intergenic', and 'exonic' using
	the segments.bed file for the genome
	"""
	# connect to database and get the rgen variables from id
	dbConnection = Config(genome)
	rgen = getRgenRecord(rgenID, dbConnection)
	# define how context categories should be mapped
	context = {"in": "intronic", "ig": "intergenic", "ex": "exonic"}
	# construct bed intersect command
	segmentsFile = os.path.join(dbConnection.ROOT_PATH, "jbrowse/data."+genome, "downloads", genome+".segments.bed")
	extendedBed = os.path.join(dbConnection.ROOT_PATH, "GuideFinder/tempfiles", str(batchID)+"_extended.bed")
	bedCommand = ["bedtools", "intersect", "-a", extendedBed, "-b", segmentsFile, "-wb"]
	p = Popen(bedCommand, stdin=PIPE, stdout=PIPE, stderr=PIPE)
	out, err = p.communicate()
	if err:
		sys.exit(err)
	
	categorized = []
	for line in out.splitlines():
		# assign every intersection to its off-target
		intersect = line.decode("utf-8").split("\t")
		guideID, location = intersect[3].split("_")
		for offTarget in guideDict[guideID]['offtargets']:
			if offTarget['loc'] == location:
				contextString = intersect[-1]
				# replace shorthand for full genomic context description 
				for c in context.keys():
					contextString = re.sub(c+":", context[c]+":", contextString)	
				# start the context string or append to the existing one
				offTarget['context'] = contextString if 'context' not in offTarget else str(offTarget['context']) + ", " + contextString	
	
	return guideDict


def main():
	print("Import categorize_offtargets to use the categorizeOffTarets function")


if __name__ == "__main__":
    main()
