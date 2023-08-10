#!/usr/bin/python3.7
"""
Hillary Elrick August 2018

Stores functions and attributes related to designing primers based on Guides.
Child of the Gene class for the gene the guides were created for, uses
functions for generating APE files from the APE class, and attributes to
access the Mongo Database via the static Config class.
"""

import os
import sys
import re
import csv
import json
import requests
from collections import OrderedDict

# import classes based on relative file location
dir_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(dir_path)
from Gene import Gene
from Gene import returnError
from Config import Config
from APE import APE
from Primer3 import Primer3

server = "https://rest.ensembl.org"

class Guide(Gene):
	primer3Dir = os.path.join(dir_path, "../files/primer3Files")
	primer3SettingsDir = os.path.join(dir_path, "../files/primer3Files/SETTINGS")
	apeDir = os.path.join(dir_path,"../files/apeFiles")
	csvDir = os.path.join(dir_path,"../files/csvFiles")
	jsonDir = os.path.join(dir_path,"../files/jsonFiles")

	def __init__(self, geneObj):
		self.success = [False, False]
		self.wtTrimStart = 0
		self.emTrimStart = 0
		self.super = geneObj  # parent gene object
		self.gRNAs, self.gRNADict = self.fetchGuides()
		self.addCutsites()  # add cutsites and direction to self.gRNAs
		self.labelGuides()  # add labels to self.gRNAs
		'''
			self.gRNAs is an array of the guides with the indices corresponding to the following order and sorted on their start:

			guideScore(0), guideSeq(1), guideGenomicStart(2), pamSeq(3), pamGenomicStart(4), otDesc(5), Notes(6),
			start(7), end(8), direction(9), label(10)
		'''
		self.startExcise, self.lengthExcise, self.wtTarget, self.emTarget = self.setTargets()
		self.wtPrimers, self.emPrimers, self.resultsTable = self.primer3Design()

		# create an APE object using the guide object
		self.APEObj = APE(None, self, None)
		self.fileDictionary = self.APEObj.addFeatures()
		self.checkSuccess()
		self.guideQA

	def guideQA(self):
		# get the genomic excised sequence location (the guide array is sorted)
		earliestStart = self.gRNAs[0][2]
		latestEnd = 0
		for guide in self.gRNAs:
			latestEnd = guide[2]

		# reverse if on opposite strand
		if earliestStart > latestEnd:
			earliestStart, latestEnd = latestEnd, earliestStart

		# get the regulatory elements within the excised sequence
		ext = "/overlap/region/"+self.super.Config.organismName+"/%s:%s-%s?feature=transcript;feature=regulatory;feature=other_regulatory" % (
			self.super.chromosome, earliestStart, latestEnd)
		try:
			regulatoryRequest = requests.get(server + ext, headers={"Content-Type": "application/json"}, timeout=15)
		except requests.exceptions.Timeout:
			returnError("The Ensembl Rest API is not responding (https://rest.ensembl.org).")
		except Exception:
			returnError("Problem with Ensembl Rest API call")
		if not regulatoryRequest.ok:
			regulatoryRequest.raise_for_status()
			returnError('Problem fetching the regulatory elements for the excised sequence')

		elements = regulatoryRequest.json()

		# connect to the genome's database
		dbConnection = Config(self.super.genome)
		curr_geneCollection = dbConnection.curr_geneCollection

		# filter out the transcript that's being targeted (same external name as gene name)
		filteredElements = []
		try:
			for e in elements:
				if e['feature_type'] == 'transcript':
					if str(self.super.ensemblID) != str(e['Parent']):
						tempDict = {}
						tempDict['feature_type'] = e['feature_type']
						tempDict['start'] = e['start']
						tempDict['end'] = e['end']
						tempDict['chr'] = e['seq_region_name']
						tempDict['parentID'] = e['Parent']
						filteredElements.append(tempDict)
				else:
					tempDict = {}
					tempDict['feature_type'] = e['feature_type']
					tempDict['start'] = e['start']
					tempDict['end'] = e['end']
					tempDict['chr'] = e['seq_region_name']
					tempDict['description'] = e['description']
					filteredElements.append(tempDict)
		except Exception as e:
			returnError("Problem parsing regulatory elements during QA" + str(e))

		if len(filteredElements) > 0:
			print("<div style=\"align-items: center;\"><span class=\"text-warning\"><i class=\"fa fa-exclamation-circle\"></i><p style=\"display: inline;\"> Warning: Guides may overlap with the following features:</p></span>")
			print('''
			<table class="table table-bordered mt-1" style="max-width: 75%; margin: auto;">
				<thead>
				<tr>
					<th class="centreCell" scope="col">Feature Type</th>
					<th class="centreCell" scope="col">Description</th>
					<th class="centreCell" scope=col">Location</th>
				</tr>
				</thead>
				<tbody>
			''')
			for e in filteredElements:
				if e['feature_type'] == 'transcript':
					try:
						parent = curr_geneCollection.find_one({"ENSID": e['parentID']})
						print("<tr><td>" + e['feature_type'] + "</td><td>Transcript of " +
							parent['Name'] + "</td><td>chr" + str(e['chr']) + ":" +
							str(e['start']) + "-" + str(e['end']) + "</td></tr>")
					except Exception as e:
						returnError("Problem fetching name of parent transcript" + str(e))
				else:
					print("<tr><td>" + e['feature_type'] + "</td><td>" + e['description'] + "</td><td>chr" + str(
						e['chr']) + ":" + str(e['start']) + "-" + str(e['end']) + "</td></tr>")

			print("</tbody></table></div>")
		else:
			print("<span class=\"text-success\"><i class=\"fa fa-check\"></i><p style=\"display: inline;\"> Guides passed QA check</p></span><br>")

		print("<br>")

	def checkSuccess(self):
		# check that there are both wt and em primers and the file dictionary has been written
		if len(self.fileDictionary) > 0:
			if len(self.wtPrimers) > 0 and len(self.emPrimers) > 0:
				self.success = [True, True] # both em and wt primers found & written successfully
			elif len(self.wtPrimers) > 0:
				self.success = [True, False] # only wt found/written
			elif len(self.emPrimers) > 0:
				self.success = [False, True] # only em found/written

	def writeGuideAPE(self):
		# write every combination to file, labelling with postfix (0-9)_(0-9) to indicate pair
		for key, apeString in self.fileDictionary.items():
			try:
				# name file based on wt/em pair chosen
				if len(self.wtPrimers) > 0 and len(self.emPrimers) > 0:
					filename = str(self.super.geneName+"_"+str(self.super.release)+"-automated_"+ str(key[0])+"_"+str(key[1])+".ape")
				elif len(self.wtPrimers) > 0:
					filename = str(self.super.geneName+"_"+str(self.super.release)+"-automated_"+ str(key[0])+"_0.ape")
				elif len(self.emPrimers) > 0:
					filename = str(self.super.geneName+"_"+str(self.super.release)+"-automated_0_"+ str(key[0])+".ape")
				else:
					returnError("No EM or WT primers")
				apeFile = open(os.path.join(self.apeDir, self.super.genome, 'features', filename), 'w')
				apeFile.write(apeString)
				apeFile.close()
			except Exception as e:
				returnError("Problem writing APE file " + str(e))

	def writePrimerCSV(self):
		guideDict = {}
		guideCounter = 1
		for guide in self.gRNAs:
			guideDict[guideCounter] = {}
			guideDict[guideCounter]['sequence'] = guide[1]
			guideDict[guideCounter]['PAM'] = guide[3]
			guideCounter += 1

		wtCounter = 0
		emCounter = 0
		csvDir_genome = os.path.join(self.csvDir, self.super.genome)
		#check that the csv dir exists for this organism
		if not os.path.exists(csvDir_genome):
			# create if it doesn't exist yet
			os.makedirs(csvDir_genome)
		# write a csv for every pair of wt and em primers
		for w, wPrimer in self.wtPrimers.items():
			if len(self.emPrimers) > 0:
				for e, ePrimer in self.emPrimers.items():
					filename = str(self.super.geneName+"_"+str(self.super.release)+"-primers_"+str(w)+"_"+str(e)+".csv")
					filepath = os.path.join(csvDir_genome, filename)
					try:
						with open(filepath, mode='w') as csv_file:
							# write Guide Header
							writer = csv.writer(csv_file, delimiter=",")
							writer.writerow(["Guides:"])
							writer.writerow(["Sequence", "PAM"])
							# print guides from dictionary
							guideFields = ['sequence', 'PAM']
							writer = csv.DictWriter(csv_file, fieldnames=guideFields)
							for g, guide in guideDict.items():
								writer.writerow(guide)
							writer = csv.writer(csv_file, delimiter=",")
							writer.writerow([])
							writer.writerow(["Primers:"])
							writer.writerow(["Primer Name", "Sequence", "Tm"])
							primerName = str(self.super.geneName + "_")
							writer.writerow([(primerName + "wt_F1"), wPrimer['leftprimer'], str(wPrimer['leftTM'])])
							writer.writerow([(primerName + "wt_R1"), wPrimer['rightprimer'], str(wPrimer['rightTM'])])
							writer.writerow([(primerName + "em_F1"), ePrimer['leftprimer'], str(ePrimer['leftTM'])])
							writer.writerow([(primerName + "em_R1"), ePrimer['rightprimer'], str(ePrimer['rightTM'])])
						emCounter += 1
					except Exception as e:
						returnError("Problem writing csv file : " + str(e))
			else:
				filename = str(self.super.geneName+"_"+str(self.super.release)+"-primers_"+str(w)+"_0.csv")
				filepath = os.path.join(csvDir_genome, filename)
				try:
					with open(filepath, mode='w') as csv_file:
						# write Guide Header
						writer = csv.writer(csv_file, delimiter=",")
						writer.writerow(["Guides:"])
						writer.writerow(["Sequence", "PAM"])
						# print guides from dictionary
						guideFields = ['sequence', 'PAM']
						writer = csv.DictWriter(csv_file, fieldnames=guideFields)
						for g, guide in guideDict.items():
							writer.writerow(guide)
						writer = csv.writer(csv_file, delimiter=",")
						writer.writerow([])
						writer.writerow(["Primers:"])
						writer.writerow(["Primer Name", "Sequence", "Tm"])
						primerName = str(self.super.geneName + "_")
						writer.writerow([(primerName + "wt_F1"), wPrimer['leftprimer'], str(wPrimer['leftTM'])])
						writer.writerow([(primerName + "wt_R1"), wPrimer['rightprimer'], str(wPrimer['rightTM'])])
				except Exception as e:
					returnError("Problem writing csv file : " + str(e))
			wtCounter += 1
		return

	def writePrimerJSON(self):
		# get ids of guides used in design
		guideIDs = []

		for g, guide in self.gRNADict.items():
			guideIDs.append(str(guide['_id']))

		# write a json for every wt primer first
		for w, wPrimer in self.wtPrimers.items():
			filename = str(self.super.geneName + "_" + str(self.super.release) + "_WT-" + str(w) + ".json")
			filepath = os.path.join(self.jsonDir, filename)
			primerDict = self.createPrimerDict(wPrimer)
			# store the guides the primers were designed with
			primerDict["guides"] = {}
			primerDict["guides"]["ids"] = guideIDs
			primerDict["guides"]["rank"] = w # store rank of primers for guides
			with open(filepath, 'w') as json_file:
				json.dump(primerDict, json_file)

		for e, ePrimer in self.emPrimers.items():
			filename = str(self.super.geneName + "_" + str(self.super.release) + "_EM-" + str(e) + ".json")
			filepath = os.path.join(self.jsonDir, filename)
			primerDict = self.createPrimerDict(ePrimer)
			primerDict["guides"] = {}
			primerDict["guides"]["ids"] = guideIDs
			primerDict["guides"]["rank"] = e
			with open(filepath, 'w') as json_file:
				json.dump(primerDict, json_file)
		return

	# create the dict for a primer that will be written to json
	def createPrimerDict(self, primer):
		# basically just mapping internal dict to mongoDB
		primersDict = {}
		primersDict["batchName"] = self.super.geneName
		primersDict["ENSID"] = self.super.ensemblID
		primersDict["chr"] = 'chr' + str(self.super.chromosome)
		primersDict["release"] = str(self.super.release)
		primersDict["type"] = primer['type']
		primersDict["rightprimer"] = primer['rightprimer']
		primersDict["rightGC"] = str(primer['rightGC'])
		primersDict["rightTM"] = str(primer['rightTM'])
		primersDict["rightlen"] = str(primer['rightlen'])
		primersDict["right_genomicLocation"] = str(primer['genomicRightStart'])
		primersDict["leftprimer"] = primer['leftprimer']
		primersDict["leftGC"] = str(primer['leftGC'])
		primersDict["leftTM"] = str(primer['leftTM'])
		primersDict["leftlen"] = str(primer['leftlen'])
		primersDict["left_genomicLocation"] = str(primer['genomicLeftStart'])
		primersDict["productSize"] = str(primer['productSize'])
		primersDict["status"] = "Accepted"  # accepted to begin with
		primersDict["notes"] = "" # blank to start

		return primersDict

	# write the download buttons for the csv and ape files (pre-set to default (0_0))
	def writeDownloads(self):
		if self.success[0] == False and self.success[1] == False:
			returnError("Unable to design EM or WT guides")
			return

		self.writeGuideAPE()
		self.writePrimerCSV()
		self.writePrimerJSON()
		defaultAPE = str(self.super.geneName + "_" + str(self.super.release) + "-automated_0_0.ape")
		defaultCSV = str(self.super.geneName + "_" + str(self.super.release) + "-primers_0_0.csv")
		genomeAPE_features = os.path.join("../files/apeFiles", self.super.genome, 'features')
		genomeCSV = os.path.join("../files/csvFiles", self.super.genome)

		print('''
			</br>

			<div class="btn-group" role="group" style="float: left;">
				<button class="btn btn-primary btn-sm bordered-button" type="button" onclick="addPrimersToDatabase()">Add Primers to Database</button>
				<div class="btn-group" role="group">
					<button class="btn btn-secondary btn-sm dropdown-toggle bordered-button" type="button" id="dropdownDownloadLinks" data-toggle="dropdown">
					Download
					</button>
					<div class="dropdown-menu">
						<a class="dropdown-item" id="apeDownload" href="''' + os.path.join(genomeAPE_features, defaultAPE) + '''" download>Selected as APE</a>
						<a class="dropdown-item" id="csvDownload" href="''' + os.path.join(genomeCSV, defaultCSV) + '''" download>Selected as CSV</a>
					</div>
				</div>

			</div>
			<br>
			<br>
			<br>''')

	def setTargets(self):
		"""
		Each design will have 1-4 guides. WT and EM primers are designed
		based on these guides. Depending on the number of guides, there
		are different rules around what's being targeted by the primers
		"""
		# check first to make sure the guides don't overlap
		self.checkOverlap()
		# set the preliminary targets and excised start for the wt and em primers
		startExcise = self.getCut(self.gRNAs[0])
		if len(self.gRNAs) == 4:
			# wt target is the first excised sequence
			wtTarget = (self.getCut(self.gRNAs[0]), self.getCut(self.gRNAs[1]))
			# em target is largest possible excised sequence
			emTarget = (self.getCut(self.gRNAs[0]), self.getCut(self.gRNAs[3]))
			lengthExcise = abs(self.getCut(self.gRNAs[3]) - startExcise)
		elif len(self.gRNAs) == 3:
			# wt target is smaller excised sequence
			wtTarget = (self.getCut(self.gRNAs[0]), self.getCut(self.gRNAs[1]))
			# em target is largest possible excised sequence
			emTarget = (self.getCut(self.gRNAs[0]), self.getCut(self.gRNAs[2]))
			lengthExcise = abs(self.getCut(self.gRNAs[2]) - startExcise)
		elif len(self.gRNAs) == 2:  # only two guides
			# wt target is the first guide itself
			wtTarget = (self.gRNAs[0][7], self.gRNAs[0][8])
			# em target is the entire excised sequence (a 150 bp buffer is added later)
			emTarget = (self.getCut(self.gRNAs[0]), self.getCut(self.gRNAs[1]))
			lengthExcise = abs(self.getCut(self.gRNAs[1]) - startExcise)
		elif len(self.gRNAs) == 1: # only one guide, only design one set of primers
			# we'll call the primer a wt primer
			wtTarget = (self.gRNAs[0][7], self.gRNAs[0][8])
			emTarget = None
			lengthExcise = abs(self.gRNAs[0][7] - self.gRNAs[0][8]) # pretend the excised region is the guide itself
		else:
			returnError(str(len(
				self.gRNAs)) + " Guides are marked as accepted for this gene. Can only design primers using 2, 3 or 4 guides")
			exit()

		return startExcise, lengthExcise, wtTarget, emTarget

	def checkOverlap(self):
		# compare every guide to the ones after it
		for i in range(0, len(self.gRNAs)):
			for j in range(i, len(self.gRNAs)):
				if self.gRNAs[i] != self.gRNAs[j] and self.gRNAs[i][8] > self.gRNAs[j][7]:
					returnError("Two or more Guides overlap one another.")
					sys.exit()

	def fetchGuides(self):
		# get all accepted guides for this gene via the parent Gene object
		dbConnection = Config(self.super.genome)
		gRNACollection = dbConnection.guideCollection
		geneQuery = {"ENSID": self.super.ensemblID, "status": 'Accepted'}
		geneGuides = gRNACollection.find(geneQuery)
		guideArray = []
		guideDict = {}
		guideCounter = 1
		# add the score, seq, start, pam, pamStart, off targets, and notes to the guide array
		for x in geneGuides:
			'''
			old method was to use a guideArray but since this isn't flexible to additional fields
			being used, the code is in the process of being converted to use a dictionary instead.
			some sections still use this array but eventually all dependencies to it should be removed
			'''
			guideArray.append(
				[x['guideScore'], x['guideSeq'], x['guideGenomicStart'], x['pamSeq'], x['pamGenomicStart'], x['otDesc'],
				 x['Notes']])

			# TODO: convert completely to using the guideDict everywhere instead of the guideArray in future.
			# The guideDict has the label, id, and is easier to adapt to changes in structure
			guideDict[guideCounter] = {}
			guideDict[guideCounter]['guideScore'] = x['guideScore']
			guideDict[guideCounter]['guideSeq'] = x['guideSeq']
			guideDict[guideCounter]['guideGenomicStart'] = x['guideGenomicStart']
			guideDict[guideCounter]['pamSeq'] = x['pamSeq']
			guideDict[guideCounter]['pamGenomicStart'] = x['pamGenomicStart']
			guideDict[guideCounter]['otDesc'] = x['otDesc']
			guideDict[guideCounter]['label'] = x['label']
			guideDict[guideCounter]['_id'] = x['_id']
			guideCounter += 1

		return guideArray, guideDict

	def addCutsites(self):
		"""
			the gRNAs are in an array with the indices corresponding to the following order:
			guideScore(0), guideSeq(1), guideGenomicStart(2), pamSeq(3), pamGenomicStart(4), otDesc(5), Notes(6)
			we want to get the start, end,  and direction for the guides relative to the formatted sequence (with 1000bp buffer)
			they're added to indices 7, 8 and 9 of the array self.gRNAs

			(this is done in parallel to the modification of the guide dict which will replace the guide list)
		"""
		for g in self.gRNAs:
			# find start of forward primers
			start = None
			guideSeq = g[1]
			try:
				start = re.search(guideSeq, self.super.sequence, re.IGNORECASE).start()
				g.append(start)
				g.append(start + len(guideSeq))
				g.append('F')
			except Exception:
				# the guide sequence wasn't found
				# reverse it an search again
				guideSeq = revSeq(g[1])
				try:
					start = re.search(guideSeq, self.super.sequence, re.IGNORECASE).start()
					g.append(start)
					g.append(start + len(guideSeq))
					g.append('R')
				except Exception:
					returnError("Could not find one of the guides in the sequence for the gene")

		# also do for the guide dict (slowly moving towards eliminating the list...)
		for key, g in self.gRNADict.items():
			try:
				start = re.search(g['guideSeq'], self.super.sequence, re.IGNORECASE).start()
				g['start'] = start
				g['end'] = int(start) + len(g['guideSeq'])
				g['direction'] = 'F'
			except Exception:
				# guide sequence wasn't found
				# reverse and search again
				try:
					start = re.search(revSeq(g['guideSeq']), self.super.sequence, re.IGNORECASE).start()
					g['start'] = start
					g['end'] = int(start) + len(g['guideSeq'])
					g['direction'] = 'R'
				except Exception:
					returnError("Unable to find one of the guides in the sequence for this gene")

	# TODO: remove the gRNA code once converted to using gRNADict
	def labelGuides(self):
		"""
			If every guide has a manual label associated with it, use those.
			Otherwise, label the guides based on where they lie on the gene (relative to gene direction)
			if there are 4 then from left to right they're labelled: 'U5', 'U3', 'D5', 'D3'
			if there are 2 though, they're just labelled: 'U' and 'D'
			if there are 3, use 'U' and 'D' and label the middle guide with 'M'
			if there is 1, just use 'gRNA'
		"""
		# sort the guide dict & convert it to an ordered dict
		self.gRNADict = OrderedDict(sorted(self.gRNADict.items(), key=lambda x: int(x[1]['start'])))

		useManualLabel = True
		for key, guide in self.gRNADict.items():
			if guide['label'] == '' or guide['label'] is None:
				useManualLabel = False

		self.gRNAs.sort(key=lambda x: x[7])  # sort based on start

		# TODO can remove this once converted to using dict
		if useManualLabel:
			# add manual label to list of gRNAs
			# this is annoying but it's a temp fix until code is fully converted to using the guide dict
			for guide in self.gRNAs:
				for key, gDict in self.gRNADict.items():
					if gDict['guideSeq'] == guide[1]:
						guide.append(gDict['label'])
		else:
			nGuides = len(self.gRNADict)
			for i, (key, guide) in enumerate(self.gRNADict.items()):
				if nGuides == 4:
					if i == 0:
						guide['label'] = 'gRNA_U5'
					elif i == 1:
						guide['label'] = 'gRNA_U3'
					elif i == 2:
						guide['label'] = 'gRNA_D5'
					elif i == 3:
						guide['label'] = 'gRNA_D3'
				elif nGuides == 3:
					if i == 0:
						guide['label'] = 'gRNA_U'
					elif i == 1:
						guide['label'] = 'gRNA_M'
					elif i == 2:
						guide['label'] = 'gRNA_D'
				elif nGuides == 2:
					if i == 0:
						guide['label'] = 'gRNA_U'
					elif i == 1:
						guide['label'] = 'gRNA_D'
				elif nGuides == 1:
					guide['label'] = 'gRNA'
				else:
					returnError("Problem labelling guides, the number of accepted guides must be 2, 3, or 4")

			# TODO: once switched to dict, can remove this
			numGuides = len(self.gRNAs)
			for g, guide in enumerate(self.gRNAs):
				if numGuides == 4:
					if g == 0:
						guide.append('gRNA_U5')
					if g == 1:
						guide.append('gRNA_U3')
					if g == 2:
						guide.append('gRNA_D5')
					if g == 3:
						guide.append('gRNA_D3')
				elif numGuides == 3:
					if g == 0:
						guide.append('gRNA_U')
					if g == 1:
						guide.append('gRNA_M')
					if g == 2:
						guide.append('gRNA_D')
				elif numGuides == 2:
					if g == 0:
						guide.append('gRNA_U')
					if g == 1:
						guide.append('gRNA_D')
				elif numGuides == 1:
					guide.append('gRNA')
				else:
					returnError("Problem labelling guides, the number of accepted guides must be 2, 3, or 4")


	def primer3Design(self):
		# initialize Primer3 class
		primer3Connection = Primer3()
		htmlResult = ''
		for primerType in ["WT", "EM"]:
			primerResult, retryString = primer3Connection.attemptDesign(self, primerType)
			if primerResult:
				htmlResult += retryString
				if primerType == 'WT':
					wtPrimers = primerResult
					if len(wtPrimers) > 0:
						self.addGenomicLocation(wtPrimers)
				elif primerType == 'EM':
					emPrimers = primerResult
					if len(emPrimers) > 0:
						# need to rewrite the coordinates because they are relative to the excised sequence
						for rank, p in primerResult.items():
							rStart = int(p['rightstart'])
							lStart = int(p['leftstart'])
							if rStart > self.startExcise:
								p['rightstart'] = rStart + self.lengthExcise
							if lStart > self.startExcise:
								p['leftstart'] = lStart + self.lengthExcise

					self.addGenomicLocation(emPrimers)
					self.addWtFragments(emPrimers)
				if len(primerResult) > 0:
					# add the results table
					htmlResult += printPrimers(primerResult, primerType)
			else:
				if retryString:
					htmlResult += retryString
				if primerType == 'WT': wtPrimers = {}
				elif primerType == 'EM':
					emPrimers = {}

		htmlResult += ("</div>")
		return wtPrimers, emPrimers, htmlResult

	# need to add the wt product size to the em primer product size field
	def addWtFragments(self, emPrimers):
		for key, primer in emPrimers.items():
			if primer['genomicRightStart'] > primer['genomicLeftStart']:
				# we're in a forward gene
				wtFragementSize = (int(primer['genomicRightStart']) - int(primer['genomicLeftStart'])) + 1
			else:
				wtFragementSize = (int(primer['genomicLeftStart']) - int(primer['genomicRightStart'])) + 1
			primer["productSize"] = str(primer['productSize']) + "; " + str(wtFragementSize)

	# figure out the genomic locations of the primers (this should match the start that BLAST finds in the QA step later)
	def addGenomicLocation(self, filteredPrimers):
		for key, primer in filteredPrimers.items():
			'''
			If the gene is on the reverse strand, the genomic start of a primer is the genomic
			location for the last base in the APE file minus the start location of the primer
			in the APE file. If the gene is a forward one, the genomic start of a primer is the
			genomic location of the start of the APE file plus the start location of the primer
			in the APE file.
			'''
			if self.super.strand == -1:
				# if gene is on reverse strand, the start is where the APE file sequence ends
				primer['genomicLeftStart'] = int(self.super.sequenceEnd) - int(primer['leftstart']) + 1
				primer['genomicRightStart'] = int(self.super.sequenceEnd) - int(primer['rightstart']) + 1
			else:
				primer['genomicLeftStart'] = int(self.super.sequenceStart) + int(primer['leftstart']) - 1
				primer['genomicRightStart'] = int(self.super.sequenceStart) + int(primer['rightstart']) - 1


	# returns actual cutsite for a guide based on the PAM and direction of a guide
	def getCut(self, guide):
		# cuts occur 3-4 bp (using 3) upstream of PAM (which is immediately after the guide sequence)
		if guide[9] == 'F':
			# if guide is forward, cut is 3 bases upstream of end
			return guide[8] - 3
		elif guide[9] == 'R':
			# if guide is reverse, cut is 3 bases downstream of start
			# (start/end are defined by order 5'-3' on coding strand)
			return guide[7] + 3


