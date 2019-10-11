#!/usr/bin/python

"""
Hillary Elrick June 20th, 2019

Called when manually entering primers to place them in the genome using BLAST. Only returns exact hits.
"""
import sys
import os
import json
import cgi
sys.path.append('../..')
from classes.BlastDB import BlastDB

def main():
	print "Content-type: application/json\n\n"
	
	try:
		# get the ajax values	
		args = cgi.FieldStorage()	
		genome = args.getvalue('genome')
		# single primer passed using 'primer' arg	
		primer = [args.getvalue('primer')]
	except Exception, e:
		sys.exit("Problem with variables passed to function")

	#for testing
	#primers = ['CACACCGTCGGACCCTtg']
	#genome = 'mm10'
	#primers = ['GAAGACTTGGTTAGGGTTTGTGGAG', 'ACACACTCCCATTATGACAGGATC']	
	#primers = ['GGAGGGAGTTTCTCTGAGAGATTT']	
	#genome = 'mm10'
	#primers = ['CGTCTTCTTGAAGCTCCTCATT']
	#primers = ['CTGACTGCTTTGTTAGTGTGCA']
		
	if genome and primer:
		sys.stdout = open(os.devnull, 'w')
		primerBLAST = BlastDB(genome, primer, True) # identical hits only
		hits = primerBLAST.returnLocations()	
		sys.stdout = sys.__stdout__
		if len(hits[0]) > 1:
			print(json.JSONEncoder().encode(hits))
		else:
			print(json.JSONEncoder().encode([]))
	else:
		sys.exit("Arguments not passed to function")
	
if __name__ == "__main__":
	main()
