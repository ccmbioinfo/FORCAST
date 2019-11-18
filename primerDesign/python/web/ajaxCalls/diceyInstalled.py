#!/usr/bin/python

"""
Hillary Elrick February 13th, 2018

Defintes the functions for performing in silico PCR using the locally installed dicey program. Called when
designing primers to check the amplicons and binding sites of a pair of primers.
"""

import sys
import os
import json
import cgi
sys.path.append('../..')
from Config import Config
from classes.Dicey import Dicey

def main():
	
	print "Content-type: application/html\n"
	
	try:
		# get the ajax values
		args = cgi.FieldStorage()
		# get genome variable
		genome = args.getvalue('genome')
	except Exception, e:
		sys.exit("Problem fetching genome variable passed to function")
	
	if not genome:
		print("Genome not passed to script")
		return

	dbConnection = Config(genome)
	if os.path.isfile(os.path.join(dbConnection.ROOT_PATH,"dependencies/dicey/indexes/"+genome+"/"+genome+".fa.fm9")):
		print "1"
	else:
		print "0"
	
	return


if __name__ == "__main__":
	main()
