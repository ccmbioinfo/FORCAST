#!/usr/bin/env python3.7

import cgi
import os
import sys
from urllib.parse import unquote

from bson.objectid import ObjectId

# import external classes based on relative file location
dir_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(dir_path, "../../../helpers"))
from Config import Config


def getMongoRecord(ensid, dbConnection):
    primerCollection = dbConnection.primerCollection
    primerResult = primerCollection.find({"ENSID": ensid})
    return primerResult


# get label for guide from mongo
def getGuideLabel(guideID, dbConnection):
    guideCollection = dbConnection.guideCollection
    guideResult = guideCollection.find_one({"_id": ObjectId(guideID)})

    try:
        # store the seq, always
        label = [(str(guideResult["guideSeq"]))]
        # also, if it has a label, store it
        if "label" in guideResult and guideResult["label"] != "":
            decodedLabel = unquote(guideResult["label"])
            label.append(str(decodedLabel))
    except Exception:
        # the guide the primer was designed with was not found
        return ["*Guide Used in Design was Deleted*"]

    return label


def organizePrimers(primers, dbConnection):
    primerDict = {}
    for primer in primers:
        guideLabels = []
        missing = False  # track if there's a missing label
        for guideID in primer["guides"]["ids"]:
            label = getGuideLabel(guideID, dbConnection)
            if len(label) < 2:
                missing = True
            guideLabels.append(getGuideLabel(guideID, dbConnection))

        # if none were missing, construct the identifying string from the labels
        if not missing:
            """
            sort the guides alphabetically by their labels.
            otherwise primers with the same guides stored in a different
            order won't be grouped together. Ideally we would sort by
            the order of the guides on the gene (taking into account whether
            its on the forward strand or not). For now though, reverse alphabetical
            works since the typical labels (U, D, M etc.) happen to be in reverse
            alphabetical with how they are on the gene. If non-standard names
            were used though they wouldn't necessarily appear in order (TODO)
            """
            guideLabels = sorted(guideLabels, key=lambda x: x[1], reverse=True)
            guidesKey = ", ".join(i[1] for i in guideLabels)
            # add to dict if not there already
            if guidesKey not in primerDict:
                primerDict[guidesKey] = []
            primerDict[guidesKey].append(primer)  # store with guideKey
        else:
            # TODO: sort these by gene order as well. alphabetically for now
            guideLabels = sorted(guideLabels, key=lambda x: x[0])
            # at least one guide didn't have a label, create identifer from seq
            guidesKey = ", ".join(i[0] for i in guideLabels)
            if guidesKey not in primerDict:
                primerDict[guidesKey] = []
            primerDict[guidesKey].append(primer)

    return primerDict


def printRow(primerResult):
    rowID = primerResult["_id"]
    primerType = primerResult["type"]
    forwardPrimer = primerResult["leftprimer"]
    forwardDetails = "Length: " + primerResult["leftlen"]
    forwardDetails += " GC%: " + str(round(float(primerResult["leftGC"]), 1))
    forwardDetails += " T<sup>m</sup>: " + str(round(float(primerResult["leftTM"]), 1))
    productSize = primerResult["productSize"]
    primerStatus = primerResult["status"]
    if primerStatus == "Accepted":
        dropdownClass = "btn accepted-dropdown dropdown-toggle"
        statusOption = "Reject"
        # checkFlag = 'checked="checked"'
    else:
        dropdownClass = "btn rejected-dropdown dropdown-toggle"
        statusOption = "Accept"
        # checkFlag = ''
    decodedNotes = unquote(primerResult["notes"])
    reversePrimer = primerResult["rightprimer"]
    reverseDetails = "Length: " + primerResult["rightlen"]
    reverseDetails += " GC%: " + str(round(float(primerResult["rightGC"]), 1))
    reverseDetails += " T<sup>m</sup>: " + str(round(float(primerResult["rightTM"]), 1))
    print(
        f"""<tr id="{rowID}">
		<td rowspan="2" class="align-middle centreCell">{primerType}</td>
		<td class="align-middle centreCell">Forward</td>
		<td nowrap class="align-middle centreCell">{forwardPrimer}</td>
		<td nowrap class="centreCell" style="font-size: 0.9rem;">{forwardDetails}</td>
		<td rowspan="2" class="align-middle centreCell">{productSize}</td>
		<td rowspan="2" class="align-middle centreCell">
			<div class="dropdown">
				<button type="button" class="{dropdownClass}" data-toggle="dropdown">
					{primerStatus}
				</button>
				<div class="dropdown-menu">
					<a class="dropdown-item" onclick="updatePrimerStatus(this);">{statusOption}</a>
				</div>
			</div>
		</td>
		<td rowspan="2" style="padding: 0px;">
			<textarea class="primerNotes" style="border:none; width: 100%; height:85px; padding: 0px;">{decodedNotes}</textarea>
		</td>
		</tr>
		<tr>
		<td class="align-middle centreCell">Reverse</td>
		<td nowrap class="align-middle centreCell">{reversePrimer}</td>
		<td nowrap class="centreCell" style="font-size: 0.9rem;">{reverseDetails}</td>
		</tr>"""
    )


def printPrimers(primers, geneName, dbConnection):
    print("Content-Type: text/html\n")
    if primers.count() == 0:
        print("<p>No saved primers for " + str(geneName) + ".</p>")
        return

    """
	Want to print the primers grouped by the guides they were designed for.
	To acheive this, create a dict where the key is the string used to 
	describe the guides. If they all have labels, then use them. Otherwise,
	use the Guide Sequence.
	"""
    primerDict = organizePrimers(primers, dbConnection)

    for guideLabel, primerList in primerDict.items():
        print(
            f"""
		<p style="float: left; font-weight: bold">For Guides: {guideLabel}</p>
		<table class="table table-bordered">
			<thead>
			<tr id="headingRow">
			<th class="centreCell" colspan="2">Type</th>
			<th class="centreCell" scope="col">Sequence</th>
			<th class="centreCell" scope="col">Details</th>
			<th class="centreCell" scope="col">Product Size</th>
			<th class="centreCell" scope="col">Status</th>
			<th class="centreCell" scope="col">Notes</th>
			</thead>
			<tbody>
		"""
        )

        for primerResult in primerList:
            printRow(primerResult)

        print("""</tbody></table>""")

    print(
        """
	<button class="btn btn-primary btn-sm bordered-button" style="float:right;" title="Update notes of all primers" type="button" onclick="updatePrimerNotes()">
	<i class="fa fa-spinner fa-spin" id="updateNotesSpinner"></i>
	Update Notes
	</button>	
	<br>
	"""
    )


def main():
    args = cgi.FieldStorage()

    try:
        geneName = args.getvalue("gene")
        ensid = args.getvalue("ensid")
        genome = args.getvalue("genome")
    except Exception as e:
        print(f"Error: {e}")
        return

    if geneName and ensid and genome:
        try:
            dbConnection = Config(genome)
            primers = getMongoRecord(ensid, dbConnection)
            printPrimers(primers, geneName, dbConnection)
        except Exception as e:
            print(e)
    else:
        print("Missing values passed to script")


if __name__ == "__main__":
    main()
