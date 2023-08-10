#!/usr/bin/env python3.7
"""
Functions for adding a guide to the mongo database and generating GFF files
based on the current database
"""
import cgi
import os
import re
import sys

# import cgitb
# cgitb.enable()

# import external classes based on relative file location
dir_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(dir_path)
from Config import Config

sys.path.append(os.path.join(dir_path, "../primer-design"))
from classes.BlastDB import BlastDB


def insertgRNAintoMongo(guideDict, gRNACollection):
    "This function inserts a gRNA record into MongoDB"

    insert_id = -1
    insert_id = gRNACollection.insert_one(guideDict).inserted_id
    if insert_id == -1:
        sys.exit("Cannot insert this record into database. Please contact CCM!")

    print("Successfully inserted this gRNA record into database.")
    return


def checkPAMinMongo(pamGenomicStart, pamSeq, gRNACollection):
    "This function checks to see if a particular gRNA record is already in MongoDB"

    # HILLARY: proposed change, modify so it looks for the guideSeq instead, other method allowed for duplicate guides (Arid5b)
    # return gRNACollection.find({"guideSeq" : guideSeq, "pamSeq": pamSeq}).count()
    return gRNACollection.find(
        {"pamGenomicStart": pamGenomicStart, "pamSeq": pamSeq}
    ).count()


def fetchNotesfromMongo(pamGenomicStart, pamSeq, gRNACollection):
    "This function fetches notes for a particular gRNA record from MongoDB"

    ResultObject = gRNACollection.find_one(
        {"pamGenomicStart": pamGenomicStart, "pamSeq": pamSeq}, {"Notes": 1}
    )
    print(ResultObject["Notes"])


def fetchLabelfromMongo(pamGenomicStart, pamSeq, gRNACollection):
    "This function fetches the label of a gRNA record from the MongoDB"

    ResultObject = gRNACollection.find_one(
        {"pamGenomicStart": pamGenomicStart, "pamSeq": pamSeq}, {"label": 1}
    )
    print(ResultObject["label"])


def updategRNAinMongo(guideDict, gRNACollection):
    "This function updates the record of a particular gRNA in MongoDB"
    # update label, notes, guideScore, and off targets (in case of change in scoring algorithm)
    updates = {
        "Notes": guideDict["Notes"],
        "label": guideDict["label"],
        "guideScore": guideDict["guideScore"],
        "otDesc": guideDict["otDesc"],
    }
    ResultObject = gRNACollection.update_one(
        {
            "pamGenomicStart": guideDict["pamGenomicStart"],
            "pamSeq": guideDict["pamSeq"],
        },
        {"$set": updates},
    )

    if ResultObject.modified_count != 1:
        sys.exit("Cannot update. Please contact CCM!")

    print("Successfully inserted/updated this gRNA record.")
    return


def noOptionFound():
    "This function is to alert the user that the action string in GET has an invalid value"
    print("Invalid string in GET request")


def getENSID(geneName, geneCollection):
    ENSID = ""
    # get the stable ensembl id from gene name
    ensResult = geneCollection.find_one({"Name": geneName}, {"ENSID": 1, "_id": 0})
    if ensResult is not None:
        ENSID = ensResult["ENSID"]

    return ENSID


