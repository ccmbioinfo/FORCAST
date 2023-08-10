#!/usr/bin/env python3

"""
Hillary Elrick, July 5th, 2019

Accepts a dictionary of potential guides to evaluate for off-targets and an RGENID
For each guide, find and categorizes its off-targets with 0-1-2-3-4 mismatches in the genome

"""
import binascii
import logging
import os
import sys
import time
from subprocess import DEVNULL, PIPE, Popen, run

dir_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(dir_path, "../../helpers"))
from itertools import product

from Config import Config

logging.basicConfig(filename="logs/GuideSearchAndScore.log", level=logging.DEBUG)

nucleotide_codes = {
    "A": ["A"],
    "T": ["T"],
    "G": ["G"],
    "C": ["C"],
    "R": ["A", "G"],
    "Y": ["C", "T"],
    "S": ["G", "C"],
    "W": ["A", "T"],
    "K": ["G", "T"],
    "M": ["A", "C"],
    "B": ["C", "G", "T"],
    "D": ["A", "G", "T"],
    "H": ["A", "C", "T"],
    "V": ["A", "C", "G"],
    "N": ["A", "C", "G", "T"],
}


def getRgenRecord(rgenID):
    dbConnection = Config()
    rgenCollection = dbConnection.rgenCollection
    rgenRecord = rgenCollection.find({"rgenID": str(rgenID)})
    if rgenRecord.count() == 1:
        return rgenRecord.next()
    else:
        raise Exception(
            "Incorrect number of records returned from RGEN database for rgenID "
            + str(rgenID)
        )


def expandSequence(seq):
    """accepts a nucleotide sequence with ILAR codes and returns a list of the possible expansions"""
    base_options = []
    for base in seq:
        base_options.append(nucleotide_codes[base])

    # get cartesian product of option lists for each base
    expanded = list(product(*base_options))
    expanded = map("".join, expanded)  # convert tuples to strings

    return expanded


def generateAlternateSeqs(guide, offtargetPAMS):
    """given a guide and the OffTargetPAMS of its RGEN, generate the alternate sequences"""
    expandedPAMS = []
    for PAM in offtargetPAMS:
        expandedPAMS.extend(expandSequence(PAM))
    expandedPAMS = list(set(expandedPAMS))  # remove redundancies if they exist

    # now append them to the guide sequence
    alternateSeqs = [guide + pam for pam in expandedPAMS]
    return alternateSeqs


def getMotifs(PAMS):
    """given a list of potential PAM motifs, generates the list of their expansions"""
    expandedPAMS = []
    for p in PAMS:
        expandedPAMS.extend(expandSequence(p))

    return expandedPAMS


def writeFasta(batchID, guides, tempfile_directory):
    """given a dict of guides, write them to a fasta file"""
    fileString = ""
    for guideID, guideRecord in guides.items():
        if "skip" not in guideRecord:
            fileString += ">" + str(guideID)
            fileString += "\n" + str(guideRecord["guide_seq"]) + "\n"
    fileString = fileString[:-1]  # trim trailing newline

    fasta = open(os.path.join(tempfile_directory, str(batchID) + ".fa"), "w+")
    fasta.write(fileString)
    fasta.close()

    return fasta


def revSeq(seq):
    """given a sequence returns the complement (preserving direction, i.e. 5'->3' is converted to 5'->3' on opposite strand)"""
    complement = {
        "A": "T",
        "C": "G",
        "G": "C",
        "T": "A",
        "N": "N",
        "a": "t",
        "c": "g",
        "g": "c",
        "t": "a",
    }
    return "".join([complement[base] for base in seq[::-1]])


def hasMotif(offTargetMotifs, pamLocation, strand, sequence):
    """
    given a potential off target (location and sequence), and information about the PAM,
    determine if the sequence contains a PAM, return True if so, False otherwise
    """
    if strand == "-":
        sequence = revSeq(sequence)

    if pamLocation == "upstream":
        for motif in offTargetMotifs:
            if sequence.startswith(motif):
                return True
    elif pamLocation == "downstream":
        for motif in offTargetMotifs:
            if sequence.endswith(motif):
                return True

    return False


