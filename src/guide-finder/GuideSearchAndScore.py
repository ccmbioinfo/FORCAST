#!/usr/bin/env python3.7

"""
Hillary Elrick, September 16th, 2019

Class for searching and evaluating guides then formatting the results
Requires: input region, genome, rgen, and gene

Steps:
1) Gets the sequence within the search location (get_sequence.py)
2) Finds the gRNAs within the sequence (find_grna.py)
3) Finds and counts all the off-targets in the genome for each guide (find_offtargets.py)
4) Scores the off-targets and calculates an aggregate score for each guide (score_offtargets.py)
5) Categorizes each off-target into 'intergenic', 'intronic', and 'exonic'
6) Puts the results into a jinja2 template and prints the html
"""

import argparse
import binascii
import cgi
import csv
import datetime
import json
import logging
import os
import sys
import tempfile
import time
import urllib.parse
from collections import OrderedDict

from jinja2 import Template

# import external classes based on relative file location
dir_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(dir_path, "../helpers"))
from Config import Config

sys.path.append(os.path.join(dir_path, "core"))
import categorize_offtargets
import find_grna
import find_offtargets
import get_sequence
import score_offtargets

today = datetime.date.today()
log_filename = (
    f"/var/log/FORCAST/GuideSearchAndScore/{today.year}/{today:%m}/{today:%d}.log"
)
log_file_dir = os.path.dirname(log_filename)

if not os.path.exists(log_file_dir):
    os.makedirs(log_file_dir)

logging.basicConfig(
    filename=log_filename,
    level=logging.DEBUG,
)