def writePrimerGFF(dbConnection, org):
    idCounter = 1
    gffString = []

    primerCollection = dbConnection.primerCollection

    # create a line in the gff file for every pair of accepted primers in the database
    for primerRecord in primerCollection.find({"status": "Accepted"}):
        # see if the gene is + or -
        try:
            strand = Config.fetchStrandofGene(primerRecord["ENSID"], org)
        except ValueError:
            print(
                f"Skipping writing primer record associated with {primerRecord['batchName']} ({primerRecord['ENSID']}) as it cannot be found in the database"
            )
            continue

        if strand == "+":
            fwdStart = primerRecord["left_genomicLocation"]
            # subtract 1 from length to account for 'cap' jbrowse puts on exon features
            fwdEnd = str(int(fwdStart) + (int(primerRecord["leftlen"]) - 1))
            fwdStrand = "+"
            revEnd = primerRecord["right_genomicLocation"]
            revStart = str(int(revEnd) - (int(primerRecord["rightlen"]) - 1))
            revStrand = "-"
        elif strand == "-":
            fwdEnd = primerRecord["left_genomicLocation"]
            fwdStart = str(int(fwdEnd) - (int(primerRecord["leftlen"]) - 1))
            fwdStrand = "-"
            revStart = primerRecord["right_genomicLocation"]
            revEnd = str(int(revStart) + (int(primerRecord["rightlen"]) - 1))
            revStrand = "+"
        else:
            print(
                "Invalid strand property of '"
                + str(strand)
                + "' for gene '"
                + str(primerRecord["ENSID"])
                + "'"
            )

        # make the left/fwd primer's line first
        colNine = (
            "ID=exon_"
            + str(idCounter)
            + ";Name="
            + primerRecord["type"]
            + "_forward "
            + primerRecord["leftprimer"]
            + ";batchName="
            + primerRecord["batchName"]
        )
        colNine += (
            ";ensid="
            + primerRecord["ENSID"]
            + ";pair_notes="
            + primerRecord["notes"]
            + ";pair_id="
            + str(primerRecord["_id"])
        )
        colNine += (
            ";tm="
            + str(primerRecord["leftTM"])
            + ";gc="
            + str(primerRecord["leftGC"])
            + ";length="
            + str(primerRecord["leftlen"])
        )
        gffLine = "\t".join(
            [
                primerRecord["chr"],
                ".",
                "exon",
                str(fwdStart),
                str(fwdEnd),
                ".",
                fwdStrand,
                ".",
                colNine,
            ]
        )
        gffString.append(gffLine)
        idCounter += 1

        # now the right/rev primer line
        colNine = (
            "ID=exon_"
            + str(idCounter)
            + ";Name="
            + primerRecord["type"]
            + "_reverse "
            + primerRecord["rightprimer"]
            + ";batchName="
            + primerRecord["batchName"]
        )
        colNine += (
            ";ensid="
            + primerRecord["ENSID"]
            + ";pair_notes="
            + primerRecord["notes"]
            + ";pair_id="
            + str(primerRecord["_id"])
        )
        colNine += (
            ";tm="
            + str(primerRecord["rightTM"])
            + ";gc="
            + str(primerRecord["rightGC"])
            + ";length="
            + str(primerRecord["rightlen"])
        )
        gffLine = "\t".join(
            [
                primerRecord["chr"],
                ".",
                "exon",
                str(revStart),
                str(revEnd),
                ".",
                revStrand,
                ".",
                colNine,
            ]
        )
        gffString.append(gffLine)
        idCounter += 1

    try:
        primerGFF = os.path.join(
            dbConnection.ROOT_PATH, str("jbrowse/data/" + org + "/acceptedPrimers.gff")
        )
        gffFile = open(primerGFF, "w")
        gffFile.write("\n".join(gffString))
        gffFile.close()
    except Exception as e:
        print("Problem writing primer gff file: " + str(e))


