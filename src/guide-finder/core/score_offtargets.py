#!/usr/bin/env python3

"""
Hillary Elrick, August 7th, 2019

Accepts a dictionary of potential guides and their off-targets along with the rgen ID for the guide. Determines which scoring method(s) to apply
depending on the rgen and appends each off-target with its score. Also adds the cumulative scores to the guide record in the dictionaries.

The code to calculate the CFD score (for Cas9 RGEN) is contained within the cfd_code folder and comes directly from the authors' paper.
"""

import sys
import os
from subprocess import Popen, PIPE, DEVNULL
dir_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(dir_path, "../../helpers"))
from Config3 import Config
from itertools import product
import cfd_code.cfd_score_calculator3 as cfd
sys.path.append(os.path.join(dir_path,"inDelphi-model"))
import inDelphi
import get_sequence
import time

def getRgenRecord(rgenID):
	dbConnection = Config()	
	rgenCollection = dbConnection.rgenCollection
	rgenRecord = rgenCollection.find({"rgenID": str(rgenID)})
	if rgenRecord.count() == 1:
		return rgenRecord.next()
	else:
		raise Exception("Incorrect number of records returned from RGEN database for rgenID " + str(rgenID))
		return


def inDelphiScore(guideDict,genome_fa,twoBitToFa_path,genome_2bit,tempfiles_path, cleaves):
	"""
	Given a dict of guides, calculate the inDelphi score of each guide and adds this information to the dictionary

	Method: Max W. Shen*, Mandana Arbab*, Jonathan Y. Hsu, Daniel Worstell, Sannie J. Culbertson, Olga Krabbe,
	Christopher A. Cassa, David R. Liu, David K. Gifford, and Richard I. Sherwood.
	"Predictable and precise template-free editing of pathogenic variants." Nature, 2018.
	doi:10.1038/s41586-018-0686-x
	"""
	import math
	inDelphi.init_model(celltype = 'mESC')

	for guideID, guide in guideDict.items():
		if guide['max_exceeded']:
			guide['Precision'] = '0'
			guide['Frameshift Frequency'] = '0'
			guide['MH Strength'] = '0'
			continue
		elif guide['skip']:
			guide['Precision'] = '-1'
			guide['Frameshift Frequency'] = '-1'
			guide['MH Strength'] = '0'

		#TODO: NEED TO REPLACE NEXT LINE
		# the last term should be replaced with ~20 bps after the cutsite
		# get this via the get_sequence code
		print(guide['guide_seq'])

		cleavePos=int(str(cleaves)[2:-2])
		print(cleavePos)
		#get strand
		print(guide['strand'])
		#apply strand logic to coordinates before submitting to get_sequence.py
		if guide['strand'] == "+":
			coords=str("%s:%s-%s"%(guide['pam_chrom'],(guide['pam_genomic_start']+cleavePos-30),(guide['pam_genomic_start']+cleavePos+29)))
		elif guide['strand'] == "-":
			coords=str("%s:%s-%s"%(guide['pam_chrom'],(guide['pam_genomic_start']-cleavePos-29),(guide['pam_genomic_start']-cleavePos+30)))
#		coords=str("%s:%s-%s"%(guide['pam_chrom'],guide['guide_genomic_start'],(guide['pam_genomic_start']+cleavePos+20)))

		print(coords)

		timestr = time.strftime("%Y%m%d-%H%M%S")
		getseq=str(get_sequence.fetch_sequence(twoBitToFa_path, coords, genome_2bit, os.path.join(tempfiles_path,timestr+'_out.fa')))
		print(os.path.join(tempfiles_path,timestr+'_out.fa'))

		#get flanking sequence before and after cutsite
		fullSeq = ''
		with open(os.path.join(tempfiles_path, timestr+'_out.fa'), 'r') as f:
			for line in f:
				if line.startswith(">"):
					location = line.strip()
					location = location[1:] # remove > marker
					continue
				else:
					fullSeq = fullSeq + line.strip("\n") # seq is next line after label

		#set up strand complementation
		forward_nuc = 'ATGC'
		reverse_nuc = 'TACG'
		translate_code = str.maketrans(forward_nuc, reverse_nuc)
		if guide['strand'] == "+":
			fullSeq=fullSeq
		elif guide['strand'] == "-":
  			fullSeq = "".join(list(reversed(fullSeq))).translate(translate_code)

		cutsite = len(guide['guide_seq']) + cleavePos
		print(fullSeq)

		pred_df, stats = inDelphi.predict(fullSeq, cutsite)
		guide['Precision'] = round(stats['Precision'],2)
		guide['Frameshift Frequency'] = round(stats['Frameshift frequency'],2)
		# from inDelphi GitHub: natural log of phi refers to microhomology strength
		guide['MH Strength'] = round(math.log(stats['Phi']),2)

