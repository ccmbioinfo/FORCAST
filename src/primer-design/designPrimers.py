#!/usr/bin/python3.7

"""
	Hillary Elrick September 2018

	This script will be called via ajax is passed a gene name, prompting the creation of a gene object
	or fetching of a gene object if it's already been created. It then designs primers for the guides associated
	with the gene in the database. It returns a table of potential primers for both EM and WT with some information
	about them (sequence, gc percent, tm etc.).
"""

import cgi
import os
import sys
import pickle

# import external classes based on relative file location
dir_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(dir_path, '../helpers'))
from Config import Config

from classes.Gene import Gene
from classes.Guide import Guide
from classes.Gene import returnError

def main():
	if 'REQUEST_METHOD' in os.environ:
		print("Content-Type: text/html\n")	
		args = cgi.FieldStorage()
		try:
			geneName = args.getvalue('gene')
			genome = args.getvalue('genome')
		except Exception as e:
			returnError(e)
			return
	else:
		if len(sys.argv) != 3:
			print("Please provide the genome of interest and a gene to design guides for.")
			print("The program will attempt a design for all accepted guides for the gene")
			sys.exit()
		else:
			genome = sys.argv[1]
			geneName = sys.argv[2]

	if not geneName or not genome:
		returnError("Required parameters not passed to script")	

	# create a gene object based on the current gene name and genome
	geneObj = Gene(geneName, genome)
	geneObj.writeAPE(False)  # creates the blank APE for the gene (False for no download link)

	# guide object designs primers for accepted guides stored in the database for a given gene
	guideObj = Guide(geneObj)
	guideObj.guideQA()  # preform QA on the guides
	print(guideObj.resultsTable)

	guideObj.writeDownloads()

if __name__ == "__main__":
	main()
