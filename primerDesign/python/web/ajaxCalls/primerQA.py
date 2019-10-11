#!/usr/bin/python

"""
Hillary Elrick February 13th, 2018

Defintes the functions for performing in silico PCR using the locally installed dicey program. Called when
designing primers to check the amplicons and binding sites of a pair of primers.
"""

import sys
import ast
import json
import cgi
sys.path.append('../..')
from classes.Dicey import Dicey

def main():
	
	print "Content-type: application/json\n\n"

	try:
		# get the ajax values	
		args = cgi.FieldStorage()
		# array is passed using 'primers' arg
		primers = args.getvalue('primers')
		# javascript passes a string rep of the list, need to convert
		primers = ast.literal_eval(primers)	
		# get the genome we're using
		genome = args.getvalue('genome')
	except Exception, e:
		#pass
		sys.exit("Problem with variables passed to function")

	#genome = 'mm10'
	#primers = ['GAAGACTTGGTTAGGGTTTGTGGAG', 'ACACACTCCCATTATGACAGGATC']	
	# non specific primers for Ifit3
	#primers = ['CAGTCCTCTCTACTCTTTGGTCATG','AACCATTCAGCCACTCCTTTATCC']
	#primers = ['TCTACCTTCCAAGTCAGTCCTG','CATCTCCCTCCTCACCTTAGTC']

	if primers:
		primerQA = Dicey(primers, '50', genome)
		result = primerQA.runSequences()
		print(json.JSONEncoder().encode(result))
		primerQA.deleteTempFile()
	else:
		sys.exit("Arguments not passed to function")

	
if __name__ == "__main__":
	main()
