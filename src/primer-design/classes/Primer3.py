#!/usr/bin/python3.7

"""
Hillary Elrick April 22nd, 2019

Class definition for interfacing to installed primer3 program using pre-defined settings files
"""

import sys
import re
import os
from subprocess import Popen, PIPE

from Gene import returnError
sys.path.append("..")
from Config import Config

class Primer3:
	"""
	Primer3 is used to design primers
	"""
	def __init__(self):
		# connect to the primer3 conf file and create dict of settings
		self.Config = Config()
		# using the primer3 settings files (as defined in the Config object), construct dictionary of settings
		self.settingsDict = self.loadPrimer3Settings()

	def loadPrimer3Settings(self):
		# settings dict is 2d dictionary with following structure:
		"""
		settingsDict = {
			'0': {'filepath': 'pathToFile',
			      'desc': ''},
			'1': {'filepath': 'pathToFile',
			      'desc': 'Description of changes'}
			etc...
		}
		"""
		settingsDict = {}
		# open the primer3 settings conf file
		f = open(self.Config.PRIMER3_SETTINGS, 'r')
		# the settings path files are relative to the .conf file
		settings_path_prefix = os.path.dirname(self.Config.PRIMER3_SETTINGS)
		for line in f:
			'''
			If the need to specify design settings per genome arises, can
			use the below regex which will match the settings files prefixed
			by 'genome_'. The genome will then be group(1) of the match and 
			the attempt number group(2). If this need arises, the Primer3
			object will require the genome to be passed to its constructor. 
			For now, all genomes use the same primer design settings.	
			'''
			#file_match = re.match(r"(^[^_]+)_ATTEMPT_([0-9]*)_FILE=", line)
			#desc_match = re.match(r"(^[^_]+)_ATTEMPT_([0-9]*)_DESC=", line)
			file_match = re.match(r"^ATTEMPT_([0-9]*)_FILE=", line)
			desc_match = re.match(r"^ATTEMPT_([0-9]*)_DESC=", line)
			# get the info after the '=' sign (if there is one)
			if '=' in line:
				value = line.split('=')[1].strip("\"'\n")
			else:
				continue
			if file_match:
				attemptNum = file_match.group(1)
				if attemptNum in settingsDict:
					settingsDict[attemptNum]['filepath'] = os.path.join(settings_path_prefix, value)
				else:
					settingsDict[attemptNum] = {}
					settingsDict[attemptNum]['filepath'] = os.path.join(settings_path_prefix, value)
			elif desc_match:
				attemptNum = desc_match.group(1)
				if attemptNum in settingsDict:
					settingsDict[attemptNum]['desc'] = value
				else:
					settingsDict[attemptNum] = {}
					settingsDict[attemptNum]['desc'] = value
	
		return settingsDict
	
	
	def createPrimer3Input(self, primer, sequence, guideObject, targetSecondGuide=False):
		"""
		Create the input files for Primer3, it contains three lines:
		SEQUENCE_ID=(i.e. Gene1_WT or Gene1_EM)
		SEQUENCE_TEMPLATE=(target sequence plus 1000bp on either side)
		SEQUENCE_TARGET=(region the primers should target)
		WT file has the entire sequence and a target of either:
			1) the first guide sequence if there are two guides
			2) the first excised region if there are four guides
		EM file has the sequence minus the excised region and a target of either:
			1) the (only) excised region if there are two guides
			2) the largest excised region if there are four guides
		"""
		fileLines = []
		if primer == 'WT':
			# pre-process sequence to cut down computation times for primer3
			# 1000bp on start and end of target sequence is passed to primer3
			if not targetSecondGuide:
				# usual case
				trimStart = guideObject.wtTarget[0] - 1000
				startTarget = 1000
				trimEnd = guideObject.wtTarget[1] + 1000
					
				# if there are two guides, the primer should be picked within the excised region
				if len(guideObject.gRNAs) == 2:
					# cut off input sequence at 2nd guide's end
					trimEnd = guideObject.gRNAs[1][8]
				if len(guideObject.gRNAs) == 3 or len(guideObject.gRNAs) == 4:
					# cut off input sequence at 3rd guide's cutsite
					trimEnd = guideObject.getCut(guideObject.gRNAs[2])
			else:
				# indicates the target should be the second gRNA
				trimStart = guideObject.gRNAs[1][7] - 1000
				startTarget = 1000
				trimEnd = guideObject.gRNAs[1][8] + 1000
					
			if trimStart <= 0:
				trimStart = 0
				startTarget = guideObject.wtTarget[0]
			if trimEnd >= len(sequence):
				trimEnd = len(sequence)

			trimmed_sequence = sequence[trimStart: trimEnd]

			fileLines.append("SEQUENCE_ID=" + guideObject.super.symbol + "_" + primer)
			fileLines.append("SEQUENCE_TEMPLATE=" + trimmed_sequence)
			length = abs(guideObject.wtTarget[1] - guideObject.wtTarget[0]) + 1  # end of target - start of target
			if guideObject.emTarget is None:
				# if there isn't an em target, this is a single guide design, so a 170 bp
				# buffer should be added to the sequence target
				fileLines.append("SEQUENCE_TARGET=" + str(startTarget - 170) + "," + str(340))
			else:
				fileLines.append("SEQUENCE_TARGET=" + str(startTarget) + "," + str(length))
			fileLines.append("=")

			# store the trim start for later use
			guideObject.wtTrimStart = trimStart
		elif primer == 'EM':
			fileLines.append(f"SEQUENCE_ID={guideObject.super.symbol}_{primer}")
			# remove the target from the excised sequence
			excisedSequence = sequence[:guideObject.emTarget[0]] + sequence[guideObject.emTarget[1]:]

			# trim excised sequence
			trimStart = guideObject.emTarget[0] - 1000
			startTarget = 1000
			trimEnd = guideObject.emTarget[1] + 1000
			if trimStart < 0:
				trimStart = 0
				startTarget = guideObject.emTarget[0]
			if trimEnd > len(excisedSequence):
				trimEnd = len(excisedSequence)

			trimmed_excisedSequence = excisedSequence[(trimStart): (trimEnd)]

			fileLines.append("SEQUENCE_TEMPLATE=" + trimmed_excisedSequence)
			# add a 150bp buffer on either side of the excised sequence for the target
			fileLines.append("SEQUENCE_TARGET=" + str(startTarget - 149) + "," + str(300))
			fileLines.append("=")

			# store trim start
			guideObject.emTrimStart = trimStart

		filepath = os.path.join(self.Config.PRIMER3_DIR, f"{primer}_{guideObject.super.symbol}_input")
		try:
			with open(filepath, 'w') as inputfile:
				for line in fileLines:
					print(line, file=inputfile)
		except Exception as e:
			returnError("Problem creating Primer3 input file: " + str(e))

		return filepath

	def attemptDesign(self, guideObject, primerType):
		"""
		Using primer3 and the predefined settings files, attempt to design primers and parse the results
		"""
		if not guideObject.emTarget and primerType == 'EM':
			# handling the single guide case
			return None, None
		htmlResult = ''
		foundPrimers = False
		attemptNumber = 0
		sequence = guideObject.super.sequence	
		numRetrys = len(self.settingsDict)
	
		while not foundPrimers and attemptNumber < numRetrys:		
			# create the input file to primer3			
			primer3Input = self.createPrimer3Input(primerType, sequence, guideObject)
			# grab the correct settings file
			settingsFile = self.settingsDict[str(attemptNumber)]['filepath']
			# construct the command
			p = Popen(self.Config.PRIMER3 + ' --p3_settings_file="' + settingsFile + '" < ' + primer3Input, shell=True, stdout=PIPE, stderr=PIPE, encoding="utf-8")
			stdout, stderr = p.communicate()
			if stderr:
				returnError(stderr)
			# parse the result	
			primerDict = self.parsePrimers(stdout, primerType, guideObject)
			foundCount = len(primerDict)
			if foundCount == 0:
				# if the design was for wt primers with 2 guides, can target second guide before changing settings
				if len(guideObject.gRNAs) == 2 and primerType == 'WT':
					primerDict = self.targetSecond(sequence, guideObject, attemptNumber)
					if len(primerDict) > 0:
						foundPrimers = True
					
				# move on to the next attempt settings
				attemptNumber += 1
				if attemptNumber == numRetrys:
				 	return primerDict, htmlResult
				try:
					retryDesc = str(self.settingsDict[str(attemptNumber)]['desc'])
				except Exception:
					# nothing defined, set to blank string
					retryDesc = ''
				
				htmlResult += ('<p id="retryText" class="text-danger">'+primerType+' Retry '+str(attemptNumber)+': '+retryDesc+'</p>')
			else:
				foundPrimers = True

		return primerDict, htmlResult

	def targetSecond(self, sequence, guideObject, attemptNumber):
		"""
		If the targeting for WT primers on the first guide of a 2 guide design fails, design around the second
		"""
		primerType = 'WT' # only the wt primers have this option
		
		# create input file to primer3. True indicates that the second guide should be targeted
		primer3Input = self.createPrimer3Input(primerType, sequence, guideObject, True)
		# grab the correct settings file
		settingsFile = self.settingsDict[str(attemptNumber)]['filepath']
		# construct the command
		p = Popen(self.Config.PRIMER3 + ' "--p3_settings_file="' + settingsFile + '" < ' + primer3Input, shell=True, stdout=PIPE, stderr=PIPE, encoding="utf-8")
		stdout, stderr = p.communicate()
		# parse the result
		primerDict = self.parsePrimers(stdout, primerType, guideObject)
		
		return primerDict
				
	
	# get the primers written to the primer3 outputfile and puts the relevant info into a dictionary
	def parsePrimers(self, primer3_output, primer, guideObject):
		primerDict = {}
		for line in primer3_output.split("\n"):
			# perform searches
			sequenceSearch = re.search("^PRIMER_(LEFT|RIGHT)_([0-9])_SEQUENCE=(.*)", line)
			startSearch = re.search("^PRIMER_(LEFT|RIGHT)_([0-9])=(.*)", line)
			tmSearch = re.search("^PRIMER_(LEFT|RIGHT)_([0-9])_TM=(.*)", line)
			gcSearch = re.search("^PRIMER_(LEFT|RIGHT)_([0-9])_GC_PERCENT=(.*)", line)
			sizeSearch = re.search("PRIMER_PAIR_([0-9])_PRODUCT_SIZE=(.*)", line)

			# see if line is a sequence line
			if sequenceSearch:
				pairNum = sequenceSearch.group(2)
				if pairNum not in primerDict:
					primerDict[pairNum] = {}
					primerDict[pairNum]['type'] = primer
				if sequenceSearch.group(1) == 'LEFT':
					primerDict[pairNum]['leftprimer'] = sequenceSearch.group(3)
				elif sequenceSearch.group(1) == 'RIGHT':
					primerDict[pairNum]['rightprimer'] = sequenceSearch.group(3)
			# if line matched the start line pattern
			elif startSearch:
				pairNum = startSearch.group(2)
				if pairNum not in primerDict:
					primerDict[pairNum] = {}
					primerDict[pairNum]['type'] = primer
				start, length = startSearch.group(3).split(",")

				# convert trimmed start to APE start
				if primer == 'WT':
					start = str(guideObject.wtTarget[0] - 1000 + int(start))
				elif primer == 'EM':
					start = str(guideObject.emTarget[0] - 1000 + int(start))

				if startSearch.group(1) == 'LEFT':
					primerDict[pairNum]['leftstart'] = start
					primerDict[pairNum]['leftlen'] = length
				elif startSearch.group(1) == 'RIGHT':
					primerDict[pairNum]['rightstart'] = start
					primerDict[pairNum]['rightlen'] = length
			# if line matched the temperature line pattern
			elif tmSearch:
				pairNum = tmSearch.group(2)
				if pairNum not in primerDict:
					primerDict[pairNum] = {}
					primerDict[pairNum]['type'] = primer
				if tmSearch.group(1) == 'LEFT':
					primerDict[pairNum]['leftTM'] = tmSearch.group(3)
				elif tmSearch.group(1) == 'RIGHT':
					primerDict[pairNum]['rightTM'] = tmSearch.group(3)
			# if line matched the gc line pattern
			elif gcSearch:
				pairNum = gcSearch.group(2)
				if pairNum not in primerDict:
					primerDict[pairNum] = {}
					primerDict[pairNum]['type'] = primer
				if gcSearch.group(1) == 'LEFT':
					primerDict[pairNum]['leftGC'] = gcSearch.group(3)
				elif gcSearch.group(1) == 'RIGHT':
					primerDict[pairNum]['rightGC'] = gcSearch.group(3)
			# if line matched the product size line pattern	
			elif sizeSearch:
				pairNum = sizeSearch.group(1)
				if pairNum not in primerDict:
					primerDict[pairNum] = {}
					primerDict[pairNum]['type'] = primer
				primerDict[pairNum]['productSize'] = sizeSearch.group(2)

		return primerDict

