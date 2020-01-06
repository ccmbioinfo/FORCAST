#!/usr/bin/env python3

"""
Hillary Elrick, August 7th, 2019

Accepts a dictionary of potential guides and their off-targets along with the rgen ID for the guide.
Categorizes the off-targets into intergenic, intronic, and exonic using the segments file for the passed genome.
"""

import os, sys, re
from subprocess import Popen, PIPE, DEVNULL
from itertools import product
dir_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(dir_path, "../../primerDesign/python"))
from Config3 import Config


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
	# construct bed intersect command
	segmentsFile = os.path.join(dbConnection.ROOT_PATH, "jbrowse/data."+genome, "downloads", genome+".segments.bed")
	extendedBed = os.path.join(dbConnection.ROOT_PATH, "src/guide-finder/tempfiles", str(batchID)+"_extended.bed")
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
		if guideDict[guideID]['max_exceeded']:
			# don't care about categorizing these
			continue
		for offTarget in guideDict[guideID]['offtargets']:
			if offTarget['loc'] == location:
				contextString = str(intersect[-1])
				# start the context string or append to the existing one
				offTarget['context'] = formatContext('', contextString) if 'context' not in offTarget else formatContext(offTarget['context'], contextString)
	
	return guideDict


def formatContext(existingContext, newIntersection):
	""" given the existing bed intersect results, add the new intersection according to hierarchy/duplicate rules"""
	if newIntersection == 'exonic':
		if 'exonic' in existingContext:
			return existingContext
		elif 'intronic' in existingContext:
			return existingContext.replace('intronic', 'exonic/intronic') # recategorize
		else:
			return newIntersection + " | " + existingContext
	elif newIntersection == 'intronic':
		if 'intronic' in existingContext:
			return existingContext
		elif 'exonic' in existingContext:
			return existingContext.replace('exonic', 'exonic/intronic') # give more specific categorization 
		else:
			return newIntersection + " | " + existingContext
	elif newIntersection == 'intergenic':
		if existingContext != '':
			return existingContext
		else:
			return newIntersection
	else:
		# gene/ncRNA/pseudogene case
		if existingContext == '':
			return newIntersection
		elif '|' in existingContext:
			if existingContext.split(" | ")[1]:
				return existingContext + ", " + newIntersection
			else:
				return existingContext + newIntersection
		elif existingContext:
			return existingContext + ", " + newIntersection
		else:
			return existingContext


def main():
	print("Import categorize_offtargets to use the categorizeOffTarets function")


if __name__ == "__main__":
    main()