def countMismatches(guideDict, seedRegion, offTargetGuide):
    """
    given a guideDict representing a potential guide, the seed region of the rgen used,
    the location of the PAM, and the off-target sequence, and the off-target direction, count
    the number of mismatches the off-target has to the guide. Additionally, if the off-target
    has no mismatches within the seed region, return True (and False otherwise)
    """
    mismatches = 0
    exactMatchSeed = True

    # throw the guide sequence in a string variable, and do a double check of their lengths
    guideSequence = str(guideDict["guide_seq"])
    assert len(offTargetGuide) == len(guideSequence), (
        "off-target length does not match length of guide" + str(offTargetGuide) + "!"
    )

    # get direction and length of seed
    seedDirection, seedIndex = seedRegion[0], int(seedRegion[1:])
    # flip index if seed is at end of sequence
    seedIndex = (len(guideSequence) - seedIndex) if seedDirection == "-" else seedIndex

    for i in range(0, len(offTargetGuide)):
        if (
            guideSequence[i].upper() != offTargetGuide[i].upper()
            and offTargetGuide[i].upper() != "N"
        ):
            mismatches += 1
            if seedDirection == "+" and i < seedIndex:
                exactMatchSeed = False
            elif seedDirection == "-" and i >= seedIndex:
                exactMatchSeed = False

    return mismatches, exactMatchSeed


def initializeMismatchCount(mismatches):
    """
    initialize a list of length 5 to represent 0-1-2-3-4 mismatches and
    increment the count in position 'mismatches' by one
    """
    result = [0] * 5
    result[mismatches] = result[mismatches] + 1
    return result


def incrementMismatchCount(counts, mismatches):
    """increment the list that tracks the count of mismatches"""
    if mismatches <= 4:
        counts[mismatches] += 1

    return counts


def processOffTarget(guideDict, rgen, offTargetLoc, offTargetSeq):
    """
    given a dictionary representing a potential guide, info about the rgen used to find it,
    and the location and sequence of an off-target for the guide,
    count the number of mismatches that the off-target has (both within the seed region and not)
    and modify the guideDict to incorporate the information about this off-target
    """

    # annoyingly, the bed to fasta program requires different chromosomal coordinates than everything else (0 based indexing)
    # now that we've grabbed everything we need, can switch it back to 1 based coordinates
    chm, pos, strand = offTargetLoc.split(":")
    start, end = pos.split("-")
    offTargetLoc = chm + ":" + start + "-" + end + ":" + strand

    # if the offtarget is on the reverse strand, reverse complement it
    offTargetSeq = revSeq(offTargetSeq) if strand == "-" else offTargetSeq

    # split into sequence and PAM
    if rgen["PamLocation"] == "downstream":
        offTargetGuide = offTargetSeq[
            0 : (len(offTargetSeq) - len(guideDict["pam_seq"]))
        ]
        offTargetPAM = offTargetSeq[len(offTargetGuide) :]
        leftStart = guideDict[
            "guide_genomic_start"
        ]  # track the 'leftmost' coordinate of the guide
    elif rgen["PamLocation"] == "upstream":
        offTargetGuide = offTargetSeq[len(guideDict["pam_seq"]) :]
        offTargetPAM = offTargetSeq[0 : len(guideDict["pam_seq"])]
        leftStart = guideDict[
            "pam_genomic_start"
        ]  # track the 'leftmost' coordinate of the guide

    # check that the "off-target" is not actually the guide itself
    if offTargetGuide == guideDict["guide_seq"]:
        if (guideDict["strand"] == "+" and int(leftStart) - 1 == int(start)) or (
            guideDict["strand"] == "-" and int(leftStart) == int(end)
        ):
            # return unchanged
            return guideDict

    # first count the number of mismatches to the off target (in seed region too)
    mismatches, noneInSeed = countMismatches(
        guideDict, rgen["SeedRegion"], offTargetGuide
    )

    # update the guideDict to reflect the new off target
    try:
        guideDict["offtarget_counts"] = (
            initializeMismatchCount(mismatches)
            if "offtarget_counts" not in guideDict
            else incrementMismatchCount(guideDict["offtarget_counts"], mismatches)
        )
        if noneInSeed:
            guideDict["offtargets_seed"] = (
                initializeMismatchCount(mismatches)
                if "offtargets_seed" not in guideDict
                else incrementMismatchCount(guideDict["offtargets_seed"], mismatches)
            )
    except Exception:
        print(
            f"Error: Update of Guide Dict failed. Number of mismatches: {mismatches}, {offTargetSeq} {guideDict['guide_seq']}"
        )

    # change case of the off-target sequence based on the mismatched bases (lowercase)
    offTargetGuide = changeCase(guideDict["guide_seq"], offTargetGuide)
    # add the off-target attributes to the guide dict
    if "offtargets" not in guideDict:
        guideDict["offtargets"] = []
    guideDict["offtargets"].append(
        {"seq": offTargetGuide, "pam": offTargetPAM, "loc": offTargetLoc}
    )

    return guideDict


