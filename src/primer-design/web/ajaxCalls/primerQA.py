#!/usr/bin/python

"""
Hillary Elrick February 13th, 2018

Defintes the functions for performing in silico PCR using the locally installed dicey program. Called when
designing primers to check the amplicons and binding sites of a pair of primers.
"""

import sys
import os
import ast
import json
import cgi

# import external classes based on relative file location
dir_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(dir_path, '../../../helpers'))
from Config import Config
sys.path.append(os.path.join(dir_path,'../..'))
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

	if primers:
		primerQA = Dicey(primers, '50', genome)
		result = primerQA.runSequences()
		print(json.JSONEncoder().encode(result))
		primerQA.deleteTempFile()
	else:
		sys.exit("Arguments not passed to function")

	
if __name__ == "__main__":
	main()