def cfdScore(guideDict):
	"""
	Given a dict of guides, calculates the CFD score of each of the off-targets as well as the cumulative CFD score
	for the entire guide. Incorporates this information into the dict

	Method: Doench, 2016 (https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4744125)
	Code Included in Supplementary Materials
	"""
	mm_scores, pam_scores = cfd.get_mm_pam_scores()
	for guideID, guide in guideDict.items():
		if guide['max_exceeded']:
			# don't report aggregated CFD score if off target list was truncated
			guide['CFD'] = '0'
			continue
		elif guide['skip']:
			guide['CFD'] = '-1' # show below max_exceeded

		guideSeq = str(guide['guide_seq'])
		cumulative_score = []
		for offtarget in guide['offtargets']:
			if 'N' in offtarget['seq'].upper():
				offtarget['CFD'] = None
				continue # cfd scores can't be calculated for offtargets with Ns
			offSeq = offtarget['seq'].upper()
			offPam = offtarget['pam'][-2:].upper() # only requires last 2 bases of pam
			sub_score = cfd.calc_cfd(guideSeq, offSeq, offPam)
			offtarget['CFD'] = str(round(sub_score,2))
			cumulative_score.append(sub_score)

		aggregate_score = 100 / (100+sum(cumulative_score))
		aggregate_score = int(round(aggregate_score*100))
		guide['CFD'] = str(aggregate_score)


def mitScore(guideDict, rgenRecod):
	"""
	Given a dict of guides, calculates the MIT score of each off-target as well as the cumulative MIT score
	for the entire guide. Incorporates this information into the dict.


	Method: Hsu, 2013 (https://www.nature.com/articles/nbt.2647)
	Values and scoring formula from: https://web.archive.org/web/20160825081629/http://crispr.mit.edu/about
	Using sgRNA activity ratios for alternative pams from: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4744125
	"""
	M=[0,0,0.014,0,0,0.395,0.317,0,0.389,0.079,0.445,0.508,0.613,0.851,0.732,0.828,0.615,0.804,0.685,0.583]

	for guideID, guide in guideDict.items():
		if guide['max_exceeded']:
			# don't calculate MIT score if off target list was truncated
			guide['MIT'] = '0'
			continue
		elif guide['skip']:
			guide['MIT'] = '-1' # show below max_exceeded
			continue

		guideSeq = str(guide['guide_seq'])
		cumulative_score = []
		for offtarget in guide['offtargets']:
			offSeq = offtarget['seq'].upper()
			offPam = offtarget['pam'].upper()
			assert (len(guideSeq) == len(offSeq)), "Guide and Off-target are different lengths"
			score = 0
			mismatches = []
			weight = 1.0
			for i in range(0, len(guideSeq)):
				if str(guideSeq[i]) != str(offSeq[i]):
					mismatches.append(i)
					weight *= (1-M[i])

			if len(mismatches) == 0:
				# no mismatches gets score of 1
				score=1
			else:
				# calculate mean distance between subsequent mismatches
				try:
					distance = sum([b-a for a,b in zip(mismatches, mismatches[1:])])/(len(mismatches)-1)
				except ZeroDivisionError:
					# handle only one mismatch
					distance = 0

				# calculate term to multiply weight by
				multiplier = ((19 - distance)/float(19)*4)+1
				multiplier = (1.0/multiplier)
				multiplier = multiplier * (1.0/(len(mismatches)**2))

				score = weight * multiplier * 100

			# reduce scores for alternative PAMS
			if str(guide['pam_seq'][-2:]).upper() != offPam[-2:].upper():
				if offPam[-2:].upper() == 'AG':
					score = score * 0.26
				elif offPam[-2:].upper() == 'CG':
					score = score * 0.11
				elif offPam[-2:].upper() == 'GA':
					score = score * 0.07
				else:
					raise ValueError("Unrecognized PAM sequence")

			#guide['offtargets'][i]['MIT'] = str(score)
			offtarget['MIT'] = str(round(score,2)) # store shorter
			cumulative_score.append(score)

		aggregate_score = 100 / (100+sum(cumulative_score))
		aggregate_score = int(round(aggregate_score*100))
		guide['MIT'] = str(aggregate_score)


def defaultRank(guideDict):
	"""
	If no score exists for the rgen, rank based on a weighted count of off-targets.
	Multiply the number of off-targets with 0 mismatches by 10^4, 1 mismatches by 10^3 etc.
	"""
	for guideID, guide in guideDict.items():
		cumulative_rank = 0
		if guide['max_exceeded']:
			cumulative_rank = 10**(5) # add large weight
		elif guide['skip']:
			cumulative_rank = 10**(5) + 1 # show below max_exceeded

		for i, count in enumerate(guide['offtarget_counts']):
			cumulative_rank += (int(count)*(10**(4-i)))

		guide['Rank'] = cumulative_rank


def scoreOffTargets(guideDict, rgenID,genome_fa,twoBitToFa_path,genome_2bit,tempfiles_path):
	# connect to database and get the rgen variables from id
	rgen = getRgenRecord(rgenID)
	scores = rgen['Scores']
	cleaves = rgen['Cleaves']

	if scores:
		if 'MIT' in scores:
			mitScore(guideDict, rgen["OffTargetPAMS"])
		if 'CFD' in scores:
			cfdScore(guideDict)
		if 'inDelphi' in scores:
			inDelphiScore(guideDict,genome_fa,twoBitToFa_path,genome_2bit,tempfiles_path,cleaves)

	defaultRank(guideDict)
	return guideDict


def main():
	scoreOffTargets({}, 1)

if __name__ == "__main__":
    main()
