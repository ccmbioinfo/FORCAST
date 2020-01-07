#!/usr/bin/python

"""
Hillary Elrick February 4th, 2019

Class definition to ease & organize access to Dicey in silico PCR tool
"""

import sys
import re
import os
import subprocess
import time
import json

# get the global root path from the Config object
sys.path.append("..")
from Config import Config

class Dicey:
	"""
	Dicey is used to run in silico PCR on a pair of primers.
	Default temperature for the primers is 45C
	"""
	def __init__(self, sequences, temp='45', genome='mm10'):
		self.Config = Config()
		sys.path.insert(0, self.Config.DICEY_PATH)	
		assert len(sequences) == 2, "Exactly two primers required"
		self.sequences = sequences
		self.temp = temp # temperature
		self.genomePath = self.Config.DICEY_PATH+"/indexes/"+genome+"/"+genome+".fa.gz"
		self.tempfile = self.createTempFile()	
		self.diceyCommand = self.constructDiceyCommand()	

	
	def constructDiceyCommand(self):
		"""
		Returns the Dicey command with reference to the locally installed Primer3 in addition
		to the genome of interest and minimum temperature to consider for binding
		"""
		# base shell command 
		diceyCommand = [self.Config.DICEY]
		diceyCommand.append('search')

		# provide location of primer3 config directory
		diceyCommand.append('-i')
		diceyCommand.append(self.Config.PRIMER3_CONFIG)
		
		# add in the temperature
		diceyCommand.append('-c')
		diceyCommand.append(self.temp)

		# add in the genome
		diceyCommand.append('-g')
		diceyCommand.append(self.genomePath)

		# add in temp file
		diceyCommand.append(self.tempfile)

		return diceyCommand


	def createTempFile(self):
		filename = str(self.sequences[0])+"_"+str(self.sequences[1])+(time.strftime("%Y-%m-%d-%H:%M:%S"))
		f = open(os.path.join(self.Config.DICEY_PATH, "dicey_tempfiles", filename), "w+")
			
		faFormat = '>leftPrimer'
		faFormat += '\n' + str(self.sequences[0])
		faFormat += '\n>rightPrimer'
		faFormat += '\n' + str(self.sequences[1])	
	
		f.write(faFormat)
		f.close()	
		
		return f.name


	def deleteTempFile(self):
		if os.path.exists(self.tempfile):
			os.remove(self.tempfile)


	def runSequences(self):		
		diceyProcess = subprocess.Popen(self.diceyCommand, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
		(diceyOut, diceyErr) = diceyProcess.communicate()	

		try:
			# decode json
			jsonResult = json.loads(diceyOut)
			data = jsonResult['data']
		except Exception, e:
			print("Error reading Dicey results: "+str(e))
			return
		
		return data

	