def writeGuideGFF(dbConnection, org):
    # initialize the strings
    mRNAGFF3str = ""
    PAMGFF3str = ""
    guideGFF3str = ""
    mRNAIDCounter = 1

    gRNACollection = dbConnection.guideCollection

    for gRNARecord in gRNACollection.find({}):  # get all gRNA records from the database
        # mRNAstart = -1
        # mRNAend = -1
        # parse out elements of location
        chrom, guideCoordinates, strand = gRNARecord["guideLocation"].split(":")
        # sort the coordinates of the guide
        sortedGuideCoordinates = sorted([int(x) for x in guideCoordinates.split("-")])
        # calculate the pam coordinates
        if strand == "+":
            pamStart = sortedGuideCoordinates[-1]
            pamEnd = int(pamStart) + len(gRNARecord["pamSeq"])
            mRNAName = gRNARecord["guideSeq"] + ", " + gRNARecord["pamSeq"]
        elif strand == "-":
            pamEnd = sortedGuideCoordinates[0]
            pamStart = int(pamEnd) - len(gRNARecord["pamSeq"])
            mRNAName = gRNARecord["pamSeq"] + ", " + gRNARecord["guideSeq"]
        # sort all coordinates inclu. pam
        sortedCoordinates = list(sortedGuideCoordinates)
        sortedCoordinates.extend([pamStart, pamEnd])
        sortedCoordinates.sort()

        mRNAID = "mRNA" + "_" + str(mRNAIDCounter)
        mRNAIDCounter = mRNAIDCounter + 1

        if gRNARecord["guideScore"] == "" or int(gRNARecord["guideScore"]) == -1:
            gRNARecord["guideScore"] = "NA"

        otHits = re.findall(r"\d+", gRNARecord["otDesc"])
        gRNARecord["otDesc"] = "-".join(otHits)
        mRNAcolumn9 = (
            "ID="
            + mRNAID
            + ";Name="
            + mRNAName
            + ";guideScore="
            + gRNARecord["guideScore"]
            + ";otDesc="
            + gRNARecord["otDesc"]
        )
        if "label" in gRNARecord:
            mRNAcolumn9 += ";label=" + gRNARecord["label"]
        if "Notes" in gRNARecord:
            mRNAcolumn9 += ";Notes=" + gRNARecord["Notes"]
        if "batchName" in gRNARecord:
            mRNAcolumn9 += ";batchName=" + gRNARecord["batchName"]
        if "status" in gRNARecord:
            mRNAcolumn9 += ";status=" + gRNARecord["status"]
        if "ENSID" in gRNARecord:
            mRNAcolumn9 += ";ensid=" + gRNARecord["ENSID"]

        # the entire feature including arrow
        mRNAGFF3str += "\t".join(
            [
                chrom,
                ".",
                "mRNA",
                str(sortedCoordinates[0]),
                str(sortedCoordinates[-1]),
                ".",
                strand,
                ".",
                mRNAcolumn9,
            ]
        )
        mRNAGFF3str += "\n"

        # just the PAM feature
        PAMcolumn9 = (
            "ID="
            + chrom
            + ":"
            + str(gRNARecord["pamGenomicStart"])
            + "_"
            + gRNARecord["pamSeq"]
            + ";Name="
            + gRNARecord["pamSeq"]
            + ";Parent="
            + mRNAID
        )
        PAMGFF3str += "\t".join(
            [
                chrom,
                ".",
                "three_prime_UTR",
                str(pamStart),
                str(pamEnd),
                ".",
                strand,
                "-1",
                PAMcolumn9,
            ]
        )
        PAMGFF3str += "\n"

        # the coloured part of the guide feature (not PAM)
        gRNAcolumn9 = (
            "ID="
            + chrom
            + ":"
            + str(sortedGuideCoordinates[0])
            + "_"
            + gRNARecord["guideSeq"]
            + ";Name="
            + gRNARecord["guideSeq"]
            + ";Parent="
            + mRNAID
        )
        guideGFF3str += "\t".join(
            [
                chrom,
                ".",
                "CDS",
                str(sortedGuideCoordinates[0]),
                str(sortedGuideCoordinates[1]),
                ".",
                strand,
                "0",
                gRNAcolumn9,
            ]
        )
        guideGFF3str += "\n"

    try:
        guideGFF = os.path.join(
            dbConnection.ROOT_PATH, str("jbrowse/data/" + org + "/gRNA_CRISPR.gff")
        )
        gffFile = open(guideGFF, "w")
        gffFile.write(mRNAGFF3str)
        gffFile.write(PAMGFF3str)
        gffFile.write(guideGFF3str)
        gffFile.close()
    except Exception as e:
        print("Problem writing guide gff file: " + str(e))