"""
# option to also capitalize pam
def changeCase(guide, offtarget_guide, offtarget_pam, pam_location):
	assert (len(guide) == len(offtarget_guide)), "Guide and Off-Target must be of same length"
	resultGuide = ''
	resultPam = ''
	for b in range(0, len(guide)):
		resultGuide = resultGuide+guide[b] if guide[b].lower() == offtarget_guide[b].lower() else resultGuide+(offtarget_guide[b].lower())
		if b < len(pam):
			resultPam = resultPam+pam[b] if pam[b].lower() == offtarget_pam[b].lower() else resultPam+(offtarget_pam[b].lower())

	return resultGuide, resultPam
"""


def changeCase(guide, offtarget_guide):
    """change case to indicate matches/mismatches to offtarget"""
    assert len(guide) == len(
        offtarget_guide
    ), "Guide and Off-Target must be of same length"
    resultGuide = ""
    for b in range(0, len(guide)):
        if (
            guide[b].upper() == offtarget_guide[b].upper()
            or offtarget_guide[b].upper() == "N"
        ):
            resultGuide += offtarget_guide[b].upper()
        else:
            resultGuide += offtarget_guide[b].lower()

    return resultGuide


def countOffTargets(batchID, potentialGuides, rgen, maxOffTargets, tempfile_directory):
    """
    Given a batchID, list of potential guides, and an rgen, parse the extended fastas and get dict of off-targets.
    Using the rgen, remove all the matches that aren't adjacent to a PAM motif
    """
    offTargetMotifs = getMotifs(
        rgen["OffTargetPAMS"]
    )  # NB: OffTargetPAMS should also include the classical PAM for the rgen
    pamLocation = rgen["PamLocation"]
    # rgenSeed = rgen['SeedRegion']

    # initialize the counts, offtarget list, and max_exceeded flag
    for guideID, guide in potentialGuides.items():
        guide["offtarget_counts"] = [0] * 5
        guide["offtargets_seed"] = [0] * 5
        guide["max_exceeded"] = False
        guide["offtargets"] = []

    # open the extended fasta
    with open(
        os.path.join(tempfile_directory, str(batchID) + "_extended.fa"), "r"
    ) as f:
        for line in f:
            if line.startswith(">"):
                guideID, location = line.strip().split(
                    "_"
                )  # parse out label and location
                guideID = guideID[1:]  # remove > marker
                if (
                    potentialGuides[guideID]["max_exceeded"]
                    or potentialGuides[guideID]["skip"]
                ):
                    continue
                seq = next(f).strip()  # seq is next line after label
                strand = location[-1]
                # only add off-target to guide's dict if it has the motif
                if hasMotif(offTargetMotifs, pamLocation, strand, seq):
                    if maxOffTargets and sum(
                        potentialGuides[guideID]["offtarget_counts"]
                    ) >= int(maxOffTargets):
                        # don't track any more
                        potentialGuides[guideID]["max_exceeded"] = True
                    else:
                        potentialGuides[guideID] = processOffTarget(
                            potentialGuides[guideID], rgen, location, seq
                        )

    return potentialGuides


