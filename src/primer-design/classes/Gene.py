#!/usr/bin/env python3.7

import os
import sys

import requests

sys.path.append(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "helpers")
)
from classes.APE import APE
from Config import Config

server = "https://rest.ensembl.org"


class Gene(object):
    # where the APE files are written
    APE_PATH = "files/apeFiles"

    # initialize with gene name
    def __init__(self, geneName, genome, suppressWarnings=False, ENSID=None):
        self.genome = genome
        self.Config = Config(genome)  # object for db and tool connection
        self.geneName = geneName
        self.suppressWarnings = suppressWarnings
        self.release = self.checkRelease()
        if ENSID:
            self.ensemblID = ENSID
            self.featureType = self.getFeatureType()
        if not ENSID:
            self.ensemblID, self.featureType = self.dbGetEnsemblID()

        (
            self.symbol,
            self.chromosome,
            self.gene_start,
            self.gene_end,
        ) = self.getGeneCoordinates()
        self.exons = self.getExons()
        self.sortedExons = self.exons  # will be sorted in getSequenceAttributes
        (
            self.sequence,
            self.sequenceLength,
            self.sequenceStart,
            self.sequenceEnd,
            self.strand,
        ) = self.getSequenceAttributes()

        # create an APE object using the current Gene object
        self.APEObj = APE(self, None, None)
        self.APE = self.APEObj.geneAPE

    def checkRelease(self):
        ext = "/info/data"
        try:
            releaseRequest = requests.get(
                server + ext, headers={"Content-Type": "application/json"}, timeout=30
            )
        except requests.exceptions.Timeout:
            returnError(f"The Ensembl Rest API is not responding ({server + ext})")
        except Exception:
            returnError("Problem with Ensembl Rest API call")
        if not releaseRequest.ok:
            try:
                releaseRequest.raise_for_status()
            except Exception as e:
                returnError(f"Problem fetching release information from Ensembl: {e}")
        release = releaseRequest.json()["releases"]

        if len(release) != 1:
            warningString = (
                "The API call to Ensembl for this gene returned multiple releases: "
            )
            for r in release:
                warningString += str(r)
            returnWarning(warningString)

        return release[0]

    """
	Get the feature type when the ENSID is provided
	"""

    def getFeatureType(self):
        ext = f"/lookup/id/{self.ensemblID}"
        try:
            featureRequest = requests.get(
                server + ext, headers={"Content-Type": "application/json"}, timeout=30
            )
        except requests.exceptions.Timeout:
            returnError(f"The Ensembl Rest API is not responding ({server + ext})")
        except Exception:
            returnError("Problem with Ensembl Rest API call")

        if not featureRequest.ok:
            try:
                featureRequest.raise_for_status()
            except Exception as e:
                returnError(f"Problem fetching feature type from Ensembl: {e}")

        decodedFeature = featureRequest.json()
        try:
            featureType = decodedFeature["object_type"]
        except Exception as e:
            printError(f"Problem parsing result from Ensembl: {e}")

        return featureType.lower()

    """
	Get the ensembl ID for a gene using the MongoDB that is stored localled
	"""

    def dbGetEnsemblID(self):
        geneCollection = self.Config.curr_geneCollection
        geneQuery = {"Name": self.geneName}
        geneMatch = geneCollection.find(geneQuery)

        if geneMatch.count() > 1:
            returnError(
                "More than one result found in the database for the gene "
                + str(self.geneName)
            )
        elif geneMatch.count() < 1:
            returnError(
                "No results found in the database for the gene " + str(self.geneName)
            )

        return geneMatch[0]["ENSID"], "gene"

    def getGeneCoordinates(self):
        ext = f"/overlap/id/{self.ensemblID}?feature={self.featureType}"
        try:
            geneRequest = requests.get(
                server + ext, headers={"Content-Type": "application/json"}, timeout=30
            )
        except requests.exceptions.Timeout:
            returnError(f"The Ensembl Rest API is not responding ({server + ext})")
        except Exception:
            returnError("Problem with Ensembl Rest API call")
        if not geneRequest.ok:
            try:
                geneRequest.raise_for_status()
            except Exception as e:
                returnError(f"Problem fetching gene features from Ensembl: {e}")
        decodedGene = geneRequest.json()
        try:
            decodedGene = list(
                filter(lambda l: l["gene_id"] == self.ensemblID, decodedGene)
            )
            if len(decodedGene) > 1:
                returnError(
                    "More than one gene found with the same ensemblID, using first one found"
                )
            geneInfo = decodedGene[0]
        except (KeyError, IndexError):
            returnError("No features found for this gene")

        if "external_name" in geneInfo:
            symbol = geneInfo["external_name"]
        elif "gene_id" in geneInfo:
            symbol = geneInfo["gene_id"]
        elif "id" in geneInfo:
            symbol = geneInfo["id"]
        else:
            returnError("Unable to determine gene symbol from Ensembl API Response")

        chromosome = geneInfo["seq_region_name"]
        gene_start = geneInfo["start"]
        gene_end = geneInfo["end"]

        return symbol, chromosome, gene_start, gene_end

    def getExons(self):
        # gets the transcripts and exons in the gene's region, only fetching protein-coding transcripts
        ext = f"/overlap/region/{self.Config.organismName}/{self.chromosome}:{self.gene_start}-{self.gene_end}?feature=exon;feature=transcript;biotype=protein_coding"
        try:
            featureRequest = requests.get(
                server + ext, headers={"Content-Type": "application/json"}, timeout=30
            )
        except requests.exceptions.Timeout:
            returnError(f"The Ensembl Rest API is not responding ({server + ext})")
        except Exception:
            returnError("Problem with Ensembl Rest API call")
        if not featureRequest.ok:
            try:
                featureRequest.raise_for_status()
            except Exception as e:
                returnError(
                    f"Problem fetching protein-coding transcripts for this gene from Ensembl: {e}"
                )

        # get all the transcripts from the gene and remove those that are poorly supported
        # commenting out the transcript support level for now some genes don't have it defined which causes the program to halt
        # transcripts = filter(lambda t: t['Parent'] == ensemblID and t['feature_type'] == 'transcript' and t['transcript_support_level'] not in ['NA'], featureRequest.json())
        transcripts = filter(
            lambda t: t["Parent"] == self.ensemblID
            and t["feature_type"] == "transcript",
            featureRequest.json(),
        )

        if not transcripts and not self.suppressWarnings:
            returnError(
                "There were no valid protein-coding transcripts found for this gene in Ensembl"
            )

        # get the ids of the filtered transcripts
        validTranscripts = [t["transcript_id"] for t in transcripts]
        exons = filter(
            lambda e: e["feature_type"] == "exon" and e["Parent"] in validTranscripts,
            featureRequest.json(),
        )

        # stores relevant info from the exons
        completed = []
        validExons = []
        for e in exons:
            if e["id"] not in completed:
                validExons.append(
                    [
                        e["start"],
                        e["end"],
                        e["strand"],
                        e["ensembl_phase"],
                        e["ensembl_end_phase"],
                        e["exon_id"],
                    ]
                )
                completed.append(e["exon_id"])
        if not validExons and not self.suppressWarnings:
            returnError("There were no exons from the protein-coding transcripts found")

        return validExons

    def getSequenceAttributes(self):
        """
        Greg's code from FetchAPE.py with slight changes to error checking and variable names
        exons is an array with elements in the following order:
           0     1      2          3               4              5
        [start, end, strand, ensembl_phase, ensembl_end_phase, exon_id]
        """
        if self.sortedExons:
            strand = list(zip(*self.sortedExons))[2][0]
            self.sortedExons = sorted(
                self.sortedExons, key=lambda x: int(x[1])
            )  # sort based on end

            # find the earliest start and latest end sites for the exons
            seqStart = self.sortedExons[0][0]  # set to first exon's start/end
            seqEnd = self.sortedExons[0][1]
            for e in self.sortedExons:
                if e[0] < seqStart:
                    seqStart = e[0]
                if e[1] > seqEnd:
                    seqEnd = e[1]

            # pad with 1000bp buffer
            seqStart = seqStart - 1000
            seqEnd = seqEnd + 1000

            """
			since the seqStart and seqEnd are derived from the earliest/lastest protein-coding
			genes +/- a 1000bp buffer, the potential for the seqEnd or seqStart to be WITHIN
			the actual gene sequence (instead of outside of it) exists. Need to check if the
			calculated bounds are within the gene sequence and set the seqStart or seqEnd to
			be the actual gene's start or end.
			"""
            if strand == -1:
                if seqStart > self.gene_end:
                    seqStart = self.gene_end - 100
                if seqEnd < self.gene_start:
                    seqEnd = self.gene_start + 100
            elif strand == 1:
                if seqStart > self.gene_start:
                    seqStart = self.gene_start - 100
                if seqEnd < self.gene_end:
                    seqEnd = self.gene_end + 100
        else:
            # since no exons, need to set strand and sequence limits manually
            if self.gene_start < self.gene_end:
                # forward strand
                strand = 1
                seqStart = self.gene_start - 100
                seqEnd = self.gene_end + 100
            elif self.gene_start > self.gene_end:
                # on reverse strand
                strand = -1
                seqStart = self.gene_end - 100
                seqEnd = self.gene_start + 100
            else:
                returnError(
                    "No protein-coding exons found, unable to get strand from gene coordinates"
                )

        ext = f"/sequence/region/{self.Config.organismName}/{self.chromosome}:{seqStart}..{seqEnd}:{strand}?content-type=text/plain;mask=soft"
        try:
            seqRequest = requests.get(server + ext, timeout=30)
        except requests.exceptions.Timeout:
            returnError(f"The Ensembl Rest API is not responding ({server + ext})")
        except Exception:
            returnError("Problem with Ensembl Rest API call")
        if not seqRequest.ok:
            try:
                seqRequest.raise_for_status()
            except Exception as e:
                returnError(f"Problem fetching sequence from Ensembl: {e}")

        seq = seqRequest.text.strip()

        # remove weird text that appears sometimes
        if seq.startswith("chrmsmGRCm"):
            seq = seq.lstrip("chrmsmGRCm")

        # determine the length of the sequence
        seqLength = abs(seqStart - seqEnd)

        return seq, seqLength, seqStart, seqEnd, strand

    """
	Writes the text stored in the self.APE attribute to an APE file.
	File is labelled by GeneName_ReleaseNumber.ape
	If the boolean parameter printLink is set to true, an html link/download tag is also printed
	"""

    def writeAPE(self, printLink):
        try:
            filename = str(self.symbol + "_" + str(self.release) + ".ape")
            apeDir = os.path.join(self.APE_PATH, self.genome)
            apeDir_plain = os.path.join(apeDir, "plain")
            apeDir_features = os.path.join(apeDir, "features")
            # check if the genome ape file directory exists
            if not os.path.exists(apeDir):
                # create the folder and its subdirs
                os.makedirs(apeDir)
                os.makedirs(apeDir_plain)
                os.makedirs(apeDir_features)

            apeFile = open(os.path.join(apeDir_plain, filename), "w")
            apeFile.write("\n".join(self.APE))
            apeFile.close()
            # if the link to the download should be printed
            if printLink:
                print(
                    """<a class="downloadLink" id="initialDownload" href='"""
                    + apeDir_plain
                    + """/"""
                    + filename
                    + """' download>Download APE File for """
                    + filename
                    + """</a>"""
                )
        except Exception as e:
            returnError("Problem writing APE file " + str(e))


def returnError(errorString):
    print(f"""<p class="text-danger">Error: {errorString}</p>""")


def printError(errorString):
    print("Content-type: text/html\r\n\r")
    print(
        """
	<html>
	<head>
		<title>Error Fetching APE</title>
		<link rel="stylesheet" href="bootstrap-4.1.3/dist/css/bootstrap.min.css" as="style">
		<style>
		body {text-align: center;}
		a {font-size: 14px;}
		</style>
	</head>
	<body>
	</br>
	"""
    )
    returnError(errorString)
    sys.exit()


def returnWarning(warningString):
    print(f"""<p class="text-warning">Warning: {warningString}</p>""")
