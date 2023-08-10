#!/usr/bin/python3.7
"""
Hillary Elrick, adapted from Greg Clark's Code
November 2018

Class to create APE files

"""

import os
import re
import sys
import time
from urllib.parse import unquote

dir_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(dir_path, ".."))
APE_DIR = "files/apeFiles"


class APE(object):
    # all three must be passed, but only one should have a value (other parameters should be explicitly set to None)
    def __init__(self, geneObject, guideObject, mongoRecords):
        if not geneObject and not guideObject and not mongoRecords:
            raise ValueError(
                "One of gene, guide or mongo record need to be defined when creating APE object"
            )
        if geneObject:
            if guideObject or mongoRecords:
                raise ValueError(
                    "Only one of gene, guide or mongo record should be defined"
                )
            self.geneObject = geneObject
            self.geneAPE = self.buildGeneAPE()

        elif guideObject:
            if geneObject or mongoRecords:
                raise ValueError(
                    "Only one of gene, guide or mongo record should be defined"
                )

            self.guideObject = guideObject
            self.geneObject = guideObject.super

        elif mongoRecords:
            if geneObject or guideObject:
                raise ValueError(
                    "Only one of gene, guide or mongo record should be defined"
                )

            # mongoRecords is 2d list: [[geneObject],[guideRecord1, guideRecord2, ...],[primerRecord1, primerRecord2, ...]]
            self.geneObject = mongoRecords[0][0]
            self.guides = mongoRecords[1]
            self.primers = mongoRecords[2]

    def writeMongoAPE(self, APEString):
        """
        Once the APE for a set of Mongo Records has been created, this is called from the
        generateAPE.py script to write the completed string to file
        """
        # write an APE generated from Mongo records to the /files/ape/features directory
        try:
            filename = str(
                self.geneObject.geneName
                + "_"
                + str(self.geneObject.release)
                + "-automated"
                + ".ape"
            )
            filepath = os.path.join(
                APE_DIR, self.geneObject.genome, "features", filename
            )
            apeFile = open(
                os.path.join(
                    self.geneObject.Config.ROOT_PATH, "src/primer-design", filepath
                ),
                "w",
            )
            apeFile.write(APEString)
            apeFile.close()
        except Exception as e:
            print("Problem writing APE file " + str(e))

        return os.path.join("..", filepath)

    def labelGuides(self):
        # puts automatic labels on guides
        nGuides = len(self.guides)
        for i, guide in enumerate(self.guides):
            if nGuides == 4:
                if i == 0:
                    guide["label"] = "gRNA_U5"
                elif i == 1:
                    guide["label"] = "gRNA_U3"
                elif i == 2:
                    guide["label"] = "gRNA_D5"
                elif i == 3:
                    guide["label"] = "gRNA_D3"
            elif nGuides == 3:
                if i == 0:
                    guide["label"] = "gRNA_U"
                elif i == 1:
                    guide["label"] = "gRNA_M"
                elif i == 2:
                    guide["label"] = "gRNA_D"
            elif nGuides == 2:
                if i == 0:
                    guide["label"] = "gRNA_U"
                elif i == 1:
                    guide["label"] = "gRNA_D"
            else:
                print(
                    "Error: Problem labelling guides, number of accepted guides must be 2, 3, or 4"
                )

        return

    def addGuidesMongo(self, fileToWrite):
        # add the APE locations & directions to the guides
        for guide in self.guides:
            # figure out where the guides are
            start = None
            guideSeq = guide["guideSeq"]
            try:
                guide["start"] = int(
                    re.search(guideSeq, self.geneObject.sequence, re.IGNORECASE).start()
                )
                guide["end"] = guide["start"] + len(guideSeq)
                guide["direction"] = "F"
            except Exception:
                # guide sequence wasn't found
                # reverse and search again
                guideSeq = revSeq(guideSeq)
                try:
                    guide["start"] = int(
                        re.search(
                            guideSeq, self.geneObject.sequence, re.IGNORECASE
                        ).start()
                    )
                    guide["end"] = guide["start"] + len(guideSeq)
                    guide["direction"] = "R"
                except Exception:
                    print("Unable to find one of the guides in the gene sequence")

        # sort the list of guides
        self.guides.sort(key=lambda k: k["start"])
        # if any labels are undefined, use automatic labels
        for g in self.guides:
            if g["label"] == "" or g["label"] is None:
                self.labelGuides()
                break

        # finally, add all the guides to the file string
        for guide in self.guides:
            start = str(guide["start"] + 1)
            end = str(guide["end"])
            direction = guide["direction"]
            label = unquote(guide["label"])
            fileToWrite += guideFeatureAPE(start, end, direction, label)

        return fileToWrite

    def addGuides(self, fileToWrite):
        # add all the guides from the guide object
        for guide in self.guideObject.gRNAs:
            start = str(guide[7] + 1)
            end = str(guide[8])
            direction = guide[9]
            label = unquote(guide[10])

            fileToWrite += guideFeatureAPE(start, end, direction, label)

        return fileToWrite

    def calculateDeletionSizes(self, ePrimer):
        deletionStrings = []
        if len(ePrimer["productSize"].split(";")) > 1:
            fragmentSize = int(ePrimer["productSize"].split(";")[1])
        else:
            fragmentSize = int(ePrimer["productSize"])

        # calculate the em deletion size for every possible guide pair deletion
        for i in range(0, len(self.guideObject.gRNAs)):
            for j in range(i, len(self.guideObject.gRNAs)):
                if i != j:
                    guidePairCutSize = abs(
                        self.guideObject.getCut(self.guideObject.gRNAs[i])
                        - self.guideObject.getCut(self.guideObject.gRNAs[j])
                    )
                    deletionStrings.append(
                        str(self.guideObject.gRNAs[i][10])
                        + " - "
                        + str(self.guideObject.gRNAs[j][10])
                        + " : "
                        + str(fragmentSize - guidePairCutSize)
                    )

        # finally, also report fragement size for no deletion (this is stored in the ePrimer dict)
        deletionStrings.append("No Deletion: " + str(fragmentSize))

        return deletionStrings

    def calculateDeletionSizesMongo(self, ePrimer):
        deletionStrings = []
        if len(ePrimer["productSize"].split(";")) > 1:
            fragmentSize = int(ePrimer["productSize"].split(";")[1])
        else:
            fragmentSize = int(ePrimer["productSize"])

        for i in range(0, len(self.guides)):
            for j in range(i, len(self.guides)):
                if i != j:
                    guidePairCutSize = abs(
                        getCut(self.guides[i]) - getCut(self.guides[j])
                    )
                    deletionStrings.append(
                        str(self.guides[i]["label"])
                        + " - "
                        + str(self.guides[j]["label"])
                        + " : "
                        + str(fragmentSize - guidePairCutSize)
                    )

        deletionStrings.append("No Deletion: " + str(fragmentSize))

        return deletionStrings

    def addPrimersMongo(self, fileToWrite, apeString, lastmatch):
        geneDirection = self.geneObject.strand
        self.guides.sort(key=lambda k: k["start"])
        for mongoPrimer in self.primers:
            # dict for storing the attributes to print
            primerPrint = dict(mongoPrimer)
            # get the ape start from the actual genomic start of the primers
            if geneDirection == -1:
                primerPrint["leftstart"] = (
                    int(self.geneObject.sequenceEnd)
                    - int(mongoPrimer["left_genomicLocation"])
                    + 1
                )
                primerPrint["rightstart"] = (
                    int(self.geneObject.sequenceEnd)
                    - int(mongoPrimer["right_genomicLocation"])
                    + 1
                )

            else:
                primerPrint["leftstart"] = (
                    int(mongoPrimer["left_genomicLocation"])
                    - int(self.geneObject.sequenceStart)
                    + 1
                )
                primerPrint["rightstart"] = (
                    int(mongoPrimer["right_genomicLocation"])
                    - int(self.geneObject.sequenceStart)
                    + 1
                )

            fileToWrite += primerFeatureAPE(primerPrint)

        # find last comment line
        for comment in re.finditer(r"COMMENT(?!.*COMMENT)", fileToWrite):
            lastComment = comment

        # save text before insert
        addComment = fileToWrite[0 : lastComment.end()]

        """
		Only will report common forward primers if there are exactly 2
		primers and one is EM and one is WT (the standard case). If 
		another case where common forward primers need to be reported
		arises, it should be added here.
		"""
        if len(self.primers) == 2:
            # check that they're not the same type (thus one must be wt, the other em)
            if self.primers[0]["type"].lower() != self.primers[1]["type"].lower():
                # compare their forward (left) primers
                if (
                    self.primers[0]["leftprimer"].lower()
                    == self.primers[1]["leftprimer"].lower()
                ):
                    addComment += "\nCOMMENT     "
                    addComment += (
                        "\nCOMMENT     *EM and WT SHARE A COMMON FORWARD PRIMER*"
                    )

        # add all possible em product sizes
        for primer in self.primers:
            if primer["type"].lower() == "em":
                addComment += "\nCOMMENT     "
                addComment += "\nCOMMENT     Predicted Fragement Sizes:"

                deletionSizes = self.calculateDeletionSizesMongo(primer)
                for delSize in deletionSizes:
                    addComment += "\nCOMMENT     " + delSize

        addComment += fileToWrite[lastComment.end() :]

        return addComment + apeString[lastmatch.end() :]

    def addPrimers(self, fileToWrite, apeString, lastmatch):
        # store a dict of all the fileToWrite strings with the different primers added
        filedict = {}
        if len(self.guideObject.wtPrimers) > 0 and len(self.guideObject.emPrimers) > 0:
            # both em and wt primers were designed
            for w, wPrimer in self.guideObject.wtPrimers.items():
                wtString = fileToWrite
                wtString += primerFeatureAPE(wPrimer)
                for e, ePrimer in self.guideObject.emPrimers.items():
                    dictString = wtString  # string that will be stored in the dict
                    dictString += primerFeatureAPE(ePrimer)
                    # find last comment line
                    for comment in re.finditer(r"COMMENT(?!.*COMMENT)", dictString):
                        lastComment = comment
                    # save text before insert
                    addComment = dictString[0 : lastComment.end()]
                    # adds a note if the wt and em share a common forward primer
                    if wPrimer["leftprimer"] == ePrimer["leftprimer"]:
                        addComment += "\nCOMMENT     "
                        addComment += (
                            "\nCOMMENT     *EM and WT SHARE A COMMON FORWARD PRIMER*"
                        )
                    # also add all possible em product sizes
                    addComment += "\nCOMMENT     "
                    addComment += "\nCOMMENT     Predicted Fragement Sizes:"
                    deletionSizes = self.calculateDeletionSizes(ePrimer)
                    for delSize in deletionSizes:
                        addComment += "\nCOMMENT     " + delSize
                    # append rest of text
                    addComment += dictString[lastComment.end() :]
                    # save entire string with sequence to the filedict
                    filedict[(w, e)] = addComment + apeString[lastmatch.end() :]

        elif len(self.guideObject.wtPrimers) > 0:
            # only wt primers were designed
            for w, wPrimer in self.guideObject.wtPrimers.items():
                wtString = fileToWrite
                wtString += primerFeatureAPE(wPrimer)
                filedict[(w, -1)] = wtString + apeString[lastmatch.end() :]

        elif len(self.guideObject.emPrimers) > 0:
            # only em primers were designed
            for e, ePrimer in self.guideObject.emPrimers.items():
                dictString = fileToWrite
                dictString += primerFeatureAPE(ePrimer)
                # find last comment line
                for comment in re.finditer(r"COMMENT(?!.*COMMENT)", dictString):
                    lastComment = comment
                # save text before insert
                addComment = dictString[0 : lastComment.end()]
                addComment += "\nCOMMENT     "
                addComment += "\nCOMMENT     Predicted Fragement Sizes:"
                deletionSizes = self.calculateDeletionSizes(ePrimer)
                for delSize in deletionSizes:
                    addComment += "\nCOMMENT     " + delSize
                # append rest of text
                addComment += dictString[lastComment.end() :]
                filedict[(-1, e)] = addComment + apeString[lastmatch.end() :]

        return filedict

    def splitAPE(self):
        apeString = "\n".join(
            self.geneObject.APE
        )  # plain APE from the parent Gene object
        lastmatch = False
        # get the position of the last exon in the APE features (to write the guides after it)
        for match in re.finditer(
            r"exon\s*[0-9]*..[0-9]*\s*/label=\"[^\"]*\"\s*/ApEinfo_fwdcolor=\"[^\"]*\"\s*/ApEinfo_revcolor=\"[^\"]*\"\s*/ApEinfo_graphicformat=\"[^\"]*\"",
            apeString,
        ):
            lastmatch = match
        if not lastmatch:
            lastmatch = re.search(
                r"FEATURES             Location/Qualifiers", apeString
            )
            if not lastmatch:
                print("ERROR: unable to parse APE file")

        # add beginning of APE to file string
        fileToWrite = apeString[0 : lastmatch.end()]

        return apeString, fileToWrite, lastmatch

    def addFeatures(self):
        # get the APE pieces & splitpoint
        apeString, fileToWrite, lastmatch = self.splitAPE()
        # then add the guides
        fileToWrite = self.addGuides(fileToWrite)
        # finally, all the primer pairs
        filedict = self.addPrimers(fileToWrite, apeString, lastmatch)

        return filedict

    def addFeaturesMongo(self):
        # split the APE
        apeString, fileToWrite, lastmatch = self.splitAPE()
        # then add the guides from Mongo
        fileToWrite = self.addGuidesMongo(fileToWrite)
        # finally, add the primer pairs from Mongo
        fileString = self.addPrimersMongo(fileToWrite, apeString, lastmatch)

        return fileString

    def buildGeneAPE(self):
        filetowrite = []
        # construct the header of the APE file
        comment = "COMMENT    "
        filetowrite.append(
            "LOCUS       "
            + self.geneObject.symbol
            + "_gDNA\t\t"
            + str(int(self.geneObject.sequenceLength) + 1)
            + " bp ds-DNA     linear       "
            + time.strftime("%d-%b-%Y").upper()
        )
        if self.geneObject.exons:
            filetowrite.append(
                "ACCESSION   " + str(",".join(list(zip(*self.geneObject.exons))[5]))
            )
        filetowrite.append("KEYWORDS    ." + (self.geneObject.symbol).upper())
        filetowrite.append("SOURCE      " + str(self.geneObject.Config.organismName))
        filetowrite.append(
            comment
            + ">dna:chromosome: "
            + self.geneObject.genome
            + ":"
            + self.geneObject.chromosome
            + "("
            + str(self.geneObject.strand)
            + ")"
            + ":"
            + str(self.geneObject.sequenceStart)
            + "..."
            + str(self.geneObject.sequenceEnd)
        )
        filetowrite.append(comment)
        filetowrite.append(
            comment
            + self.geneObject.symbol.capitalize()
            + " gDNA and 1000bp upstream and downstream flank"
        )
        filetowrite.append(comment)
        filetowrite.append(comment + "Created by script on " + time.strftime("%c %Z"))
        filetowrite.append(comment)
        filetowrite.append("FEATURES             Location/Qualifiers")

        if self.geneObject.exons:
            # write the gene's exons to the APE file
            for e in self.geneObject.exons:
                e_start, e_end, e_strand, startPhase, endPhase, ensemblID = e
                if str(startPhase) == "-1":
                    startPhase = "-"
                if str(endPhase) == "-1":
                    endPhase = "-"
                ensemblID = ensemblID + " " + str(startPhase) + "/" + str(endPhase)

                relativeStart = int(e_start) - self.geneObject.sequenceStart
                exonLength = abs(e_end - e_start) + 1
                if str(e_strand) == "-1":
                    relativeStart = relativeStart - 1
                    filetowrite.append(
                        "     exon            "
                        + str(
                            self.geneObject.sequenceLength
                            - relativeStart
                            - exonLength
                            + 1
                        )
                        + ".."
                        + str(self.geneObject.sequenceLength - relativeStart)
                    )
                else:
                    filetowrite.append(
                        "     exon            "
                        + str(relativeStart + 1)
                        + ".."
                        + str(relativeStart + exonLength)
                    )
                filetowrite.append('                     /label="' + ensemblID + '"')
                filetowrite.append('                     /ApEinfo_fwdcolor="#ffedc6"')
                filetowrite.append('                     /ApEinfo_revcolor="#ffcc66"')
                filetowrite.append(
                    '                     /ApEinfo_graphicformat="arrow_data {{0 1 2 0 0 -1} {} 0}'
                )
                filetowrite.append('                     width 5 offset 0"')

        filetowrite.append("ORIGIN")
        # format raw sequence before appending to APE
        filetowrite.append(formatSequence(self.geneObject.sequence))

        return filetowrite


