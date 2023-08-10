#!/usr/bin/python3.7

"""
Hillary Elrick December 28th, 2018

Class definition to ease & organize access to installed BLAST database
"""

import os
import re
import subprocess
import sys

# get the global root path from the Config object
sys.path.append(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "helpers")
)
from Config import Config


class BlastDB:
    """
    BlastDB is used for PrimerQA, Guide Insertion, and Manual Primer Entry
    Manages the functionality for interatcting with installed blast database.
    When creating a BlastDB object, the organism 'code' (i.e. mm10) and a list of sequence
    strings or single sequence is required. Optional parameters include the evalue cutoff
    for a search (default is 0.01), and whether identity values should be returned (default is
    that they aren't, i.e. False).
    """

    def __init__(self, org, sequences, evalue="0.01", identity=False):
        # ensure that the organism has been defined
        assert (
            org
        ), "An organism (i.e. genome) must be defined to connect to the BLAST db"
        self.org = org

        # BLAST is picky about its PATH and os variables
        self.Config = Config()
        os.environ["BLASTDB"] = os.path.join(
            self.Config.ROOT_PATH, ("jbrowse/data/" + str(org) + "/blastdb/")
        )

        # store attributes
        self.evalue = evalue
        self.identity = identity

        # if sequences is a string, (i.e. there's only one), put it into a list
        if isinstance(sequences, str):
            sequences = [sequences]
        # quick check before assigning
        assert len(sequences) > 0, "At least one input sequence must be defined"
        self.sequences = sequences

        # construct blast command
        self.blastCommand = self.constructBlastCommand()

    def constructBlastCommand(self):
        """
        Returns BLAST command for mm10 optimized for primer sequences that will only return
        hits below the class' evalue threshold. Uses the evalue and identity class attributes
        """
        # global ROOT_PATH
        # base shell command with path
        blastCommand = [self.Config.BLAST]
        blastCommand.append("-db")

        # blast db that was created by makeblastdb command on 'org'.fa files from ensembl
        blastCommand.append(str(self.org) + "_blastdb")
        blastCommand.append("-task")

        # since the primers are short, need to pass this argument or no hits will be found
        blastCommand.append("blastn-short")

        # default for object is 0.01 unless alternate value passed
        # blastCommand.append('-evalue')
        # blastCommand.append(self.evalue)

        # specify output format
        blastCommand.append("-outfmt")
        blastCommand.append("7 qseqid sseqid sseq evalue nident sstrand sstart send")

        return blastCommand

    def locationSearchCommand(self):
        """
        Returns BLAST command for mm10 optimized for parsing the location from a search.
        """
        # base shell command with path
        blastCommand = [self.Config.BLAST]
        blastCommand.append("-db")

        # blast db that was created by makeblastdb command on mm10.fa files from ensembl
        blastCommand.append(str(self.org) + "_blastdb")
        blastCommand.append("-task")

        # since the primers are short, need to pass this argument or no hits will be found
        blastCommand.append("blastn-short")

        # specify output format (just need location and nident)
        blastCommand.append("-outfmt")
        blastCommand.append("7 qseqid sseqid nident sstrand sstart send")

        return blastCommand

    def blastSequences(self):
        """
        Perform a BLAST search for every sequence in the list
        Each search of a primer results in a dictionary of the hits, the list of
        these dictionaries (hitDicts list) is returned from the function
        """
        hitDicts = []
        for seq in self.sequences:
            # convert sequence to fasta format
            printfCommand = ["printf", ">primerBLAST\n " + str(seq)]
            try:
                # bash command pipes the print command in fasta format to blast
                printfProcess = subprocess.Popen(printfCommand, stdout=subprocess.PIPE)
                blastProcess = subprocess.Popen(
                    self.blastCommand,
                    stdin=printfProcess.stdout,
                    stdout=subprocess.PIPE,
                    encoding="utf-8",
                )
                (blastOut, blastErr) = blastProcess.communicate()
            except Exception as e:
                print("Error running BLAST: " + str(e))
                return
            if blastErr:
                print(blastErr)

            # parse the results of blastOut and store the hit dictionary
            hitDict = self.parseResults(blastOut.splitlines(), seq)
            hitDicts.append(hitDict)

        return hitDicts

    def returnLocations(self):
        """
        When the BLAST searches are only being used to find
        the location of the sequence, this function will return
        a list of every sequence with its location in the genome.
        Only returns an identical match, if there are multiple, an
        error will be returned.
        """
        result = []
        blastLocation = self.locationSearchCommand()
        hitSearch = re.compile(
            "^primerBLAST[\s]([^\s]+)\s([0-9]*)[\s]*(minus|plus)[\s]*([0-9]*)[\s]*([0-9]*)"
        )

        for seq in self.sequences:
            # convert sequence to fasta format
            printfCommand = ["printf", ">primerBLAST\n " + str(seq)]
            try:
                # bash command pipes the print command in fasta format to blast
                printfProcess = subprocess.Popen(printfCommand, stdout=subprocess.PIPE)
                blastProcess = subprocess.Popen(
                    blastLocation,
                    stdin=printfProcess.stdout,
                    stdout=subprocess.PIPE,
                    encoding="utf-8",
                )
                (blastOut, blastErr) = blastProcess.communicate()
            except Exception as e:
                print("Error running BLAST: " + str(e))
            if blastErr:
                print(blastErr)

            numIdentical = 0
            hits = [str(seq)]  # to store locations
            seqLength = len(str(seq))
            for line in blastOut.splitlines():
                hitMatch = hitSearch.search(line)
                if hitMatch:
                    identLength = int(hitMatch.group(2))
                    if seqLength == identLength:
                        numIdentical += 1
                        location = hitMatch.group(1) + ":"
                        location += hitMatch.group(4) + "-" + hitMatch.group(5)
                        if hitMatch.group(3) == "plus":
                            location += ":+"
                        elif hitMatch.group(3) == "minus":
                            location += ":-"
                        else:
                            print(
                                "Error parsing direction of match: "
                                + str(hitMatch.group(3))
                            )
                        hits.append(location)
                        if numIdentical > 1:
                            print(
                                "Error: more than one identical match for search sequence '{}'".format(
                                    str(seq)
                                )
                            )

            if numIdentical == 0:
                print(
                    "Error: No identical hits found in genome for input search sequence"
                )
            result.append(hits)

        return result

    def parseResults(self, blastLines, seq):
        """
        Parse the output of the BLAST program & returns
        information about the hits in a dictionary
        """
        # hitCount = -1
        hitDict = {}
        locationCount = 0
        hit = re.compile(
            "^primerBLAST[\s]+(chr[\S]*)[\s]+([A|G|T|C|a|g|t|c|N]*)[\s]*([0-9|.|e|\-|+]*)[\s]*([0-9]*)[\s]*(minus|plus)[\s]*([0-9]*)[\s]*([0-9]*)"
        )

        # iterate through every line in output
        for line in blastLines:
            # match line containing number of hits
            # numHits = re.search("^# ([0-9]*) hits found", line)
            locationHit = hit.search(line)
            if locationHit:
                # print float(locationHit.group(4))
                # print float(len(seq))
                if float(locationHit.group(4)) / float(len(seq)) >= 0.830:
                    # only track location of first 50 hits
                    if locationCount < 50:
                        hitDict[locationCount] = {}
                        hitDict[locationCount]["inputseq"] = str(seq)
                        hitDict[locationCount]["chromosome"] = locationHit.group(1)
                        hitDict[locationCount]["matchseq"] = locationHit.group(2)
                        hitDict[locationCount]["evalue"] = locationHit.group(3)
                        hitDict[locationCount]["nident"] = locationHit.group(4)
                        hitDict[locationCount]["strand"] = locationHit.group(5)
                        hitDict[locationCount]["start"] = locationHit.group(6)
                        hitDict[locationCount]["end"] = locationHit.group(7)

                    locationCount += 1
        if locationCount <= 0:
            sys.exit("Problem parsing BLAST output, unexpected output")

        hitDict["numHits"] = locationCount

        return hitDict


"""
# section for testing on the command-line
def main():
	print("Command-line test")
	testingObject = BlastDB('mm10', 'CCTTTCTGATACTGTCATCCATTGGTTTCCC', True)
	hits = testingObject.returnLocations()
	print(hits)

if __name__ == "__main__":
	main()
"""