def modifyDatabase(action, guideDict, geneCollection, gRNACollection):
    # to get the chromosomal location of guideStart and pamStart, we need to add the pamStart variable to the start of inputSearchCoordinates
    genomicSearchStart = -1

    if "inputSearchCoordinates" in guideDict:
        genomicMatchObj = re.match(
            r"^(.+?:(\d+))\-\d+", guideDict["inputSearchCoordinates"]
        )
        guideDict["chromSearchStart"] = genomicMatchObj.group(1)  # ex: chr10:12345
        genomicSearchStart = int(genomicMatchObj.group(2))
    else:
        sys.exit(
            "Error! Input genomic coordinates werent captured. Please contact CCM!"
        )

    if genomicSearchStart == -1:
        sys.exit(
            "Error! Input genomic coordinates are not in the correct format. Please contact CCM!"
        )

    # +1 because search assumes '0' based coordinates for input
    guideDict["pamGenomicStart"] = genomicSearchStart + int(guideDict["pamStart"]) + 1
    if "guideStart" in guideDict:
        guideDict["guideGenomicStart"] = (
            genomicSearchStart + int(guideDict["guideStart"]) + 1
        )

    if action == "insert":
        # get the stable ENSID based on the gene name (batchName)
        guideDict["ENSID"] = getENSID(guideDict["batchName"], geneCollection)

        if (
            checkPAMinMongo(
                guideDict["pamGenomicStart"], guideDict["pamSeq"], gRNACollection
            )
            == 0
        ):
            # if a PAM sequence doesnt exist at a particular genomic location
            insertgRNAintoMongo(guideDict, gRNACollection)
        else:
            updategRNAinMongo(guideDict, gRNACollection)
    elif action == "fetch":
        if (
            checkPAMinMongo(
                guideDict["pamGenomicStart"], guideDict["pamSeq"], gRNACollection
            )
            != 0
        ):
            fetchNotesfromMongo(
                guideDict["pamGenomicStart"], guideDict["pamSeq"], gRNACollection
            )
    elif action == "fetchLabel":
        if (
            checkPAMinMongo(
                guideDict["pamGenomicStart"], guideDict["pamSeq"], gRNACollection
            )
            != 0
        ):
            fetchLabelfromMongo(
                guideDict["pamGenomicStart"], guideDict["pamSeq"], gRNACollection
            )
    else:
        noOptionFound()


def writeGFF(org):
    # connect to the organism's db
    dbConnection = Config(org)
    # gRNACollection = dbConnection.guideCollection
    # primerCollection = dbConnection.primerCollection
    # rewrite the GFF files
    writePrimerGFF(dbConnection, org)
    writeGuideGFF(dbConnection, org)


def addGenomicLocation(org, guideDict):
    # get the location from blast using the gRNA sequence (and PAM)
    guideSeq = guideDict["guideSeq"]
    pamSeq = guideDict["pamSeq"]

    # THIS IS A TEMPORARY FIX FOR CPF1 (PAM before guide)
    if pamSeq[:3] == "TTT":
        searchSeq = pamSeq + guideSeq
    else:
        searchSeq = guideSeq + pamSeq

    seqSearch = BlastDB(
        org, searchSeq, True
    )  # true indicates that the matches should be identical only
    hits = seqSearch.returnLocations()
    if len(hits) > 1:
        sys.exit(
            "Guide sequence "
            + str(searchSeq)
            + " has "
            + str(len(hits))
            + " identical matches in the genome"
        )
    if len(hits) < 1:
        sys.exit("Guide sequence " + str(searchSeq) + " has 0 matches in the genome")
    else:
        try:
            # check to make sure there's only only location for the identical hit
            if len(hits) == 1:
                # get the location
                location = hits[0][1]
            else:
                print("Unable to definitively place gRNA")
                sys.exit()
        except Exception:
            print(
                "BLAST search for sequence "
                + str(searchSeq)
                + " did not return a location"
            )
            sys.exit()

        # parse out the chrom, coordinates, and strand of match
        chrom, coord, strand = location.split(":")
        # separate the PAM and gRNA locations
        if strand == "+":
            start, end = coord.split("-")
            guideEnd = int(end) - len(pamSeq)
            pamStart = guideEnd + 1
        elif strand == "-":
            start, end = coord.split("-")
            guideEnd = int(end) + len(pamSeq)
            pamStart = guideEnd - 1
        # reconstruct
        guideLocation = chrom + ":" + str(start) + "-" + str(guideEnd) + ":" + strand
        pamLocation = chrom + ":" + str(pamStart) + "-" + str(end) + ":" + strand
        # guideGenomicStart = start
        pamGenomicStart = pamStart  # old code relies on this

    # record in dict
    guideDict["guideLocation"] = guideLocation
    guideDict["pamLocation"] = pamLocation
    guideDict["pamGenomicStart"] = pamGenomicStart

    return