#TODO: consider moving this and other html printing functions out of the class
# uses the dict to write a table with the relevant primer info
def printPrimers(primerDict, primer):
	htmlTable = ""
	if primer == 'EM':
		htmlTable += "<br>"
	htmlTable += "<h4 id=\"tableTitle\"> Top " + str(len(primerDict)) + " " + primer + " Primers</h4>"
	htmlTable += """
	<table class="primerTable table table-bordered center">
		<thead>
		<tr>
		<th scope="col" class="centreCell">Select</th>
		<th scope="col" class="centreCell" style="width: 5%;">Pair Rank</th>
		<th scope="col">Type</th>
		<th scope="col">Sequence</th>
		<th scope="col">Details</th>
		<th scope="col" style="width: 20%;">BLAST Results</th>
		<th scope="col" class="centreCell">Product</th>
		</tr>
		</thead>
		<tbody>
	"""
	rank = 1
	idCount = 0
	for pairNum in sorted(primerDict.keys()):

		idCountString = str(idCount)

		# define html for beginning of first row
		if rank == 1:
			# if top-ranked, want to automatically select
			htmlTable += """
			<tr id="{primer}-{idCountString}">
				<td rowspan="2" class="align-middle centreCell">
					<input type="checkbox" class="selectCheckbox-{primer}" checked="checked"/>
				</td>
			""".format(**locals())
		else:
			htmlTable += """
			<tr id="{primer}-{idCountString}">
				<td rowspan="2" class="align-middle centreCell">
					<input type="checkbox" class="selectCheckbox-{primer}">
				</td>
			""".format(**locals())

		# continue html for first row which contains left primer info
		# define the variables for left primer first
		leftPrimer = str(primerDict[pairNum]['leftprimer'])
		leftLength = str(primerDict[pairNum]['leftlen'])
		leftGC_rounded = str(round(float(primerDict[pairNum]['leftGC']), 2))
		leftTM_rounded = str(round(float(primerDict[pairNum]['leftTM']), 2))
		productSize = str(primerDict[pairNum]['productSize'])
		htmlTable += """
		<td rowspan="2" class="align-middle centreCell">{rank}</td>
		<td class="align-middle centreCell">Forward</td>
		<td class="align-middle centreCell">{leftPrimer}</td>
		<td class="centreCell" style="font-size: 0.75rem;">Length: {leftLength}<br>GC Percent: {leftGC_rounded}<br>TM: {leftTM_rounded}</td>
		<td class="align-middle centreCell" style="background-color: #e9f3fd">Searching <i class="fa fa-spinner fa-spin"></i></td>
		<td rowspan="2" class="align-middle centreCell">{productSize}</td>
		</tr>
		""".format(**locals())

		# right primer is the second row for pair. define its attributes
		idCountString = str(idCount+1)
		rightPrimer = str(primerDict[pairNum]['rightprimer'])
		rightLength = str(primerDict[pairNum]['rightlen'])
		rightGC_rounded = str(round(float(primerDict[pairNum]['rightGC']), 2))
		rightTM_rounded = str(round(float(primerDict[pairNum]['rightTM']), 2))
		# and write the html for the row
		htmlTable += """
		<tr id="{primer}-{idCountString}">
		<td>Reverse</td>
		<td>{rightPrimer}</td>
		<td class="centreCell" style="font-size: 0.75rem;">Length: {rightLength}<br>GC Percent: {rightGC_rounded}<br>TM: {rightTM_rounded}</td>
		<td class="align-middle centreCell" style="background-color: #e9f3fd">Searching <i class="fa fa-spinner fa-spin"></i></td>
		</tr>
		""".format(**locals())

		rank = rank + 1
		idCount = idCount + 2

	htmlTable += """
	</tbody>
	</table>
	<br>
	"""
	return htmlTable


# get the reverse complement of seq
def revSeq(seq):
	reversedSeq = seq[::-1]
	complements = {'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A'}
	return ''.join([complements[base] for base in reversedSeq])