class GuideSearchAndScore:
    def __init__(self, **kwargs):
        """class for controlling the guide searching workflow and displaying results"""
        # track whether web or cli
        self.cli = kwargs["command-line"]
        if self.cli:
            self.output_file = kwargs["output"]
        else:
            # for debugging:
            import cgitb

            cgitb.enable()

        # validate searchInput
        if "searchInput" not in kwargs:
            self.sendError("'searchInput' parameter not set")
        else:
            self.isValidInput(kwargs["searchInput"])
            self.searchInput = kwargs["searchInput"]

        # validate genome
        if "genome" not in kwargs:
            self.sendError("'genome' parameter not set")
        else:
            # attempt connection to genome's db before storing
            self.dbConnection = Config(kwargs["genome"])
            self.genome = kwargs["genome"]

        # check gene sent
        if "gene" not in kwargs:
            self.sendError("Please select a Target from the dropdown list")
        else:
            self.gene = kwargs["gene"]

        # validate rgenID
        if "rgenID" not in kwargs:
            self.sendError("Please select an RGEN from the dropdown list")
        else:
            self.rgenID = kwargs["rgenID"]
            try:
                self.rgenRecord = self.getRGEN()
            except ValueError:
                self.sendError(f"Invalid RGEN ID, {self.rgenID}")

        # check guideLength sent
        if "guideLength" not in kwargs:
            self.sendError("Please select a Protospacer Length from the dropdown list")
        else:
            self.guideLength = kwargs["guideLength"]

        # check maxOffTargets sent
        if "maxOffTargets" not in kwargs:
            self.sendError("Max off targets is not set")
        else:
            self.maxOffTargets = kwargs["maxOffTargets"]

        # TODO: implement
        if "offtargetPAMS" in kwargs:
            self.offTargetPAMS = kwargs["offtargetPAMS"]

        time_0 = time.time()
        logging.debug("[STARTED]\t\tPerforming guide searches...")
        self.guideDict, self.batchID = self.performGuideSearch()

        time_1 = time.time()
        logging.debug(
            f"[FINISHED]\t\tPerformed guide searches in {str(round(time_1-time_0,4))}s"
        )

        time_2 = time.time()
        logging.debug("[STARTED]\t\tSetting scores...")

        self.scores = self.setScores()

        time_3 = time.time()
        logging.debug(f"[FINISHED]\t\tSet scores in {str(round(time_3-time_2,4))}s")

        if len(self.guideDict.keys()) > 0:
            time_4 = time.time()
            logging.debug("[STARTED]\t\tWriting CSV files...")

            self.writeCsvFiles()

            time_5 = time.time()
            logging.debug(
                f"[FINISHED]\t\tWrote CSV files in {str(round(time_5-time_4,4))}s"
            )

            if not self.cli:
                time_6 = time.time()
                logging.debug("[STARTED]\t\tWriting JSON file...")

                self.writeJsonFile()

                time_7 = time.time()
                logging.debug(
                    f"[FINISHED]\t\tWrote JSON file in {str(round(time_7-time_6,4))}s"
                )

                time_8 = time.time()
                logging.debug("[STARTED]\t\tSending result HTML...")

                self.sendResultHTML()

                time_9 = time.time()
                logging.debug(
                    f"[FINISHED]\t\tSent result HTML in {str(round(time_9-time_8,4))}s"
                )
        else:
            if not self.cli:
                time_8 = time.time()
                logging.debug("[STARTED]\t\tSending no result HTML...")

                self.sendNoResultHTML()

                time_9 = time.time()
                logging.debug(
                    f"[FINISHED]\t\tSent no result HTML in {str(round(time_9-time_8,4))}s"
                )
            else:
                print("No guides found in input region")
        logging.debug(f"TOTAL TIME ELAPSED: {round(time_9-time_0,4)}s\n\n")

    def setScores(self):
        # scores = set({}) # make a set
        options = ["MIT", "CFD", "Precision", "Frameshift Frequency", "MH Strength"]
        available = []
        for key, guide in self.guideDict.items():
            for s in options:
                if s in guide and s not in available:
                    available.append(s)
            if len(available) == len(options):
                break

        return available

    def renderTemplate(self, template_name, template_values):
        """given the name of the template, goes to the templates folder, renders it, and returns the result"""
        template_path = os.path.join(
            self.dbConnection.ROOT_PATH,
            "src/guide-finder/jinja2-templates/{template_name}".format(
                template_name=template_name
            ),
        )
        template = Template(open(template_path, "rb").read().decode("utf-8"))
        html_result = template.render(template_values)
        return html_result

    def guideTableHTML(self):
        """format the guide dictionary into an HTML table"""
        template_values = {
            "guides": self.guideDict,
            "table_heading": self.tableHeadingHTML(),
            "table_body": self.tableBodyHTML(),
        }
        return self.renderTemplate("guide_table.html", template_values)

    def tableHeadingHTML(self):
        """determine which info for the guides is available and display the headings for those"""

        scoreHeading = ""
        scoreHeaders = ""
        if len(self.scores) > 0:
            scoreHeading += "<th colspan='{num_scores}'>Scoring</th>".format(
                num_scores=len(self.scores)
            )
            for score in self.scores:
                scoreHeaders += "<th>{score}</th>".format(score=score)

        template_values = {"score_heading": scoreHeading, "score_headers": scoreHeaders}

        return self.renderTemplate("table_heading.html", template_values)

    def tableBodyHTML(self):
        """generate HTML row containing info for each potential guide"""

        # generate OrderedDict
        if "MIT" in self.scores:
            sortedIDs = sorted(
                self.guideDict.keys(),
                key=lambda x: (int(self.guideDict[x]["MIT"])),
                reverse=True,
            )
        else:
            # sort by weighted off-target counts
            sortedIDs = sorted(
                self.guideDict.keys(), key=lambda x: (self.guideDict[x]["Rank"])
            )

        sortedGuides = OrderedDict((x, self.guideDict[x]) for x in sortedIDs)
        bodyHTML = "<tbody>" + self.tableRowsHTML(sortedGuides) + "</tbody>"

        return bodyHTML

    def tableRowsHTML(self, sortedGuides):
        """for each guide, generate the HTML for its row"""

        rowsHTML = ""

        for guideID, guide in sortedGuides.items():
            template_values = {
                "guideID": guideID,
                "guide": guide,
                "inDatabase": self.guideExistsInDatabase(guideID),
                "guideSeq": self.formatSequence(guide["guide_seq"], guide["pam_seq"]),
                "guideLocation": self.calculateLocation(guide),
                "offtargetModal": self.offtargetHTML(guideID, guide),
                "rowPopover": self.rowPopoverHTML(guideID),
            }
            rowsHTML += self.renderTemplate("table_row.html", template_values)

        return rowsHTML

    def rowPopoverHTML(self, guideID):
        """given a guideID fetch the label and notes if it's already in the database, give the option to add it otherwise"""

        button_text, label, notes = self.fetchGuideFromDatabase(guideID)

        template_values = {
            "batch_guideID": str(self.batchID + "_" + guideID),
            "buttonText": button_text,
            "defaultLabel": urllib.parse.unquote(label),
            "defaultNotes": urllib.parse.unquote(notes),
        }
        return self.renderTemplate("row_popover.html", template_values)

    def fetchGuideFromDatabase(self, guideID):
        """determine whether the given guide is in the database, return its label and notes, plus a descriptor of the available action"""
        searchQuery = {
            "guideSeq": self.guideDict[guideID]["guide_seq"],
            "pamSeq": self.guideDict[guideID]["pam_seq"],
            "guideLocation": self.calculateLocation(self.guideDict[guideID]),
        }
        if self.dbConnection.guideCollection.count_documents(searchQuery) > 0:
            existingGuide = self.dbConnection.guideCollection.find_one(
                searchQuery, {"label": 1, "Notes": 1}
            )
            return "Update Guide", existingGuide["label"], existingGuide["Notes"]
        else:
            return "Add to Database", "", ""

    def guideExistsInDatabase(self, guideID):
        """return true if the guide is already stored, false otherwise"""
        searchQuery = {
            "guideSeq": self.guideDict[guideID]["guide_seq"],
            "pamSeq": self.guideDict[guideID]["pam_seq"],
            "guideLocation": self.calculateLocation(self.guideDict[guideID]),
        }
        if self.dbConnection.guideCollection.count_documents(searchQuery) > 0:
            return True
        else:
            return False

    def formatSequence(self, guide_seq, pam_seq):
        """uses the rgen record to determine which order to display the pam and sequence in"""
        if self.rgenRecord["PamLocation"] == "downstream":
            return guide_seq + ", " + pam_seq
        elif self.rgenRecord["PamLocation"] == "upstream":
            return pam_seq + ", " + guide_seq
        else:
            self.sendError(
                "Unrecognized PAM Location for RGEN: "
                + str(self.rgenRecord["PamLocation"])
            )

    def calculateLocation(self, guide):
        """using the strand of the guide and the genomic start, format the location string"""
        if guide["strand"] == "+":
            return (
                guide["pam_chrom"]
                + ":"
                + str(guide["guide_genomic_start"])
                + "-"
                + str(int(guide["guide_genomic_start"] + len(guide["guide_seq"])) - 1)
                + ":+"
            )
        elif guide["strand"] == "-":
            return (
                guide["pam_chrom"]
                + ":"
                + str(guide["guide_genomic_start"])
                + "-"
                + str(int(guide["guide_genomic_start"] - len(guide["guide_seq"])) + 1)
                + ":-"
            )
        else:
            self.sendError("Unrecognized strand for guide: " + str(guide["strand"]))

    def offtargetHTML(self, guideID, guide):
        """creates the HTML for the off-target modal of a given guide"""
        classNameGuideID = guideID.replace("+", "plus").replace("-", "minus")
        template_values = {
            "guideID": guideID,
            "guide": guide,
            "offtargetCounts": self.offtargetCountsHTML(classNameGuideID, guide),
            "offtargetModals": self.offtargetModalHTML(classNameGuideID, guide),
            "csvFile": f"/download/{self.batchID}_{guideID}.csv",
            "totalCount": str(sum(guide["offtarget_counts"])),
        }
        return self.renderTemplate("offtarget_cell.html", template_values)

    def offtargetCountsHTML(self, guideID, guide):
        """formats the links to the off-target modals"""
        off_target_counts = "<div style='color: #2676ff; font-weight: bold'>"
        for num_mismatches, num_offtargets in enumerate(guide["offtarget_counts"]):
            off_target_counts += "<button class='btn btn-link no-padding' data-toggle='modal' data-target='#mismatch_{guideID}_{num_mismatches}'>{num_offtargets}</button>-".format(
                **locals()
            )
        off_target_counts = off_target_counts[:-1]  # remove trailing dash
        off_target_counts += "</div>"

        return off_target_counts

    def offtargetModalHTML(self, guideID, guide):
        """format the modals for the off-targets"""
        modalsHTML = ""
        for num_mismatches, num_offtargets in enumerate(guide["offtarget_counts"]):
            template_values = {
                "guideID": guideID,
                "guide": guide,
                "mismatches": num_mismatches,
                "guideSeq": self.formatSequence(guide["guide_seq"], guide["pam_seq"]),
                "offTargetBody": self.offtargetModalBodyHTML(guide, num_mismatches),
                "numOffTargets": len(self.subsetOffTargets(guide, num_mismatches)),
            }
            modalsHTML += self.renderTemplate("offtarget_modal.html", template_values)

        return modalsHTML

    def subsetOffTargets(self, guide, num_mismatches):
        """returns the list of off-targets with the given number of mismatches"""
        offtarget_subset = list(
            filter(
                lambda x: int(countLower(x["seq"])) == int(num_mismatches),
                guide["offtargets"],
            )
        )
        return offtarget_subset

    def offtargetModalBodyHTML(self, guide, num_mismatches):
        """format and print the table for the given number of off-targets"""
        # get only the off-targets with the selected number of mismatches
        offtarget_subset = self.subsetOffTargets(guide, num_mismatches)
        if len(offtarget_subset) > 0:
            # num_offtargets = len(offtarget_subset)
            maxShown = 20
            standard_offtargets, none_in_seed = self.separateOffTargets(
                offtarget_subset
            )
            resultHTML = ""
            if len(none_in_seed) > 0:
                resultHTML += "<p class='tableTitle left'><b>{count}</b> With No Mismatches in Seed:</p>".format(
                    count=len(none_in_seed)
                )
                resultHTML += self.offTargetTableHTML(none_in_seed, maxShown)
                if len(standard_offtargets) > 0:
                    resultHTML += "<p class='tableTitle left'><b>{count}</b> With Mismatches in Seed:</p>".format(
                        count=str(len(standard_offtargets))
                    )
                    resultHTML += self.offTargetTableHTML(standard_offtargets, maxShown)
            else:
                resultHTML += "<p class='tableTitle left'><b>{count}</b> With Mismatches in Seed:</p>".format(
                    count=str(len(standard_offtargets))
                )
                resultHTML += self.offTargetTableHTML(standard_offtargets, maxShown)

            return resultHTML
        else:
            return "<p>No Off-Targets with {mismatches} Mismatches</p>".format(
                mismatches=str(num_mismatches)
            )

    def offTargetTableHTML(self, offtarget_list, maxShown):
        """sorts, formats and returns a table of off-targets from the offtarget list provided"""

        num_offtargets = len(offtarget_list)
        offtarget_list = offtarget_list[:maxShown]

        for offtarget in offtarget_list:
            offtarget.update(
                {
                    "formatted_seq": self.colourLowercaseRed(
                        self.formatSequence(offtarget["seq"], offtarget["pam"])
                    )
                }
            )
        # sort by score if available
        if "MIT" in self.scores and "MIT" in offtarget_list[0]:  # in case max_exceeded
            offtarget_list = sorted(
                offtarget_list, key=lambda x: x["MIT"], reverse=True
            )
        elif "CFD" in self.scores and "CFD" in offtarget_list[0]:
            offtarget_list = sorted(
                offtarget_list, key=lambda x: x["CFD"], reverse=True
            )

        total_count = ""
        if num_offtargets > maxShown:
            total_count = "<p>({max} of {total} shown)</p>".format(
                max=str(maxShown), total=str(num_offtargets)
            )

        template_values = {"offtargetSubset": offtarget_list, "totalCount": total_count}

        return self.renderTemplate("offtarget_table.html", template_values)

    def separateOffTargets(self, off_target_subset):
        """given a list of filtered off-targets, separate the regular ones from those that have no mismatches in the rgen's seed region"""
        seedDirection = self.rgenRecord["SeedRegion"][0]
        seedLength = int(self.rgenRecord["SeedRegion"][1:])
        guideLength = len(off_target_subset[0]["seq"])
        standard_offtargets = []
        none_in_seed = []
        for offtarget in off_target_subset:
            if self.hasMismatchInSeed(
                offtarget["seq"], seedDirection, seedLength, guideLength
            ):
                standard_offtargets.append(offtarget)
            else:
                none_in_seed.append(offtarget)

        return standard_offtargets, none_in_seed

    def hasMismatchInSeed(self, offtargetSeq, seedDirection, seedLength, guideLength):
        """given an offtarget's guide sequence, returns true if there is a mismatch in the seed region of the rgen and false otherwise"""
        if seedDirection == "+":
            for idx in range(0, seedLength):
                if offtargetSeq[idx].islower():
                    return True
        elif seedDirection == "-":
            for idx in reversed(range(guideLength - seedLength, guideLength)):
                if offtargetSeq[idx].islower():
                    return True

        return False

    def colourLowercaseRed(self, inputString):
        """wraps the lowercase letters of a string in a span html tag that has a class to colour items within it red"""
        result = ""
        for letter in inputString:
            if letter.islower():
                result += "<span class='green'>" + letter + "</span>"
            else:
                result += letter

        return result

    def sendResultHTML(self):
        """take the results of the guide search and insert them into the result template"""
        template_values = {
            "guideTable": self.guideTableHTML(),
            "searchInput": self.searchInput,
            "rgen": self.rgenRecord,
            "gene": self.gene,
            "length": self.guideLength,
        }
        print(self.renderTemplate("guide_results.html", template_values))
        return

    def sendNoResultHTML(self):
        """if no guides are found in the input sequence, display message"""
        template_values = {"searchInput": self.searchInput, "rgen": self.rgenRecord}
        print(self.renderTemplate("no_results.html", template_values))
        return

    def sendError(self, errorString):
        """format exceptions in HTML to prevent page from crashing"""
        if not hasattr(self, "dbConnection"):
            self.dbConnection = Config()

        if self.cli:
            raise Exception(errorString)
        else:
            print(self.renderTemplate("error.html", {"errorString": str(errorString)}))
            sys.exit()

    def getRGEN(self):
        # fetch the correct rgen record using the rgenID attribute
        rgenCollection = self.dbConnection.rgenCollection
        rgenQuery = {"rgenID": str(self.rgenID)}
        if rgenCollection.count_documents(rgenQuery) == 1:
            return rgenCollection.find_one(rgenQuery)
        else:
            raise ValueError(
                f"Incorrect number of records returned from RGEN database for rgenID: {self.rgenID}"
            )

    def writeCsvFiles(self):
        """for each guide, write a csv file of its off-targets to the OS temporary file directory"""
        if self.cli:
            # if cli, put all guides into same csv
            if self.output_file:  # skip if none
                total_offtargets_processed = 0
                with open(self.output_file, mode="w") as csv_file:
                    writer = csv.writer(csv_file, delimiter=",")
                    num_skipped = 0
                    num_exceeded = 0
                    for guideID, guide in self.guideDict.items():
                        writer.writerow([str(guideID) + ":"])
                        if guide["max_exceeded"]:
                            writer.writerow(
                                [
                                    "Max off target sites exceeded ("
                                    + str(sum(guide["offtarget_counts"]))
                                    + " shown)"
                                ]
                            )
                            total_offtargets_processed += 1000
                            num_exceeded += 1
                        elif guide["skip"]:
                            writer.writerow(
                                [
                                    "Multiple hits with <= 1 mismatch found in genome. Skipped finding off-targets"
                                ]
                            )
                            num_skipped += 1
                        else:
                            writer.writerow(
                                [
                                    "Total number of potential off-target sites:"
                                    + str(sum(guide["offtarget_counts"]))
                                ]
                            )
                            total_offtargets_processed += sum(guide["offtarget_counts"])
                        writer.writerow(
                            [
                                "Off-target Counts: "
                                + "-".join(map(str, guide["offtarget_counts"]))
                            ]
                        )
                        writer.writerow(
                            [
                                "No mismatches in Seed: "
                                + "-".join(map(str, guide["offtargets_seed"]))
                            ]
                        )
                        if guide["MIT"] and not guide["max_exceeded"]:
                            writer.writerow(["MIT Score: " + str(guide["MIT"])])
                        if guide["CFD"] and not guide["max_exceeded"]:
                            writer.writerow(["CFD Score: " + str(guide["CFD"])])
                        writer.writerow(
                            ["Location", "Sequence", "Mismatches", "Context"]
                        )
                        writer.writerow(
                            [
                                self.calculateLocation(guide),
                                self.formatSequence(
                                    guide["guide_seq"], guide["pam_seq"]
                                ),
                                "0",
                                "guide",
                            ]
                        )
                    writer.writerow([str(len(self.guideDict.keys())) + " GUIDES FOUND"])
                    writer.writerow([str(num_skipped) + " SKIPPED"])
                    writer.writerow([str(num_exceeded) + " EXCEEDED MAX OFF TARGETS"])
                    writer.writerow(
                        [str(total_offtargets_processed) + " OFF TARGETS FOUND"]
                    )
                    """
                    # UNCOMMENT TO GET ALL THE OFF TARGETS
                    for offtarget in guide['offtargets']:
                        row = [offtarget['loc']]
                        row.append(self.formatSequence(offtarget['seq'], offtarget['pam']))
                        row.append(countLower(offtarget['seq']))
                        try:
                            row.append(offtarget['context'])
                        except Exception as e:
                            row.append('-')
                        writer.writerow(row)
                    """
        else:
            for guideID, guide in self.guideDict.items():
                csv_path = os.path.join(
                    tempfile.gettempdir(), self.batchID + "_" + guideID + ".csv"
                )
                try:
                    with open(csv_path, mode="w") as csv_file:
                        writer = csv.writer(csv_file, delimiter=",")
                        # build and write heading row
                        column_headings = [
                            "chromosome",
                            "location",
                            "strand",
                            "protospacer sequence",
                            "PAM",
                            "mismatches",
                            "context",
                        ]
                        if "MIT" in self.scores and not (
                            guide["max_exceeded"] or guide["skip"]
                        ):
                            column_headings.append("MIT")
                        if "CFD" in self.scores and not (
                            guide["max_exceeded"] or guide["skip"]
                        ):
                            column_headings.append("CFD")
                        writer.writerow(
                            ["Location", "Sequence", "Mismatches", "Context"]
                        )
                        column_headings.append("no mismatches in seed")
                        writer.writerow(column_headings)

                        # build and write guide row
                        guide_row = [guide["pam_chrom"]]
                        guide_row.append(self.calculateLocation(guide).split(":")[1])
                        guide_row.append(guide["strand"])
                        guide_row.append(guide["guide_seq"])
                        guide_row.append(guide["pam_seq"])
                        guide_row.append("0")  # num mismatches
                        guide_row.append("guide")  # context
                        if "MIT" in self.scores and not (
                            guide["max_exceeded"] or guide["skip"]
                        ):
                            guide_row.append(guide["MIT"])
                        if "CFD" in self.scores and not (
                            guide["max_exceeded"] or guide["skip"]
                        ):
                            guide_row.append(guide["CFD"])
                        guide_row.append("")
                        writer.writerow(guide_row)

                        # initialize variables for determining whether offtarget has mismatch in seed
                        seedDirection = self.rgenRecord["SeedRegion"][0]
                        seedLength = int(self.rgenRecord["SeedRegion"][1:])
                        # build and write row for each of the potential off target sites
                        for offtarget in guide["offtargets"]:
                            offtarget_row = offtarget["loc"].split(":")
                            offtarget_row.append(offtarget["seq"])
                            offtarget_row.append(offtarget["pam"])
                            offtarget_row.append(
                                str(
                                    sum(
                                        1 for base in offtarget["seq"] if base.islower()
                                    )
                                )
                            )  # num mismatches
                            try:
                                offtarget_row.append(offtarget["context"])
                            except Exception:
                                offtarget_row.append("-")
                            if "MIT" in self.scores and not (
                                guide["max_exceeded"] or guide["skip"]
                            ):
                                offtarget_row.append(offtarget["MIT"])
                            if "CFD" in self.scores and not (
                                guide["max_exceeded"] or guide["skip"]
                            ):
                                offtarget_row.append(offtarget["CFD"])
                            if self.hasMismatchInSeed(
                                offtarget["seq"],
                                seedDirection,
                                seedLength,
                                len(guide["guide_seq"]),
                            ):
                                offtarget_row.append("")
                            else:
                                offtarget_row.append("*")
                            writer.writerow(offtarget_row)
                except Exception as e:
                    print(guideID)
                    print(guide)
                    self.sendError("Error writing off target CSV file, " + str(e))

    def getENSID(self):
        """given the gene symbol, return the ENSEMBL ID from the stored gene collection"""
        geneCollection = self.dbConnection.curr_geneCollection
        geneQuery = {"Name": self.gene}
        geneCount = geneCollection.count_documents(geneQuery)
        if geneCount > 1:
            self.sendError(
                "More than one result in the database for gene symbol: " + self.gene
            )
        elif geneCount < 1:
            # TODO: need to deal with tracking regions of interest that aren't in a gene region
            # for now, just use a blank ensembl id
            return ""
        else:
            return geneCollection.find_one(geneQuery)["ENSID"]

    def writeJsonFile(self):
        """for each run, write a json file of the relevant guide info for adding guides to the database"""
        # reformat the dictionary
        import copy

        databaseDict = copy.deepcopy(self.guideDict)
        for guideID, guide in databaseDict.items():
            guide["guideLocation"] = self.calculateLocation(guide)
        # add a metadata key
        databaseDict["metadata"] = {
            "genome": self.genome,
            "gene": self.gene,
            "ENSID": self.getENSID(),
            "rgenID": self.rgenID,
            "inputSearchCoordinates": self.searchInput,
        }
        with open(
            os.path.join(tempfile.gettempdir(), self.batchID + ".json"), "w"
        ) as json_file:
            json.dump(databaseDict, json_file)

    def performGuideSearch(self):
        """runs the backend modules"""
        # TODO: look into a collision-free hashing function so don't have to re-run entire pipeline if inputs don't change
        batchID = binascii.b2a_hex(os.urandom(9)).decode("utf-8")

        genome_fa = os.path.join(
            self.dbConnection.ROOT_PATH,
            "jbrowse",
            "data",
            self.genome,
            "processed",
            self.genome + ".fa",
        )
        genome_2bit = os.path.join(
            self.dbConnection.ROOT_PATH,
            "jbrowse",
            "data",
            self.genome,
            "processed",
            self.genome + ".2bit",
        )
        twoBitToFa_path = os.path.join(self.dbConnection.ROOT_PATH, "bin/twoBitToFa")
        tempfiles_path = tempfile.gettempdir()

        time_0 = time.time()
        logging.debug("\t\t[STARTED]\t\tFetching sequence...")

        get_sequence.fetch_sequence(
            self.searchInput,
            genome_2bit,
            os.path.join(tempfiles_path, batchID + "_out.fa"),
        )

        time_1 = time.time()
        logging.debug(
            f"\t\t[FINISHED]\tFetched sequence in {str(round(time_1-time_0,4))}s"
        )
        logging.debug("\t\t[STARTED]\t\tDetermining guides in search region...")

        protospacer_length = getattr(
            self, "guideLength", 0
        )  # passing 0 indicates default should be used
        guideDict = find_grna.find_grna(
            self.rgenID,
            protospacer_length,
            os.path.join(tempfiles_path, batchID + "_out.fa"),
        )

        time_2 = time.time()
        logging.debug(f"\t\t[FINISHED]\tFound gRNAs in {str(round(time_2-time_1,4))}s")
        logging.debug("\t\t[STARTED]\t\tSearching for potential off target sites...")

        guideDict = find_offtargets.findOffTargets(
            guideDict,
            self.rgenID,
            self.genome,
            self.maxOffTargets,
            batchID,
            genome_fa,
            tempfiles_path,
        )

        time_3 = time.time()
        logging.debug(
            f"\t\t[FINISHED]\tFound offtargets in {str(round(time_3-time_2,4))}s"
        )
        logging.debug(
            "\t\t[STARTED]\t\tScoring potential off target sites and guides..."
        )

        guideDict = score_offtargets.scoreOffTargets(
            guideDict,
            self.rgenID,
            genome_fa,
            twoBitToFa_path,
            genome_2bit,
            tempfiles_path,
        )

        time_4 = time.time()
        logging.debug(f"\t\t[FINISHED]\tScored in {str(round(time_4-time_3,4))}s")
        logging.debug("\t\t[STARTED]\t\tCategorizing potential off target sites...")

        guideDict = categorize_offtargets.categorizeOffTargets(
            guideDict, self.rgenID, self.genome, batchID
        )

        time_5 = time.time()
        logging.debug(f"\t\t[FINISHED]\tCategorized in {str(round(time_5-time_4,4))}s")

        return guideDict, batchID

    def isValidInput(self, inputSeq):
        # TODO: code this. some validation done on front end but not for the chr number/letter
        if len(inputSeq) == 0:
            self.sendError("Please enter an input region for the search")
            return False
        if inputSeq.count(":") == 1 and inputSeq.count("-") == 1:
            # chrm = inputSeq.split(":")[0]
            start, end = list(map(int, (inputSeq.split(":")[1]).split("-")))
            if abs(start - end) > 3000:
                self.sendError(
                    "Please enter an input sequence with fewer than 3000 bases"
                )
        else:
            self.sendError(
                "Please enter input search sequence in 'chrX:start-end' format"
            )

        return True