def convertExtendedBedToFasta(batchID, genome, genome_fa, tempfile_directory):
    """uses bedtools to convert the extended bed to fasta"""
    # template command
    extendedBed = os.path.join(tempfile_directory, str(batchID) + "_extended.bed")
    extendedFasta = os.path.join(tempfile_directory, str(batchID) + "_extended.fa")

    bashCommand = [
        "bedtools",
        "getfasta",
        "-fi",
        genome_fa,
        "-bed",
        extendedBed,
        "-name",
        "-fo",
        extendedFasta,
    ]
    p = run(bashCommand, stderr=PIPE)
    if p.stderr and not p.stderr.startswith(b"Warning"):
        # raise errors, ignore warnings
        raise Exception("Error in bedtools getfasta command: " + str(p.stderr))

    """
	twoBitTwoFaCommand = ["twoBitToFa", os.path.join(dir_path,"../../../jbrowse/data/mm10/processed/mm10.2bit"),"-bed="+extendedBed, extendedFasta]
	p = run(twoBitTwoFaCommand,stderr=PIPE)
	if p.stderr:
		raise Exception("Error in twoBitToFa: "+str(p.stderr))
	"""

    return


def extendBed(batchID, potentialGuides, genome, rgen, tempfile_directory):
    """extend the locations in the guide's bed file to include the PAM"""
    # store relevant rgen attributes
    pamLocation = rgen["PamLocation"]
    pamLength = len(rgen["PAM"])
    # connect to the genome db (to check chrom lengths later)
    dbConnection = Config(genome)
    # bed files name/location
    bedFile = os.path.join(tempfile_directory, str(batchID) + ".bed")
    extendedBed = os.path.join(tempfile_directory, str(batchID) + "_extended.bed")
    # track repetetive guides to prevent writing their off-targets
    skipped_guides = []
    if os.path.isfile(bedFile):
        # rewrite every line of original bed into extended bed
        originalBed = open(bedFile, "r")
        extendedBed = open(extendedBed, "w+")
        for line in originalBed.readlines():
            chm, start, end, label, score, strand = [
                x.strip() for x in line.split("\t")[0:6]
            ]
            if label in skipped_guides:
                continue
            elif potentialGuides[label]["skip"]:
                skipped_guides.append(label)
            start, end = map(int, [start, end])
            assert start < end, str(bedFile) + " chr locations out of order"
            # calculate extension
            if (pamLocation == "downstream" and strand == "+") or (
                pamLocation == "upstream" and strand == "-"
            ):
                end = int(end) + pamLength
            elif (pamLocation == "downstream" and strand == "-") or (
                pamLocation == "upstream" and strand == "+"
            ):
                start = int(start) - pamLength
            else:
                raise Exception(
                    "Unexpected pamLocation ("
                    + str(pamLocation)
                    + ") and/or strand ("
                    + str(strand)
                    + ")"
                )

            # ensure that the extension doesn't create an illegal location, skip writing if so
            if start < 0 or end > dbConnection.chromSizes[chm]:
                continue

            # rewrite the line, and put the location in the label (for use in fasta)
            newLabel = (
                label.split("_")[0]
                + "_"
                + chm
                + ":"
                + str(start)
                + "-"
                + str(end)
                + ":"
                + strand
            )
            extendedBed.write(
                "\t".join(map(str, [chm, start, end, newLabel, score, strand])) + "\n"
            )

        originalBed.close()
        extendedBed.close()
    else:
        raise FileNotFoundError("Extended Bed File Not Found")

    return extendedBed


def runAlignment(genome, fastaFile, genome_fa, tempfile_directory):
    """execute a shell script to perform bwa alignment on a fasta file"""
    # if troubleshooting the bwa step, replace the stdout and stderr variables with PIPE to see output
    p = Popen(
        [
            os.path.join(dir_path, "bwa_align.sh"),
            genome_fa,
            os.path.basename(fastaFile.name),
            tempfile_directory,
        ],
        stdin=PIPE,
        stdout=DEVNULL,
        stderr=DEVNULL,
        encoding="utf-8",
    )
    out, err = p.communicate()
    if err:
        print(err)

    return