def guideFeatureAPE(start, end, direction, label):
    guideString = ""
    # add the coordinates
    if direction == "F":
        guideString += "\n     misc_feature    " + str(start) + ".." + str(end) + "\n"
    elif direction == "R":
        guideString += (
            "\n     misc_feature    complement(" + str(start) + ".." + str(end) + ")\n"
        )
    else:
        print("Problem writing guides to APE file. No direction specified")
        sys.exit()

    # print the label and remaining tags
    guideString += '                     /locus_tag="' + label + '"\n'
    guideString += '                     /label="' + label + '"\n'
    guideString += '                     /ApEinfo_label="' + label + '"\n'
    guideString += '                     /ApEinfo_fwdcolor="#2dc2ff"\n'
    guideString += '                     /ApEinfo_revcolor="#0064ff"\n'
    guideString += '                     width 5 offset 0"'

    return guideString


def primerFeatureAPE(primer):
    fwdColor = "#aa81ff"
    revColor = "#aa400ff"
    primerString = ""
    # write the left wt primer
    LeftStart = str(primer["leftstart"])
    LeftEnd = str(int(primer["leftstart"]) + int(primer["leftlen"]) - 1)
    LeftLabel = primer["type"].lower() + "_F1"
    primerString += "\n     primer_bind    " + LeftStart + ".." + LeftEnd + "\n"
    primerString += '                     /locus_tag="' + LeftLabel + '"\n'
    primerString += '                     /label="' + LeftLabel + '"\n'
    primerString += '                     /ApEinfo_label="' + LeftLabel + '"\n'
    primerString += '                     /ApEinfo_fwdcolor="' + fwdColor + '"\n'
    primerString += '                     /ApEinfo_revcolor="' + revColor + '"\n'
    # primerString += "                     /ApEinfo_graphicformat=\"arrow_data {{0 1 2 0 0 -1} {} 0}\n"
    # primerString += "                     width 5 offset 0\""

    # write the right wt primer
    RightStart = str(int(primer["rightstart"]) + 1)
    RightEnd = str(int(primer["rightstart"]) - int(primer["rightlen"]))
    RightLabel = primer["type"].lower() + "_R1"
    primerString += (
        "\n     primer_bind    complement(" + RightEnd + ".." + RightStart + ")\n"
    )
    primerString += '                     /locus_tag="' + RightLabel + '"\n'
    primerString += '                     /label="' + RightLabel + '"\n'
    primerString += '                     /ApEinfo_label="' + RightLabel + '"\n'
    primerString += '                     /ApEinfo_fwdcolor="' + fwdColor + '"\n'
    primerString += '                     /ApEinfo_revcolor="' + revColor + '"\n'
    # primerString += "                     /ApEinfo_graphicformat=\"arrow_data {{0 1 2 0 0 -1} {} 0}\n"
    # primerString += "                     width 5 offset 0\""

    return primerString


