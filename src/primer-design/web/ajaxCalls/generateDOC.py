#!/usr/bin/python3.7

import cgi
import os
import sys

from bson.objectid import ObjectId

# import external classes based on relative file location
dir_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(dir_path, "../../../helpers"))
from Config import Config

fileDir = os.path.join(dir_path, "../../files/docFiles")

STRAND = ""


def getGuides(ids, dbConnection):
    """
    Gets guides from Mongo database using list of guide record ids
    """
    guideCollection = dbConnection.guideCollection
    guideResults = []
    for curr_id in ids:
        guide = guideCollection.find_one({"_id": ObjectId(curr_id)})
        guideResults.append(guide)

    return guideResults


def findPrimers(ids, dbConnection):
    """
    Gets primers from Mongo database that have been designed with this specific
    set of guides
    """
    primerCollection = dbConnection.primerCollection
    primerResults = []
    primers = primerCollection.find(
        {"guides.ids": {"$size": len(ids), "$all": ids}, "status": "Accepted"}
    )
    for primer in primers:
        primerResults.append(primer)

    return primerResults


def setGeneStrand(ensid, dbConnection):
    global STRAND
    geneCollection = dbConnection.curr_geneCollection
    gene = geneCollection.find_one({"ENSID": str(ensid)})

    try:
        STRAND = gene["strand"]
    except Exception:
        print(f"Error, unable to get strand information for gene with ENSID: {ensid}")
        sys.exit()


def setupDocument():
    setupHTML = """
	<!DOCTYPE html>
	<html>
	<head>
		<title>Test</title>
	</head>
	<body>
	"""
    return setupHTML


def writeGuideTable(guideResults):
    tableHTML = """
	<table border="1" style="border-collapse: collapse; text-align: center;" color="#000000">
			<thead>
			<tr>
			<th style="font-family: 'Arial'; font-size: 10px; font-weight: bold; vertical-align: bottom;">gRNA</th>
			<th style="font-family: 'Arial'; font-size: 10px; font-weight: bold; vertical-align: bottom;">Sequence</th>
			<th style="font-family: 'Arial'; font-size: 10px; font-weight: bold; vertical-align: bottom;">Location (Strand)</th>
			<th style="font-family: 'Arial'; font-size: 10px; font-weight: bold; vertical-align: bottom;">Specificity Score</th>
			<th style="font-family: 'Arial'; font-size: 10px; font-weight: bold; vertical-align: bottom;">No. off-target sites<br>Total {0-1-2-3-4} mismatches</th>
			</tr>
			</thead>
			<tbody style="font-family: 'Arial'; font-size: 12px;">
	"""

    for guide in guideResults:
        # this isn't great... (older versions stored url encoded string of offtargets)
        offTargets = str(guide["otDesc"].encode("utf8")).split(
            "\xe2\x80\x89-\xe2\x80\x89"
        )
        if len(offTargets) > 1:
            sumOffTargets = sum([int(x) for x in offTargets])
        else:
            # not url encoded
            sumOffTargets = sum([int(x) for x in str(guide["otDesc"]).split("-")])
        formatOffTargets = str(sumOffTargets) + " {" + (" - ").join(offTargets) + "}"
        tableHTML += f"""
		<tr>
		<td>{guide['label']}</td>
		<td>{guide['guideSeq']}</td>
		<td>{guide['guideLocation']}</td> 
		<td>{guide['guideScore']}</td> 
		<td>{formatOffTargets}</td>"""

    tableHTML += """
	</tr></tbody></table>
	"""
    return tableHTML