def screenRepetetive(batchID, potentialGuides, tempfile_directory):
    """marks guides with a 'repetetive' flag in their sam file so they're screened out of the off-target search"""
    sam_file = os.path.join(tempfile_directory, str(batchID) + ".sam")

    if os.path.exists(sam_file):
        for guideID, guide in potentialGuides.items():
            p = run(["grep", "-m", "1", "-e", guideID, sam_file], stdout=PIPE)
            # grab the tags (excluding the last one containing the locations)
            hit_tags = p.stdout.decode("utf-8").strip().split("\t")[11:-1]
            # TODO if not hit_tags -> investigate
            tags = {x.split(":", 1)[0]: x.strip().split(":", 1)[1] for x in hit_tags}
            if "XT" in tags and tags["XT"].endswith(":R"):
                # repeat flag set by bwa for guide hits
                potentialGuides[guideID]["skip"] = True
            elif "X1" in tags and int(tags["X1"].split(":")[1]) > 50000:
                # skip if more than 50k suboptimal hits (they won't be reported by bwa)
                potentialGuides[guideID]["skip"] = True
            else:
                potentialGuides[guideID]["skip"] = False


def findOffTargets(
    potentialGuides,
    rgenID,
    genome,
    maxOffTargets,
    batchID,
    genome_fa,
    tempfile_directory,
):
    time_0 = time.time()
    logging.debug("\t\t\t\t[STARTED]\t\tGetting rgen record...")

    # connect to database and get rgen variables from id
    rgen = getRgenRecord(rgenID)

    # write fasta of guides
    time_1 = time.time()
    logging.debug(
        f"\t\t\t\t[FINISHED]\tGot rgen record in {str(round(time_1-time_0,4))}s"
    )
    logging.debug("\t\t\t\t[STARTED]\t\tWriting fasta file...")

    fastaFile = writeFasta(batchID, potentialGuides, tempfile_directory)

    time_2 = time.time()
    logging.debug(
        f"\t\t\t\t[FINISHED]\tWrote fasta file in {str(round(time_2-time_1,4))}s"
    )
    logging.debug("\t\t\t\t[STARTED]\t\tRunning bwa alignment...")

    runAlignment(genome, fastaFile, genome_fa, tempfile_directory)

    time_3 = time.time()
    logging.debug(
        f"\t\t\t\t[FINISHED]\tRan bwa alignment in {str(round(time_3-time_2,4))}s"
    )
    logging.debug("\t\t\t\t[STARTED]\t\tScreening repeats...")

    screenRepetetive(batchID, potentialGuides, tempfile_directory)

    time_4 = time.time()
    logging.debug(
        f"\t\t\t\t[FINISHED]\tScreened repeats in {str(round(time_4-time_3,4))}s"
    )
    logging.debug("\t\t\t\t[STARTED]\t\tExtending beds...")
    extendBed(batchID, potentialGuides, genome, rgen, tempfile_directory)

    time_5 = time.time()
    logging.debug(
        f"\t\t\t\t[FINISHED]\tExtended beds in {str(round(time_5-time_4,4))}s"
    )
    logging.debug("\t\t\t\t[STARTED]\t\tConverting bed coordinates to fasta...")

    convertExtendedBedToFasta(batchID, genome, genome_fa, tempfile_directory)

    time_6 = time.time()
    logging.debug(
        f"\t\t\t\t[FINISHED]\tConverted bed coordinates to fasta in {str(round(time_6-time_5,4))}s"
    )
    logging.debug("\t\t\t\t[STARTED]\t\tCounting off-targets...")

    potentialGuides = countOffTargets(
        batchID, potentialGuides, rgen, maxOffTargets, tempfile_directory
    )

    time_7 = time.time()
    logging.debug(
        f"\t\t\t\t[FINISHED]\tCounted off-targets in {str(round(time_7-time_6,4))}s"
    )

    return potentialGuides


def main():
    """
    uses bwa aln to find the potential off-targets for a dictionary of guides given:
     rgenID
     genome
     bwa_index
     tempfile directory (to write intermediate files)
    """
    if len(sys.argv) != 6:
        print(
            "Requires a dictionary of potentialGuides, rgenID, genome, bwa_index, and tempfile directory"
        )
    else:
        guides, rgenID, genome, genome_fa, tempfile_directory = sys.argv[1:]
        batchID = binascii.b2a_hex(os.urandom(9)).decode("utf-8")
        # guides, rgenID, genome, genome_fa, tempfile_directory = sys.argv[1:]
        result = findOffTargets(
            guides, rgenID, genome, batchID, genome_fa, tempfile_directory
        )
        print(result)


if __name__ == "__main__":
    main()