def main():
    """
    Determines if the script is being called from a web browser or command line.
    If from the web browser, updates the database according to values passed in the
    cgi arguments. If from the command line, no changes are made to the database
    but the primer and guide GFF files are rewritten. This is useful for when an
    entry in the database is manually changed (i.e. via interacting with the
    mongo shell) but the changes aren't reflected in the tracks on JBrowse since
    no GFF rewrite was performed.
    """
    try:
        # determine if running from web or commandline
        ajaxForm = cgi.FieldStorage()
        cgi_arguments = ajaxForm.getvalue("inputData").split(",")
        # if we get here we're running from a web browser
        print("Content-type:text/plain\n")
        try:
            guideDict = {}  # store the guide attributes
            for arg in cgi_arguments:
                tmpKey, tmpValue = arg.split(
                    ":", 1
                )  # the cgi arguments are in json format
                guideDict[tmpKey] = tmpValue

            # sample guide dict during insert (for debugging)
            """
			guideDict = {'batchName': 'Aasdh',
			'status': 'Accepted',
			'oof': '62',
			'guideScore': '84',
			'guideSeq': 'GTAACTGAGCAATTAGATCC',
			'Notes': 'Test%20BLAST%20search%20April%209th',
			'inputSearchCoordinates': 'chr5:76896027-76896237:+',
			'pamSeq': 'AGG',
			'label': 'test_Aasdh_D',
			'guideStart': '111',
			'org': 'mm10',
			'pamId': 's108-',
			'otDesc': '0\xe2\x80\x89-\xe2\x80\x890\xe2\x80\x89-\xe2\x80\x890\xe2\x80\x89-\xe2\x80\x895\xe2\x80\x89-\xe2\x80\x89107',
			'crisprScan': '33',
			'pamStart': '108',
			'fusi': '53'}
			"""
            action = ajaxForm.getvalue("action")  # insert, fetch or update

            # based on the org in the ajax form, connect to the right database via the Config class
            org = guideDict["org"]
            dbConnection = Config(org)
            gRNACollection = dbConnection.guideCollection
            geneCollection = dbConnection.curr_geneCollection
            # primerCollection = dbConnection.primerCollection

            if action == "insert":
                # when adding a gRNA, several fields are required. Ensure they are defined
                essentialFields = [
                    "inputSearchCoordinates",
                    "pamStart",
                    "pamSeq",
                    "guideSeq",
                    "org",
                    "batchName",
                ]
                for field in essentialFields:
                    if field not in guideDict:
                        print(
                            "Field "
                            + str(field)
                            + " doesn't exist in the request. Aborting!"
                        )
                        return
                # add the genomic coordinates for PAM and guide via blast
                addGenomicLocation(org, guideDict)

            # modify the database based on the action passed and guide info
            modifyDatabase(action, guideDict, geneCollection, gRNACollection)
            # after database changes, rewrite GFF
            writeGFF(org)

            return

        except Exception as e:
            print("Error occurred while updating database: " + str(e))

    except AttributeError:
        # no cgi arguments, will see if command-line arguments exist
        try:
            cli_arguments = sys.argv  # list of script and its arguments
            if len(cli_arguments) > 2:
                print(
                    "Unexpected number of arguments, only the organism code (i.e. mm10) should be passed"
                )
                return
            elif len(cli_arguments) == 1:
                print(
                    "To rewrite the gff files, provide the organism name (i.e. mm10) to the script"
                )
                return
            else:
                org = cli_arguments[1]
                print(
                    "Will attempt to rewrite primer and guide GFF files for " + str(org)
                )
                writeGFF(org)
                print("GFF files rewritten")
                return
        except IOError:
            print(
                "Unable to write GFF files. The script may need to be run with sudo privileges"
            )
            return
    return


if __name__ == "__main__":
    main()