def countLower(string):
    """returns the number of lowercase letters in a string"""
    count = 0
    for letter in string:
        if letter.islower():
            count += 1
    return count


def main():
    # check if running from web or command-line
    if "REQUEST_METHOD" in os.environ:
        # running from web
        print("Content-type: text/html\n")
        inputForm = cgi.FieldStorage()
        parameters = {}
        parameters["command-line"] = False

        for arg in [
            "searchInput",
            "genome",
            "gene",
            "rgenID",
            "guideLength",
            "offtargetPAMs",
            "setMax",
            "maxOffTargets",
        ]:
            if inputForm.getvalue(arg) is not None:
                parameters[arg] = inputForm.getvalue(arg)

        # only use the max if the checkbox is selected
        parameters["maxOffTargets"] = (
            parameters["maxOffTargets"] if parameters["setMax"] == "true" else None
        )

        logging.debug("[WEB]\t\tRunning guide search and score with parameters:")
        logging.debug(f"\t\t{parameters}")

        GuideSearchAndScore(**parameters)
    else:
        desc = """ The command-line version of GuideSearchAndScore.py will return potential guides along with their scores and off-targets.
         """

        parser = argparse.ArgumentParser(prog="GuideSearchAndScore", description=desc)
        parser._action_groups.pop()
        required = parser.add_argument_group("required arguments")
        optional = parser.add_argument_group("optional arguments")
        required.add_argument(
            "--genome", help="Genome database (e.g. mm10)", required=True
        )
        required.add_argument(
            "--input",
            help="Chromosomal coordinates for region of interest",
            required=True,
        )
        required.add_argument("--gene", help="Gene of interest", required=True)
        required.add_argument(
            "--output", help="Location of output csv file", required=True
        )
        # optional flags:
        # default RGEN to 1 (SpCas9 with unmodified rgens.json)
        optional.add_argument(
            "--rgenID", nargs="?", default=1, help="id of desired RGEN"
        )
        # default guide length (protospacer) to 20
        optional.add_argument(
            "--spacer",
            nargs="?",
            default=20,
            type=int,
            help="Length of protospacer (e.g. 20)",
        )
        # default max off targets to 1000
        optional.add_argument(
            "--maxOffTargets",
            nargs="?",
            default=1000,
            type=int,
            help="Maximum number of off-targets to consider for any guide. Use -1 for no max",
        )
        args = parser.parse_args()

        parameters = {
            "genome": args.genome,
            "searchInput": args.input,
            "gene": args.gene,
            "output": args.output,
            "rgenID": args.rgenID,
            "guideLength": args.spacer,
            "maxOffTargets": None
            if args.maxOffTargets == -1
            else args.maxOffTargets,  # convert -1 to False for CLI
            "command-line": True,
        }

        logging.debug("[CLI]\t\tRunning guide search and score with parameters:")
        logging.debug(f"\t\t{parameters}")

        GuideSearchAndScore(**parameters)


if __name__ == "__main__":
    main()