def writePrimerTable(primerResults):
    tableHTML = """
	<br>
	<table border="1" style="border-collapse: collapse; text-align: center;" color="#000000">
		<thead>
		<tr>
		<th style="font-family: 'Arial'; font-size: 10px; font-weight: bold; vertical-align: bottom;" colspan="2">Type</th>
		<th style="font-family: 'Arial'; font-size: 10px; font-weight: bold; vertical-align: bottom;">Sequence</th>
		<th style="font-family: 'Arial'; font-size: 10px; font-weight: bold; vertical-align: bottom;">Length</th>
		<th style="font-family: 'Arial'; font-size: 10px; font-weight: bold; vertical-align: bottom;">T<sup>m</sup></th>
		<th style="font-family: 'Arial'; font-size: 10px; font-weight: bold; vertical-align: bottom;">Location (Strand)</th>
		<th style="font-family: 'Arial'; font-size: 10px; font-weight: bold; vertical-align: bottom;">Product Size</th>
		</tr>
		</thead>
		<tbody style="font-family: 'Arial'; font-size: 12px;">
	"""

    for primer in primerResults:
        leftTM = str(round(float(primer["leftTM"]), 1))
        rightTM = str(round(float(primer["rightTM"]), 1))
        chrm = str(primer["chr"])
        if STRAND == "+":
            leftLocation = int(primer["left_genomicLocation"])
            leftLocation = (
                chrm
                + ":"
                + str(leftLocation)
                + "-"
                + str(leftLocation + int(primer["leftlen"]))
                + "(+1)"
            )
            rightLocation = int(primer["right_genomicLocation"])
            rightLocation = (
                chrm
                + ":"
                + str(rightLocation)
                + "-"
                + str(rightLocation - int(primer["rightlen"]))
                + "(-1)"
            )
        elif STRAND == "-":
            leftLocation = int(primer["left_genomicLocation"])
            leftLocation = (
                chrm
                + ":"
                + str(leftLocation)
                + "-"
                + str(leftLocation - int(primer["leftlen"]))
                + "(-1)"
            )
            rightLocation = int(primer["right_genomicLocation"])
            rightLocation = (
                chrm
                + ":"
                + str(rightLocation)
                + "-"
                + str(rightLocation - int(primer["rightlen"]))
                + "(+1)"
            )
        else:
            print(f"Error: invalid strand for gene '{STRAND}'")
        tableHTML += f"""
		<tr>
		<td rowspan="2">{primer['type']}</td>
		<td>Forward</td>
		<td>{primer['leftprimer']}</td>
		<td>{primer['leftlen']}</td>
		<td>{leftTM}</td>
		<td>{leftLocation}</td>
		<td rowspan="2">{primer['productSize']}</td>
		</tr>
		<tr>
		<td>Reverse</td>
		<td>{primer['rightprimer']}</td>
		<td>{primer['rightlen']}</td>
		<td>{rightTM}</td>
		<td>{rightLocation}</td>
		</tr>
		"""

    tableHTML += """
	</tr></tbody></table>
	"""

    return tableHTML


def writeDOC(geneName, genome, ROOT_PATH, guideResults, primerResults):
    filename = str(geneName) + "_gRNAs-and-primers.doc"
    doc_genomeDir = os.path.join(ROOT_PATH, fileDir, genome)
    # check that the genome has a csv dir
    if not os.path.exists(doc_genomeDir):
        os.makedirs(doc_genomeDir)

    filepath = os.path.join(doc_genomeDir, filename)
    try:
        fileString = setupDocument()
        fileString += writeGuideTable(guideResults)
        fileString += writePrimerTable(primerResults)
        fileString += "</body></html>"  # closing tags
    except Exception as e:
        print(str(e))
    try:
        with open(filepath, mode="w") as docfile:
            docfile.write(fileString)
    except Exception as e:
        print(f"Error: {e}")

    return filename


def main():
    print("Content-type: text/html\n")
    args = cgi.FieldStorage()
    try:
        geneName = args.getvalue("gene")
        ensid = args.getvalue("ENSID")
        genome = args.getvalue("genome")
        ids = []  # to store the guide ids
        found_all = False
        count = str(0)
        # get all the guide ids passed via ajax
        while not found_all:
            if count in args:
                ids.append(args.getvalue(count))
                count = str(int(count) + 1)
            else:
                found_all = True
    except Exception as e:
        print(f"Problem with calls to script: {e}")

    if genome:
        try:
            # get connection to the genome's database
            dbConnection = Config(genome)
            setGeneStrand(ensid, dbConnection)
            guideResults = getGuides(ids, dbConnection)
            primerResults = findPrimers(ids, dbConnection)
            filename = writeDOC(
                geneName, genome, dbConnection.ROOT_PATH, guideResults, primerResults
            )
            print(os.path.join("../files/docFiles", genome, filename))
        except Exception as e:
            print(e)
    else:
        print("No genome passed to script")


if __name__ == "__main__":
    main()
