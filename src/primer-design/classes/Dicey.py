#!/usr/bin/env python3

"""
Hillary Elrick February 4th, 2019

Class definition to ease & organize access to Dicey in silico PCR tool
"""

import json, os, subprocess, sys
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, Optional

# get the global root path from the Config object
sys.path.append(os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "helpers")))
from Config3 import Config


class Dicey:
	"""
	Dicey is used to run in silico PCR on a pair of primers.
	"""
	def __init__(self, sequences: List[str], temperature: str, genome: str):
		assert len(sequences) == 2, "Exactly two primers required"
		self.config = Config()
		self.sequences = sequences
		self.temperature = temperature
		self.genome_path = os.path.join(self.config.ROOT_PATH, "jbrowse", "data", genome, "processed", genome + ".fa")

	@property
	def command(self) -> List[str]:
		"""
		Returns the Dicey command prefix with reference to the locally installed Primer3 in addition
		to the genome of interest and minimum temperature to consider for binding.
		The final sequences.fasta parameter is not included.
		"""
		return [
			"dicey",
			"search",
			"--config",
			self.config.PRIMER3_CONFIG,
			"--cutTemp",
			self.temperature,
			"--genome",
			self.genome_path
		]


	def run(self) -> Optional[Dict[str, Any]]:
		# Dicey does not support using standard input, symlinks, or process substitution for its inputs
		with NamedTemporaryFile(mode="w", encoding="utf-8") as sequences:
			sequences.write(">leftPrimer\n{}\n>rightPrimer\n{}\n".format(self.sequences[0], self.sequences[1]))
			sequences.flush()
			dicey_process = subprocess.run(self.command + [sequences.name], capture_output=True)
			# If exceptions are okay then switch to check=True
			if dicey_process.returncode:
				print(dicey_process.stdout)
				print(dicey_process.stderr)
				return
			else:
				try:
					jsonResult = json.loads(dicey_process.stdout)
					if 'errors' in jsonResult and len(jsonResult['errors']) > 0:
						print("Error(s) from Dicey program: ")
						for error in jsonResult['errors']:
							print(error['title'])
						return
					return jsonResult['data']
				except Exception as e:
					print("Error reading Dicey results: " + str(e))
					return