def formatSequence(seq):
    """
    Format the genomic sequence passed (seq) for the APE file so it has an indent,
    base number, and 60 bases per line with a space separator every 10 bases and
    two slashes '//' to mark the end of the sequence

    *Adapted from Greg's Code*
    """
    # split sequence into 10bp chunks
    splitSequence = [seq[i : (i + 10)] for i in range(0, len(seq), 10)]
    count = 1
    baseNum = 1
    seqLine = ""
    seqString = ""
    for chunk in splitSequence:
        # length of the indent needs to take into account the number at the beginning of the line
        indent = 9 - len(str(baseNum))
        if count % 6 == 1:
            # create the beginning of the line with first 10 bases
            seqLine = " " * indent + str(baseNum) + " " + chunk
        elif count % 6 != 0:  # we aren't at the last chunk of the line
            seqLine += " " + chunk  # print a space and the next 10 bases
        else:
            # here we know the count is a multiple of 6 so it's the last chunk of the line
            seqLine += " " + chunk + "\n"  # print the last 10 bases and a newline
            seqString += seqLine  # add the line to the formatted string
            baseNum += 60  # increment the base count by 60
        count += 1
    # if the previous chunk wasn't a multiple of 6 and wasn't added to the string
    if (count - 1) % 6 != 0:
        seqString += seqLine
    # add the EOF character
    seqString += "\n//"

    return seqString


# returns actual cutsite for a guide based on the PAM and direction of a guide
def getCut(guide):
    # cuts occur 3-4 bp (using 3) upstream of PAM (which is immediately after the guide sequence)
    if guide["direction"] == "F":
        # if guide is forward, cut is 3 bases upstream of end
        return guide["end"] - 3
    elif guide["direction"] == "R":
        # if guide is reverse, cut is 3 bases downstream of start
        # (start/end are defined by order 5'-3' on coding strand)
        return guide["start"] + 3


def revSeq(seq):
    reversedSeq = seq[::-1]
    complements = {"A": "T", "C": "G", "G": "C", "T": "A"}
    return "".join([complements[base] for base in reversedSeq])
